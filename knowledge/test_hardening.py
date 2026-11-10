import io
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from datetime import timedelta
from django.test import TestCase,TransactionTestCase,override_settings
from django.contrib.auth.models import User,Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_q.models import OrmQ
from .models import Article,Category,Rule,Version
from .uploads import attach
from .permissions import visible,allowed
from .tests import pdf_bytes
from .search import index,search
from .explanations import explain

class LifecycleTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('leitor')
        self.group=Group.objects.create(name='Equipe');self.user.groups.add(self.group)
        self.category=Category.objects.create(name='Guias')
        self.a=Article.objects.create(title='Documento de teste',category=self.category,owner=self.user,status='published')
        Rule.objects.create(group=self.group,category=self.category,action='view')
        self.client.force_login(self.user)
    def test_drafts_and_archives_do_not_leak(self):
        for state in ['draft','archived']:
            self.a.status=state;self.a.save();index(self.a)
            self.assertFalse(visible(self.user).exists())
            self.assertFalse(search(visible(self.user),'Documento').exists())
            self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/').status_code,404)
            self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/pdf/').status_code,404)
            self.assertNotContains(self.client.get('/'),'Documento de teste')
    def test_editor_still_needs_view(self):
        self.a.status='draft';self.a.save()
        Rule.objects.create(group=self.group,category=self.category,action='edit')
        self.assertTrue(visible(self.user).filter(pk=self.a.pk).exists())
        Rule.objects.create(group=self.group,category=self.category,action='view',deny=True)
        self.assertFalse(visible(self.user).exists())
        self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/editar/').status_code,403)
    def test_explanation_follows_winning_rule(self):
        Rule.objects.create(group=self.group,article=self.a,action='view',deny=True)
        result=explain(self.user,self.a,'view')
        self.assertFalse(result['allowed']);self.assertIn('negação',result['reason']);self.assertEqual(len(result['rules']),1)
    def test_expired_rules_are_not_in_explanation(self):
        Rule.objects.create(group=self.group,article=self.a,action='view',deny=True,expires_at=timezone.now()-timedelta(seconds=1))
        result=explain(self.user,self.a,'view')
        self.assertTrue(result['allowed']);self.assertIn('herdada',result['reason'])
    def test_disabled_account_has_no_effective_access(self):
        self.user.is_active=False;self.user.save()
        self.assertFalse(visible(self.user).exists())
        self.assertFalse(explain(self.user,self.a,'view')['allowed'])
        self.assertIn('desativada',explain(self.user,self.a,'view')['reason'])
    def test_range_authorized_and_exact(self):
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)):
            data=pdf_bytes();(Path(tmp)/'test.pdf').write_bytes(data)
            v=Version.objects.create(article=self.a,path='test.pdf',sha256=hashlib.sha256(data).hexdigest(),uploaded_by=self.user)
            self.a.current_version=v;self.a.save()
            url=f'/artigos/{self.a.pk}/pdf/'
            for header,start,end in [('bytes=0-31',0,31),('bytes=10-',10,len(data)-1),('bytes=-20',len(data)-20,len(data)-1)]:
                response=self.client.get(url,HTTP_RANGE=header)
                self.assertEqual(response.status_code,206)
                self.assertEqual(b''.join(response.streaming_content),data[start:end+1])
            for header in ['bytes=9000000-','bytes=30-10','bytes=-0','bytes=0-1,4-5','invalid','bytes='+('9'*5000)+'-']:
                self.assertEqual(self.client.get(url,HTTP_RANGE=header).status_code,416)
            response=self.client.head(url);self.assertEqual(response.status_code,200);self.assertEqual(int(response['Content-Length']),len(data))
            response=self.client.get(url,HTTP_RANGE='bytes=0-31',HTTP_IF_RANGE='"wrong-version"')
            self.assertEqual(response.status_code,200);self.assertEqual(b''.join(response.streaming_content),data)
            self.assertEqual(self.client.get(url+'?download=1',HTTP_RANGE='bytes=0-31').status_code,403)
            Rule.objects.create(group=self.group,category=self.category,action='view',deny=True)
            self.assertEqual(self.client.get(url,HTTP_RANGE='bytes=0-31').status_code,404)
    def test_operations_are_scoped(self):
        self.user.is_staff=True;self.user.save()
        self.assertEqual(self.client.get('/painel/auditoria/').status_code,403)
        self.assertNotContains(self.client.get('/painel/processamento/'),'Documento de teste')
        self.assertEqual(self.client.post(f'/painel/processamento/{self.a.pk}/repetir/').status_code,403)

class UploadAtomicityTests(TransactionTestCase):
    def test_queue_failure_rolls_back_everything_and_keeps_previous_file(self):
        user=User.objects.create_user('envio');category=Category.objects.create(name='Base')
        article=Article.objects.create(title='Arquivo original',owner=user,category=category)
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)):
            first=attach(article,SimpleUploadedFile('original.pdf',pdf_bytes()),user)
            count=OrmQ.objects.count()
            with patch('knowledge.uploads.async_task',side_effect=RuntimeError('Queue unavailable')):
                with self.assertRaises(ValidationError): attach(article,SimpleUploadedFile('new.pdf',pdf_bytes()),user)
            article.refresh_from_db()
            self.assertEqual(article.current_version_id,first.pk);self.assertEqual(Version.objects.count(),1)
            self.assertTrue((Path(tmp)/first.path).exists());self.assertEqual(len(list(Path(tmp).glob('*.pdf'))),1)
            self.assertEqual(OrmQ.objects.count(),count)
    def test_failed_new_upload_leaves_no_article(self):
        user=User.objects.create_user('envio');category=Category.objects.create(name='Base')
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)),patch('knowledge.uploads.async_task',side_effect=RuntimeError('Queue unavailable')):
            with self.assertRaises(ValidationError):attach(Article(title='Novo',owner=user,category=category),SimpleUploadedFile('new.pdf',pdf_bytes()),user)
            self.assertFalse(Article.objects.exists());self.assertFalse(list(Path(tmp).iterdir()))

