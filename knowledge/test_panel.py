from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from .models import Category,Article,Tag

class PanelTests(TestCase):
    def setUp(self):
        self.root=User.objects.create_user('principal',is_staff=True,is_superuser=True)
        self.reader=User.objects.create_user('leitor')
        self.staff=User.objects.create_user('equipe',is_staff=True)
        self.manager=User.objects.create_user('gestor')
        self.group=Group.objects.create(name='Equipe')
        self.manager.groups.add(self.group)
        self.category=Category.objects.create(name='Suporte')
        self.category.managers.add(self.group)
        self.secret=Category.objects.create(name='Categoria confidencial')
        self.article=Article.objects.create(title='Artigo confidencial',category=self.secret,owner=self.root)

    def test_anonymous_login(self):
        self.assertRedirects(self.client.get('/painel/'),'/entrar/?next=/painel/')

    def test_reader_denied_even_post(self):
        self.client.force_login(self.reader)
        for path in ['/painel/','/painel/usuarios/','/painel/grupos/','/painel/categorias/']:
            self.assertEqual(self.client.get(path).status_code,403)
        self.assertEqual(self.client.post('/painel/grupos/novo/',{'name':'Escalada'}).status_code,403)
        self.assertFalse(Group.objects.filter(name='Escalada').exists())

    def test_superuser_screens(self):
        self.client.force_login(self.root)
        for path in ['/painel/','/painel/artigos/','/painel/categorias/','/painel/usuarios/','/painel/grupos/','/painel/tags/','/painel/usuarios/novo/','/painel/grupos/novo/','/painel/categorias/nova/','/painel/tags/nova/']:
            self.assertEqual(self.client.get(path).status_code,200,path)
        self.assertEqual(self.client.get('/metricas/').status_code,200)

    def test_staff_cannot_escalate(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/painel/').status_code,200)
        for path in ['/painel/usuarios/','/painel/grupos/','/painel/usuarios/novo/','/painel/grupos/novo/','/painel/categorias/nova/']:
            self.assertEqual(self.client.post(path,{'is_superuser':True,'is_staff':True,'name':'Escalada'}).status_code,403,path)

    def test_manager_no_leaks(self):
        self.client.force_login(self.manager)
        r=self.client.get('/painel/categorias/')
        self.assertContains(r,'Suporte'); self.assertNotContains(r,'Categoria confidencial')
        self.assertNotContains(self.client.get('/painel/artigos/'),'Artigo confidencial')
        self.assertEqual(self.client.get(f'/categorias/{self.secret.pk}/regras/').status_code,403)
        self.assertEqual(self.client.get(f'/painel/categorias/{self.secret.pk}/').status_code,403)
        self.assertEqual(self.client.get('/painel/usuarios/').status_code,403)

    def test_model_view_permission(self):
        self.staff.user_permissions.add(Permission.objects.get(codename='view_user'))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/painel/usuarios/').status_code,200)
        self.assertEqual(self.client.post(f'/painel/usuarios/{self.reader.pk}/',{'is_staff':True}).status_code,403)
        self.reader.refresh_from_db(); self.assertFalse(self.reader.is_staff)

    def test_create_group_category_tag(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.post('/painel/grupos/novo/',{'name':'Financeiro'}).status_code,302)
        self.assertEqual(self.client.post('/painel/categorias/nova/',{'name':'Processos'}).status_code,302)
        self.assertEqual(self.client.post('/painel/tags/nova/',{'name':'Rotina'}).status_code,302)
        self.assertTrue(Group.objects.filter(name='Financeiro').exists())
        self.assertTrue(Category.objects.filter(name='Processos').exists())
        self.assertTrue(Tag.objects.filter(name='Rotina').exists())

    def test_self_deactivation_denied(self):
        self.client.force_login(self.root)
        r=self.client.post(f'/painel/usuarios/{self.root.pk}/',{'username':'principal','is_active':'','is_staff':''})
        self.assertEqual(r.status_code,200)
        self.root.refresh_from_db(); self.assertTrue(self.root.is_active)

    def test_staff_admin_redirect(self):
        self.client.force_login(self.staff)
        self.assertRedirects(self.client.get('/admin/'),'/painel/')

    def test_new_navigation(self):
        self.client.force_login(self.manager)
        r=self.client.get('/')
        self.assertContains(r,'href="/painel/"'); self.assertNotContains(r,'href="/admin/"')

    def test_forged_permissions_rejected(self):
        self.client.force_login(self.root)
        dangerous=Permission.objects.get(codename='change_user')
        r=self.client.post('/painel/grupos/novo/',{'name':'Escalada','permissions':[dangerous.pk]})
        self.assertEqual(r.status_code,200)
        self.assertFalse(Group.objects.filter(name='Escalada').exists())

    def test_existing_technical_permissions_preserved(self):
        self.client.force_login(self.root)
        technical=Permission.objects.get(codename='change_user')
        self.group.permissions.add(technical)
        self.assertEqual(self.client.post(f'/painel/grupos/{self.group.pk}/',{'name':'Equipe atualizada'}).status_code,302)
        self.assertTrue(self.group.permissions.filter(pk=technical.pk).exists())

    def test_create_user_is_unprivileged(self):
        self.client.force_login(self.root)
        response=self.client.post('/painel/usuarios/novo/',{'username':'nova','password1':'Secure-testing-4728!','password2':'Secure-testing-4728!','is_superuser':'on','is_staff':'on'})
        self.assertEqual(response.status_code,302)
        user=User.objects.get(username='nova')
        self.assertFalse(user.is_superuser); self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('Secure-testing-4728!'))
