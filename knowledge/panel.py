"""Administração web com escopos verificados no servidor."""
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .audit import record
from .models import Article, Category, Tag
from .permissions import allowed, category_allowed, visible
from django.views.decorators.http import require_POST
from django.conf import settings


def managed(user):
    return Category.objects.filter(pk__in=[c.pk for c in Category.objects.select_related('parent__parent') if category_allowed(user, c, 'manage')])


def access(user):
    if not (user.is_active and (user.is_staff or user.is_superuser or managed(user).exists())):
        raise PermissionDenied


def permit(user, permission):
    if not user.has_perm(permission):
        raise PermissionDenied


def context(user):
    return {
        'can_users': user.has_perm('auth.view_user'),
        'can_groups': user.has_perm('auth.view_group'),
        'can_tags': user.has_perm('knowledge.view_tag'),
        'can_add_category': user.has_perm('knowledge.add_category'),
        'processing_failures': visible(user).filter(indexing='error',pk__in=visible(user,'edit').values('pk')).count(),
    }


def page(request, template, **extra):
    access(request.user)
    return render(request, 'panel/' + template, {**context(request.user), **extra})


@login_required
def dashboard(request):
    access(request.user)
    cats = managed(request.user)
    articles = visible(request.user)
    return page(request, 'dashboard.html', categories=cats, total=articles.count(), drafts=articles.filter(status='draft').count(), overdue=articles.filter(review_at__lt=timezone.now()).count(), recent=articles.select_related('category').order_by('-updated_at')[:8])


@login_required
def processing(request):
    access(request.user)
    qs=visible(request.user).filter(pk__in=visible(request.user,'edit').values('pk')).select_related('category').order_by('-updated_at')
    return page(request,'processing.html',pagination=Paginator(qs,25).get_page(request.GET.get('page')))


@login_required
@require_POST
def retry_processing(request,pk):
    access(request.user)
    from datetime import timedelta
    from django_q.tasks import async_task
    from django.core.exceptions import ValidationError
    with transaction.atomic():
        article=get_object_or_404(visible(request.user),pk=pk)
        if not allowed(request.user,article,'edit'): raise PermissionDenied
        if not article.current_version_id:
            messages.error(request,'Este artigo ainda não possui PDF.');return redirect('panel_processing')
        recent=article.processing_started_at or article.queued_at
        if article.indexing in ['pending','processing'] and recent and recent>timezone.now()-timedelta(minutes=20):
            messages.info(request,'Este PDF já está na fila ou em processamento.');return redirect('panel_processing')
        try:
            # Savepoint: falha da fila não altera o estado persistido.
            with transaction.atomic():
                async_task('knowledge.tasks.extract',article.current_version_id)
                article.indexing='pending';article.indexing_error='';article.queued_at=timezone.now();article.processing_started_at=None
                article.save(update_fields=['indexing','indexing_error','queued_at','processing_started_at'])
        except Exception:
            messages.error(request,'Não foi possível agendar. O PDF foi preservado; tente novamente.')
            return redirect('panel_processing')
    record(request.user,'retry_processing',article)
    messages.success(request,'PDF enviado novamente para processamento.');return redirect('panel_processing')


