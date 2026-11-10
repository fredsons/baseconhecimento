from pathlib import Path
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse,Http404,JsonResponse
from django.shortcuts import render,get_object_or_404,redirect
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.text import slugify
from .models import Article,Category,Rule,Feedback,SearchMiss,Version
from .permissions import visible,allowed,category_allowed
from .search import search,index
from .forms import ArticleForm,ReplacementForm,RuleForm
from .uploads import attach
from .audit import record
from django.contrib import messages
@login_required
def category_rules(request,pk):
 from django.forms import modelformset_factory
 category=get_object_or_404(Category,pk=pk)
 if not category_allowed(request.user,category,'manage'): raise PermissionDenied
 Factory=modelformset_factory(Rule,form=RuleForm,extra=1,can_delete=True)
 formset=Factory(request.POST or None,queryset=Rule.objects.filter(category=category))
 if request.method=='POST' and formset.is_valid():
  from django.db import transaction
  with transaction.atomic():
   objects=formset.save(commit=False)
   for obj in formset.deleted_objects: obj.delete()
   for obj in objects: obj.category=category; obj.article=None; obj.save()
  record(request.user,'category_permissions',category=category.pk)
  from django.contrib import messages
  messages.success(request,'Permissões salvas.')
  return redirect('category_rules',pk=pk)
 return render(request,'rules.html',{'formset':formset,'article':category,'scope':'category','now':timezone.now()})
@login_required
def rules(request,pk):
 from django.forms import modelformset_factory
 a=get_object_or_404(Article,pk=pk)
 if not allowed(request.user,a,'manage'): raise PermissionDenied
 Factory=modelformset_factory(Rule,form=RuleForm,extra=1,can_delete=True)
 formset=Factory(request.POST or None,queryset=Rule.objects.filter(article=a))
 if request.method=='POST' and formset.is_valid():
  from django.db import transaction
  with transaction.atomic():
   objects=formset.save(commit=False)
   for obj in formset.deleted_objects: obj.delete()
   for obj in objects: obj.article=a; obj.category=None; obj.save()
  record(request.user,'permissions',a)
  from django.contrib import messages
  messages.success(request,'Permissões salvas.')
  return redirect('rules',pk=pk)
 return render(request,'rules.html',{'formset':formset,'article':a,'scope':'article','now':timezone.now()})
@login_required
def metrics(request):
 if not request.user.is_superuser: raise PermissionDenied
 from collections import Counter
 import json
 from django.db.models import Count
 from .panel import context
 accesses=Counter()
 for path in settings.DATA_DIR.glob('audit.log*'):
  with path.open(encoding='utf-8') as log:
   for line in log:
    try:
     entry=json.loads(line)
     if entry.get('event')=='view': accesses[entry.get('article')]+=1
    except ValueError: continue
 titles=dict(Article.objects.filter(pk__in=[pk for pk in accesses if pk is not None]).values_list('pk','title'))
 popular=[{'pk':pk,'title':titles[pk],'count':count} for pk,count in accesses.most_common() if pk in titles][:10]
 return render(request,'panel/metrics.html',{**context(request.user),'popular':popular,'misses':SearchMiss.objects.values('query').annotate(total=Count('pk')).order_by('-total')[:15],'feedback':Feedback.objects.values('article__title','helpful').annotate(total=Count('pk')).order_by('article__title')[:30],'overdue':Article.objects.filter(review_at__lt=timezone.now()).order_by('review_at')[:30]})
@login_required
def home(request):
 qs=visible(request.user).select_related('category','owner').order_by('-updated_at')
 q=request.GET.get('q','').strip()[:200]
 if q:
  qs=search(qs,q)
  if not qs.exists(): SearchMiss.objects.create(query=q)
 category=request.GET.get('categoria','')
 if category.isdigit(): qs=qs.filter(category_id=category)
 categories=Category.objects.filter(article__in=visible(request.user)).distinct()
 return render(request,'home.html',{'page':Paginator(qs,20).get_page(request.GET.get('page')),'q':q,'categories':categories,'category':category})
@login_required
def detail(request,pk):
 a=get_object_or_404(visible(request.user).select_related('category','owner'),pk=pk)
 record(request.user,'view',a)
 return render(request,'article.html',{'article':a,'download':allowed(request.user,a,'download'),'edit':allowed(request.user,a,'edit'),'publish':allowed(request.user,a,'publish'),'archive':allowed(request.user,a,'archive'),'manage':allowed(request.user,a,'manage')})
