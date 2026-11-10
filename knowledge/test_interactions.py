import re
import time
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from django.test import override_settings
from django.test import TestCase,Client
from django.contrib.auth.models import User,Group,Permission
from django.utils import timezone
from .models import Article,Category,Tag,Rule,Version

class InteractionTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user('principal',is_superuser=True,is_staff=True)
        self.reader=User.objects.create_user('pessoa')
        self.c=Category.objects.create(name='Processos')
        self.a=Article.objects.create(title='Guia importante',category=self.c,owner=self.admin,status='archived',indexing='ready')
        self.client.force_login(self.admin)
    def token(self,kind,pk):
        response=self.client.get(f'/painel/excluir/{kind}/{pk}/')
        self.assertEqual(response.status_code,200)
        return re.search(r'name="token" value="([^"]+)"',response.content.decode()).group(1)
    def test_get_never_deletes(self):
        self.client.get(f'/painel/excluir/artigo/{self.a.pk}/')
        self.assertTrue(Article.objects.filter(pk=self.a.pk).exists())
    def test_missing_confirmation_and_token_do_not_delete(self):
        url=f'/painel/excluir/artigo/{self.a.pk}/'
        self.assertEqual(self.client.post(url,{'confirm':'yes'}).status_code,400)
        self.assertEqual(self.client.post(url,{'token':self.token('artigo',self.a.pk)}).status_code,400)
        self.assertTrue(Article.objects.filter(pk=self.a.pk).exists())
    def test_confirmed_article_delete_and_fts_cleanup(self):
        from .search import index,search
        index(self.a)
        token=self.token('artigo',self.a.pk)
        response=self.client.post(f'/painel/excluir/artigo/{self.a.pk}/',{'token':token,'confirm':'yes'})
        self.assertEqual(response.status_code,302);self.assertFalse(Article.objects.filter(pk=self.a.pk).exists())
        self.assertFalse(search(Article.objects.all(),'Guia').exists())
    def test_token_is_bound_to_target_and_actor(self):
        token=self.token('artigo',self.a.pk)
        other=Article.objects.create(title='Outro',category=self.c,owner=self.admin,status='archived',indexing='ready')
        self.assertEqual(self.client.post(f'/painel/excluir/artigo/{other.pk}/',{'token':token,'confirm':'yes'}).status_code,400)
        second=User.objects.create_user('outroadmin',is_superuser=True,is_staff=True)
        self.client.force_login(second)
        self.assertEqual(self.client.post(f'/painel/excluir/artigo/{self.a.pk}/',{'token':token,'confirm':'yes'}).status_code,400)
    def test_changed_object_requires_new_confirmation(self):
        token=self.token('artigo',self.a.pk)
        self.a.title='Título alterado';self.a.save()
        self.assertEqual(self.client.post(f'/painel/excluir/artigo/{self.a.pk}/',{'token':token,'confirm':'yes'}).status_code,400)
    def test_expired_confirmation_is_rejected(self):
        token=self.token('artigo',self.a.pk)
        with patch('django.core.signing.time.time',return_value=time.time()+601):
            self.assertEqual(self.client.post(f'/painel/excluir/artigo/{self.a.pk}/',{'token':token,'confirm':'yes'}).status_code,400)
        self.assertTrue(Article.objects.filter(pk=self.a.pk).exists())
    def test_dependency_added_after_preview_is_preserved(self):
        group=Group.objects.create(name='Temporário');token=self.token('grupo',group.pk)
        self.reader.groups.add(group)
        self.assertEqual(self.client.post(f'/painel/excluir/grupo/{group.pk}/',{'token':token,'confirm':'yes'}).status_code,400)
        self.assertTrue(self.reader.groups.filter(pk=group.pk).exists())
    def test_deleting_record_does_not_purge_retained_pdf(self):
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)):
            path=Path(tmp)/'retained.pdf';path.write_bytes(b'%PDF-test')
            version=Version.objects.create(article=self.a,path=path.name,sha256='x'*64,uploaded_by=self.admin)
            self.a.current_version=version;self.a.save()
            token=self.token('artigo',self.a.pk)
            self.assertEqual(self.client.post(f'/painel/excluir/artigo/{self.a.pk}/',{'token':token,'confirm':'yes'}).status_code,302)
            self.assertTrue(path.exists());self.assertFalse(Version.objects.filter(pk=version.pk).exists())
            self.assertEqual(self.client.get(f'/artigos/{self.a.pk}/pdf/').status_code,404)
    def test_published_article_is_blocked(self):
        self.a.status='published';self.a.save()
        response=self.client.get(f'/painel/excluir/artigo/{self.a.pk}/')
        self.assertContains(response,'Arquive o artigo');self.assertNotContains(response,'name="token"')
    def test_category_dependencies_are_blocked(self):
        response=self.client.get(f'/painel/excluir/categoria/{self.c.pk}/')
        self.assertContains(response,'Há artigos');self.assertNotContains(response,'name="token"')
    def test_group_in_use_cannot_delete_or_remove_members(self):
        g=Group.objects.create(name='Equipe');self.reader.groups.add(g)
        response=self.client.get(f'/painel/excluir/grupo/{g.pk}/')
        self.assertContains(response,'Há usuários');self.assertTrue(self.reader.groups.filter(pk=g.pk).exists())
    def test_tag_in_use_is_blocked(self):
        tag=Tag.objects.create(name='Rotina');self.a.tags.add(tag)
        self.assertContains(self.client.get(f'/painel/excluir/tag/{tag.pk}/'),'em uso')
    def test_empty_category_group_and_tag_can_be_deleted(self):
        for kind,obj in [('categoria',Category.objects.create(name='Vazia')),('grupo',Group.objects.create(name='Vazio')),('tag',Tag.objects.create(name='Vazia'))]:
            pk=obj.pk;token=self.token(kind,pk)
            self.assertEqual(self.client.post(f'/painel/excluir/{kind}/{pk}/',{'token':token,'confirm':'yes'}).status_code,302)
            self.assertFalse(type(obj).objects.filter(pk=pk).exists())
    def test_reader_and_staff_cannot_delete_articles(self):
        for staff in [False,True]:
            self.reader.is_staff=staff;self.reader.save();self.client.force_login(self.reader)
            for method in [self.client.get,self.client.post]:self.assertEqual(method(f'/painel/excluir/artigo/{self.a.pk}/').status_code,403)
    def test_csrf_is_required(self):
        token=self.token('artigo',self.a.pk)
        client=Client(enforce_csrf_checks=True);client.force_login(self.admin)
        self.assertEqual(client.post(f'/painel/excluir/artigo/{self.a.pk}/',{'token':token,'confirm':'yes'}).status_code,403)
    def test_processing_alert_respects_view_permissions(self):
        self.a.indexing='error';self.a.indexing_error='falha de processamento';self.a.save()
        self.assertContains(self.client.get('/painel/'),'1 PDF(s) com falha')
        self.reader.is_staff=True;self.reader.save();self.client.force_login(self.reader)
        self.assertNotContains(self.client.get('/painel/'),'PDF(s) com falha')
    def test_confirmation_hooks_and_form_error_feedback(self):
        self.assertContains(self.client.get(f'/artigos/{self.a.pk}/'),'data-confirm-title="Publicar artigo?"')
        self.assertContains(self.client.get(f'/artigos/{self.a.pk}/editar/'),'data-confirm-file')
        self.assertContains(self.client.get('/painel/usuarios/novo/'),'data-dirty')
        self.assertContains(self.client.get('/painel/usuarios/novo/'),'id="action-dialog"')
        self.assertContains(self.client.post('/painel/categorias/nova/',{'name':''}),'O formulário não foi salvo')