@login_required
def audit(request):
    access(request.user)
    if not request.user.is_superuser: raise PermissionDenied
    from collections import deque
    import json
    rows=deque(maxlen=200)
    event=request.GET.get('evento','')[:50]
    for path in sorted(settings.DATA_DIR.glob('audit.log*'),key=lambda p:p.stat().st_mtime):
        with path.open(encoding='utf-8') as log:
            for line in log:
                try: row=json.loads(line)
                except ValueError: continue
                if not event or row.get('event')==event: rows.append(row)
    people=dict(User.objects.filter(pk__in=[r.get('user') for r in rows]).values_list('pk','username'))
    titles=dict(Article.objects.filter(pk__in=[r.get('article') for r in rows if r.get('article')]).values_list('pk','title'))
    labels={'view':'Abriu artigo','pdf':'Visualizou PDF','download':'Baixou PDF','upload':'Enviou artigo','edit':'Editou artigo','publish':'Publicou artigo','archive':'Arquivou artigo','permissions':'Alterou permissões do artigo','category_permissions':'Alterou permissões da categoria','user_change':'Alterou usuário','group_change':'Alterou grupo','retry_processing':'Solicitou nova extração'}
    labels['delete']='Excluiu registro'
    from django.utils.dateparse import parse_datetime
    items=[]
    for row in reversed(rows):
        items.append({'at':parse_datetime(row.get('at','')),'user':people.get(row.get('user'),'Conta removida'),'event':labels.get(row.get('event'),row.get('event')),'article':titles.get(row.get('article'),''),'details':{k:v for k,v in row.items() if k not in ['at','user','event','article']}})
    return page(request,'audit.html',items=items,event=event,events=labels.items())


@login_required
def articles(request):
    access(request.user)
    qs = visible(request.user).select_related('category','owner').order_by('-updated_at')
    q = request.GET.get('q','').strip()[:200]
    if q:
        qs = qs.filter(Q(title__icontains=q)|Q(description__icontains=q))
    status = request.GET.get('status','')
    if status in dict(Article.STATUS):
        qs = qs.filter(status=status)
    if request.GET.get('revisao') == 'vencida':
        qs = qs.filter(review_at__lt=timezone.now())
    items = []
    for a in Paginator(qs,20).get_page(request.GET.get('page')):
        items.append({'article':a, 'edit':allowed(request.user,a,'edit'), 'manage':allowed(request.user,a,'manage'), 'publish':allowed(request.user,a,'publish'), 'archive':allowed(request.user,a,'archive')})
    return page(request,'articles.html',items=items,pagination=Paginator(qs,20).get_page(request.GET.get('page')),q=q,status=status,statuses=Article.STATUS)


class CategoryForm(forms.ModelForm):
    class Meta:
        model=Category
        fields=['name','parent','managers']


@login_required
def categories(request):
    access(request.user)
    qs = Category.objects.all() if request.user.has_perm('knowledge.view_category') else managed(request.user)
    items=list(qs.select_related('parent').order_by('name'))
    for category in items: category.can_manage=category_allowed(request.user,category,'manage')
    return page(request,'categories.html',categories=items)


@login_required
def category_edit(request,pk=None):
    access(request.user)
    permit(request.user,'knowledge.change_category' if pk else 'knowledge.add_category')
    obj=get_object_or_404(Category,pk=pk) if pk else None
    form=CategoryForm(request.POST or None,instance=obj)
    if request.method=='POST' and form.is_valid():
        obj=form.save(); record(request.user,'category_change',category=obj.pk)
        messages.success(request,'Categoria salva.'); return redirect('panel_categories')
    return page(request,'form.html',form=form,title='Editar categoria' if pk else 'Nova categoria',back='panel_categories')


User=get_user_model()


class NewUserForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model=User
        fields=['username','first_name','last_name','email']


class PersonForm(forms.ModelForm):
    class Meta:
        model=User
        fields=['username','first_name','last_name','email','is_active','is_staff','groups']
        labels={'is_staff':'Acesso ao painel administrativo','groups':'Grupos e departamentos'}


@login_required
def users(request):
    access(request.user); permit(request.user,'auth.view_user')
    qs=User.objects.order_by('username')
    q=request.GET.get('q','').strip()[:150]
    if q: qs=qs.filter(Q(username__icontains=q)|Q(first_name__icontains=q)|Q(email__icontains=q))
    return page(request,'users.html',pagination=Paginator(qs,30).get_page(request.GET.get('page')),q=q,can_add=request.user.is_superuser)


