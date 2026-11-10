import io
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection, connections
from django.utils import timezone
from pypdf import PdfWriter
from .models import Category,Article,Rule,Version
from .permissions import visible,allowed
from .search import index,search
from .uploads import attach,validate

def pdf_bytes():
    b=io.BytesIO(); w=PdfWriter(); w.add_blank_page(width=400,height=600); w.write(b); return b.getvalue()

class PermissionTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('ana',password='Strong-test-328!')
        self.g=Group.objects.create(name='RH'); self.other=Group.objects.create(name='TI'); self.user.groups.add(self.g,self.other)
        self.root=Category.objects.create(name='Pessoas'); self.child=Category.objects.create(name='Políticas',parent=self.root)
        self.a=Article.objects.create(title='Férias e benefícios',description='Orientação',status='published',owner=self.user,category=self.child)
        self.secret=Article.objects.create(title='Segredo estratégico',owner=self.user,category=Category.objects.create(name='Diretoria'))
    def grant(self,**kw): return Rule.objects.create(group=self.g,category=self.root,action='view',**kw)
    def test_default_denial(self): self.assertFalse(allowed(self.user,self.a,'view'))
    def test_inherited(self): self.grant(); self.assertTrue(allowed(self.user,self.a,'view'))
    def test_multigroup_deny(self):
        self.grant(); Rule.objects.create(group=self.other,category=self.child,action='view',deny=True)
        self.assertFalse(allowed(self.user,self.a,'view'))
    def test_article_override_can_open(self):
        self.grant(deny=True); Rule.objects.create(group=self.g,article=self.a,action='view')
        self.assertTrue(allowed(self.user,self.a,'view'))
    def test_article_override_can_restrict(self):
        self.grant(); Rule.objects.create(group=self.g,article=self.a,action='view',deny=True)
        self.assertFalse(allowed(self.user,self.a,'view'))
    def test_expiration(self):
        self.grant(expires_at=timezone.now()-timedelta(seconds=1)); self.assertFalse(allowed(self.user,self.a,'view'))
    def test_distinct_actions(self):
        self.grant(); self.assertFalse(allowed(self.user,self.a,'download'))
    def test_search_accent_and_leaks(self):
        self.grant(); index(self.a); index(self.secret)
        self.assertEqual(list(search(visible(self.user),'FERIAS')), [self.a])
        self.assertFalse(search(visible(self.user),'segredo').exists())
        self.client.force_login(self.user)
        r=self.client.get('/?q=segredo'); self.assertNotContains(r,'estratégico'); self.assertContains(r,'0 artigos')
    def test_document_access(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/pdf/').status_code,404)
        self.grant()
        self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/pdf/?download=1').status_code,403)
    def test_category_cycle(self):
        self.root.parent=self.child
        with self.assertRaises(ValidationError): self.root.clean()
    def test_depth(self):
        c=Category.objects.create(name='3',parent=self.child)
        with self.assertRaises(ValidationError): Category(name='4',parent=c).clean()
    def test_manager(self):
        self.root.managers.add(self.g); self.assertTrue(allowed(self.user,self.a,'manage'))
        self.assertFalse(allowed(self.user,self.a,'view'))
    def test_lockout(self):
        for _ in range(5): self.client.post('/entrar/',{'username':'ana','password':'bad'})
        self.assertEqual(self.client.post('/entrar/',{'username':'ana','password':'Strong-test-328!'}).status_code,429)
    def test_csrf(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True); client.force_login(self.user)
        self.assertEqual(client.post(f'/artigos/{self.a.pk}/feedback/',{'helpful':'yes'}).status_code,403)
    def test_bad_pdf(self):
        with self.assertRaises(ValidationError): validate(SimpleUploadedFile('a.pdf',b'fake'))
    @override_settings(MAX_PDF_BYTES=1)
    def test_size(self):
        with self.assertRaises(ValidationError): validate(SimpleUploadedFile('a.pdf',pdf_bytes()))
    def test_versions_and_file(self):
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)):
            self.grant(); Rule.objects.create(group=self.g,category=self.root,action='download')
            first=attach(self.a,SimpleUploadedFile('a.pdf',pdf_bytes()),self.user)
            second=attach(self.a,SimpleUploadedFile('b.pdf',pdf_bytes()),self.user)
            self.assertEqual(self.a.versions.count(),2); self.assertNotEqual(first.path,second.path)
            self.client.force_login(self.user)
            r=self.client.get(f'/artigos/{self.a.pk}/pdf/?download=1')
            self.assertEqual(r.status_code,200); self.assertEqual(b''.join(r.streaming_content),pdf_bytes())
    def test_templates(self):
        self.grant(); self.client.force_login(self.user)
        for url in ['/',f'/artigos/{self.a.pk}/','/enviar/','/conta/password_change/']:
            self.assertEqual(self.client.get(url).status_code,200,url)
    def test_rule_editor_denies_reader(self):
        self.grant(); self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/regras/').status_code,403)
        self.assertEqual(self.client.get(f'/categorias/{self.root.pk}/regras/').status_code,403)
    def test_rule_editor_delegation(self):
        self.root.managers.add(self.g); self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/regras/').status_code,200)
        self.assertEqual(self.client.get(f'/categorias/{self.root.pk}/regras/').status_code,200)
        self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/permissoes/').status_code,200)
    def test_expired_override_falls_back(self):
        self.grant()
        Rule.objects.create(group=self.g,article=self.a,action='view',deny=True,expires_at=timezone.now()-timedelta(seconds=1))
        self.assertTrue(allowed(self.user,self.a,'view'))
    def test_no_group_union_leak(self):
        Rule.objects.create(group=Group.objects.create(name='Outro'),category=self.root,action='view')
        self.assertFalse(visible(self.user).exists())
    def test_unrelated_version_not_accessible(self):
        self.grant(); Rule.objects.create(group=self.g,category=self.root,action='edit')
        v=Version.objects.create(article=self.secret,path='private.pdf',sha256='0'*64,uploaded_by=self.user)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/pdf/?version={v.pk}').status_code,404)
    def test_state_change_requires_action_and_post(self):
        self.grant(); self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/acao/publish/').status_code,405)
        self.assertEqual(self.client.post(f'/artigos/{self.a.pk}/acao/publish/').status_code,403)
        Rule.objects.create(group=self.g,category=self.root,action='publish')
        self.assertEqual(self.client.post(f'/artigos/{self.a.pk}/acao/publish/').status_code,302)
        self.a.refresh_from_db(); self.assertEqual(self.a.status,'published')