@login_required
def pdf(request,pk):
 a=get_object_or_404(visible(request.user),pk=pk)
 download=request.GET.get('download')=='1'
 if download and not allowed(request.user,a,'download'): raise PermissionDenied
 v=a.current_version
 if request.GET.get('version'):
  if not allowed(request.user,a,'edit'): raise PermissionDenied
  if not request.GET['version'].isdigit(): raise Http404
  v=get_object_or_404(Version,article=a,pk=request.GET['version'])
 if not v: raise Http404
 path=settings.PRIVATE_ROOT/v.path
 if not path.is_file(): raise Http404
 record(request.user,'download' if download else 'pdf',a,version=v.pk)
 import re
 from .pdf_response import serve
 filename=re.sub(r'[<>:"/\\|?*\x00-\x1f]','-',a.title).strip(' .') or 'artigo'
 return serve(request,path,filename+'.pdf',v.sha256,download)
@login_required
def upload(request):
 form=ArticleForm(request.POST or None,request.FILES or None)
 cats=[c.pk for c in Category.objects.all() if category_allowed(request.user,c,'upload')]
 form.fields['category'].queryset=Category.objects.filter(pk__in=cats)
 if request.method=='POST' and form.is_valid():
  a=form.save(commit=False); a.owner=request.user
  try:
   attach(a,form.cleaned_data['pdf'],request.user)
   from django.db import transaction
   with transaction.atomic():
    form.save_m2m();a.refresh_from_db();index(a)
   record(request.user,'upload',a)
   messages.success(request,'Artigo enviado. O PDF está na fila de processamento.')
   return redirect('article',pk=a.pk) if visible(request.user).filter(pk=a.pk).exists() else redirect('home')
  except ValidationError as e: form.add_error('pdf',e)
 return render(request,'form.html',{'form':form,'title':'Enviar artigo'})
@login_required
def edit(request,pk):
 a=get_object_or_404(Article,pk=pk)
 if not allowed(request.user,a,'edit'): raise PermissionDenied
 form=ArticleForm(request.POST or None,request.FILES or None,instance=a); form.fields['pdf'].required=False
 form.fields['category'].queryset=Category.objects.filter(pk=a.category_id)
 if request.method=='POST' and form.is_valid():
  try:
   from django.db import transaction
   a=form.save(commit=False)
   if form.cleaned_data['pdf']: attach(a,form.cleaned_data['pdf'],request.user)
   else:
    a.save(update_fields=['title','description','review_at','updated_at'])
   with transaction.atomic():
    form.save_m2m();a.refresh_from_db();index(a)
   record(request.user,'edit',a);messages.success(request,'Artigo salvo. O histórico das versões foi preservado.');return redirect('article',pk=pk)
  except ValidationError as e: form.add_error('pdf',e)
 return render(request,'form.html',{'form':form,'title':'Editar artigo e substituir PDF'})
@login_required
@require_POST
def transition(request,pk,action):
 a=get_object_or_404(Article,pk=pk)
 if action not in ['publish','archive'] or not allowed(request.user,a,action): raise PermissionDenied
 a.status='published' if action=='publish' else 'archived'
 if action=='publish': a.published_at=timezone.now()
 a.save(update_fields=['status','published_at','updated_at']); record(request.user,action,a)
 messages.success(request,'Artigo publicado.' if action=='publish' else 'Artigo arquivado.')
 return redirect('article',pk=pk)
@login_required
@require_POST
def feedback(request,pk):
 a=get_object_or_404(visible(request.user),pk=pk)
 Feedback.objects.update_or_create(article=a,user=request.user,defaults={'helpful':request.POST.get('helpful')=='yes'})
 messages.success(request,'Obrigado. Sua avaliação foi registrada.')
 return redirect('article',pk=pk)
@login_required
def effective(request,pk):
 a=get_object_or_404(Article,pk=pk)
 if not allowed(request.user,a,'manage'): raise PermissionDenied
 from django.contrib.auth import get_user_model
 value=request.GET.get('user',str(request.user.pk))
 if not value.isdigit(): raise Http404
 user=get_object_or_404(get_user_model(),pk=value)
 from .explanations import explain
 return render(request,'effective_v2.html',{'article':a,'subject':user,'people':get_user_model().objects.order_by('username'),'results':[explain(user,a,action) for action,_ in Rule.ACTIONS]})