@login_required
def user_edit(request,pk=None):
    access(request.user)
    # Contas e grupos controlam privilégios: somente superusuários os alteram.
    if not request.user.is_superuser: raise PermissionDenied
    obj=get_object_or_404(User,pk=pk) if pk else None
    was_active=bool(obj and obj.is_active)
    form=PersonForm(request.POST or None,instance=obj) if pk else NewUserForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if obj and obj.pk==request.user.pk and (not form.cleaned_data['is_active'] or not form.cleaned_data['is_staff']):
            form.add_error(None,'Você não pode desativar seu próprio acesso administrativo.')
        else:
            obj=form.save(); record(request.user,'user_change',target_user=obj.pk)
            messages.success(request,'Usuário salvo.'); return redirect('panel_users')
    return page(request,'form.html',form=form,title='Editar usuário' if pk else 'Novo usuário',back='panel_users',confirm_deactivate=was_active)


class PermissionChoice(forms.ModelMultipleChoiceField):
    def label_from_instance(self,obj):
        actions={'view':'Consultar','add':'Criar','change':'Editar'}
        subjects={'user':'usuários','group':'grupos','category':'categorias','tag':'tags'}
        return actions.get(obj.codename.split('_')[0],obj.codename)+' '+subjects.get(obj.content_type.model,obj.content_type.model)


class GroupForm(forms.ModelForm):
    permissions=PermissionChoice(queryset=Permission.objects.filter(Q(content_type__app_label='knowledge',content_type__model__in=['category','tag'],codename__regex=r'^(view|add|change)_')|Q(content_type__app_label='auth',codename__in=['view_user','view_group'])).select_related('content_type'),required=False,label='Funções administrativas',help_text='Para usar o painel como administrador, o usuário também precisa ter acesso administrativo habilitado. As permissões de conteúdo são configuradas nas categorias.')
    class Meta:
        model=Group
        fields=['name','permissions']
        labels={'name':'Nome do grupo / departamento'}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.preserved=list(self.instance.permissions.exclude(pk__in=self.fields['permissions'].queryset)) if self.instance.pk else []
    def save(self,commit=True):
        obj=super().save(commit=commit)
        if commit: obj.permissions.add(*self.preserved)
        return obj


@login_required
def groups(request):
    access(request.user); permit(request.user,'auth.view_group')
    return page(request,'groups.html',groups=Group.objects.prefetch_related('user_set').order_by('name'))


@login_required
def group_edit(request,pk=None):
    access(request.user)
    if not request.user.is_superuser: raise PermissionDenied
    obj=get_object_or_404(Group,pk=pk) if pk else None
    form=GroupForm(request.POST or None,instance=obj)
    if request.method=='POST' and form.is_valid():
        obj=form.save(); record(request.user,'group_change',group=obj.pk)
        messages.success(request,'Grupo salvo.'); return redirect('panel_groups')
    return page(request,'form.html',form=form,title='Editar grupo' if pk else 'Novo grupo',back='panel_groups')


class TagForm(forms.ModelForm):
    class Meta:
        model=Tag
        fields=['name']


@login_required
def tags(request):
    access(request.user); permit(request.user,'knowledge.view_tag')
    return page(request,'tags.html',tags=Tag.objects.order_by('name'),can_add=request.user.has_perm('knowledge.add_tag'),can_change=request.user.has_perm('knowledge.change_tag'))


@login_required
def tag_edit(request,pk=None):
    access(request.user); permit(request.user,'knowledge.change_tag' if pk else 'knowledge.add_tag')
    obj=get_object_or_404(Tag,pk=pk) if pk else None
    form=TagForm(request.POST or None,instance=obj)
    if request.method=='POST' and form.is_valid():
        from .search import index
        with transaction.atomic():
            obj=form.save()
            for article in obj.article_set.all(): index(article)
        record(request.user,'tag_change',tag=obj.pk)
        messages.success(request,'Tag salva.'); return redirect('panel_tags')
    return page(request,'form.html',form=form,title='Editar tag' if pk else 'Nova tag',back='panel_tags')