class ConcurrentTests(TransactionTestCase):
    def test_backup_restore_integrity(self):
        from django.core.management import call_command
        from io import StringIO
        import sqlite3
        u=User.objects.create_user('backup'); c=Category.objects.create(name='Backup')
        a=Article.objects.create(title='Preservado',owner=u,category=c)
        with TemporaryDirectory() as tmp,TemporaryDirectory() as dest,override_settings(PRIVATE_ROOT=Path(tmp)):
            with patch('knowledge.uploads.async_task'): attach(a,SimpleUploadedFile('x.pdf',pdf_bytes()),u)
            output=StringIO(); call_command('backup',dest,stdout=output)
            root=Path(output.getvalue().strip())
            call_command('verify_backup',str(root),stdout=StringIO())
            with closing(sqlite3.connect(':memory:')) as restored,closing(sqlite3.connect(root/'knowledge.sqlite3')) as source:
                source.backup(restored)
                self.assertEqual(restored.execute('SELECT title FROM knowledge_article').fetchone()[0],'Preservado')
                self.assertEqual(restored.execute('PRAGMA integrity_check').fetchone()[0],'ok')
    def test_reads_during_upload(self):
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA journal_mode')
            self.assertEqual(cursor.fetchone()[0],'wal')
        u=User.objects.create_user('admin',is_superuser=True); c=Category.objects.create(name='Base')
        a=Article.objects.create(title='Teste',owner=u,category=c)
        def read(_):
            close_old_connections()
            try:
                for i in range(30): self.assertEqual(visible(User.objects.get(pk=u.pk)).count(),1)
            finally: connections.close_all()
        def write():
            close_old_connections()
            try:
                with patch('knowledge.uploads.async_task'):
                    attach(Article.objects.get(pk=a.pk),SimpleUploadedFile('x.pdf',pdf_bytes()),User.objects.get(pk=u.pk))
            finally: connections.close_all()
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)):
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures=[pool.submit(read,i) for i in range(4)]+[pool.submit(write)]
                for f in futures: f.result()
        self.assertEqual(Version.objects.count(),1)


