from django.test import TestCase
from django.contrib.auth.models import User,Group
from .models import Category,Article,Rule

class RuleEditorTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('editor',is_superuser=True,is_staff=True)
        self.group=Group.objects.create(name='Atendimento')
        self.category=Category.objects.create(name='Guias')
        self.article=Article.objects.create(title='Guia',category=self.category,owner=self.user)
        self.client.force_login(self.user)
    def payload(self,deny):
        return {'form-TOTAL_FORMS':'1','form-INITIAL_FORMS':'0','form-MIN_NUM_FORMS':'0','form-MAX_NUM_FORMS':'1000','form-0-group':self.group.pk,'form-0-action':'view','form-0-deny':deny,'form-0-expires_at':''}
    def test_explicit_allow(self):
        r=self.client.post(f'/categorias/{self.category.pk}/regras/',self.payload('False'))
        self.assertEqual(r.status_code,302)
        self.assertFalse(Rule.objects.get().deny)
    def test_explicit_block(self):
        r=self.client.post(f'/artigos/{self.article.pk}/regras/',self.payload('True'))
        self.assertRedirects(r,f'/artigos/{self.article.pk}/regras/')
        self.assertTrue(Rule.objects.get().deny)
    def test_blank_new_row_does_not_create_rule(self):
        payload=self.payload('False'); payload['form-0-group']='';payload['form-0-action']=''
        self.assertEqual(self.client.post(f'/categorias/{self.category.pk}/regras/',payload).status_code,302)
        self.assertFalse(Rule.objects.exists())
    def test_remove_existing_with_empty_new_row(self):
        rule=Rule.objects.create(group=self.group,category=self.category,action='view')
        payload=self.payload('False');payload.update({'form-INITIAL_FORMS':'1','form-TOTAL_FORMS':'2','form-0-id':rule.pk,'form-0-DELETE':'on','form-1-group':'','form-1-action':'','form-1-deny':'False','form-1-expires_at':''})
        self.assertEqual(self.client.post(f'/categorias/{self.category.pk}/regras/',payload).status_code,302)
        self.assertFalse(Rule.objects.exists())
    def test_scope_help_and_layout(self):
        r=self.client.get(f'/artigos/{self.article.pk}/regras/')
        self.assertContains(r,'Quem pode acessar?');self.assertContains(r,'Adicionar regra')
        self.assertContains(r,'Permitir');self.assertContains(r,'Bloquear')
        self.assertContains(r,'ACESSO AO ARTIGO')
        self.assertContains(self.client.get(f'/categorias/{self.category.pk}/regras/'),'ACESSO À CATEGORIA')
