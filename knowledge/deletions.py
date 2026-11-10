"""Exclusões com confirmação vinculada ao objeto e nova checagem de dependências."""
import hashlib
from contextlib import nullcontext
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404,redirect,render
from django.http import Http404
from .models import Article,Category,Tag
from .audit import record
from .permissions import visible
from django.views.decorators.http import require_http_methods

TARGETS={'artigo':(Article,'panel_articles'),'categoria':(Category,'panel_categories'),'grupo':(Group,'panel_groups'),'tag':(Tag,'panel_tags')}

def blockers(kind,obj):
    if kind=='artigo':
        result=[]
        if obj.status!='archived': result.append('Arquive o artigo antes de excluí-lo.')
        if obj.indexing in ['pending','processing']: result.append('Aguarde o processamento do PDF terminar antes de excluir.')
        return result
    if kind=='categoria':
        return [label for yes,label in [(obj.category_set.exists(),'Há subcategorias vinculadas.'),(obj.article_set.exists(),'Há artigos nesta categoria.'),(obj.rule_set.exists(),'Remova primeiro as regras de acesso.'),(obj.managers.exists(),'Remova primeiro a delegação de gestão.')] if yes]
    if kind=='grupo':
        return [label for yes,label in [(obj.user_set.exists(),'Há usuários neste grupo.'),(obj.rule_set.exists(),'O grupo possui regras de acesso.'),(obj.managed_categories.exists(),'O grupo é gestor de uma categoria.'),(obj.permissions.exists(),'O grupo possui funções administrativas.')] if yes]
    return ['Esta tag está em uso por artigos.'] if obj.article_set.exists() else []

def fingerprint(kind,obj):
    # Inclui o estado relevante para não confirmar um alvo editado em outra aba.
    values={field.attname:getattr(obj,field.attname) for field in obj._meta.concrete_fields if field.name not in ['extracted_text','indexing_error']}
    return hashlib.sha256(repr((kind,values,blockers(kind,obj))).encode()).hexdigest()

@login_required
@require_http_methods(['GET','POST'])
def delete(request,kind,pk):
    if kind not in TARGETS: raise Http404
    model,back=TARGETS[kind]
    if kind in ['artigo','grupo']:
        if not request.user.is_superuser: raise PermissionDenied
    elif not request.user.is_staff or not request.user.has_perm('knowledge.delete_'+model._meta.model_name): raise PermissionDenied
    with (transaction.atomic() if request.method=='POST' else nullcontext()):
        obj=get_object_or_404(model,pk=pk)
        reasons=blockers(kind,obj)
        current=fingerprint(kind,obj)
        token=signing.dumps({'kind':kind,'pk':pk,'state':current,'actor':request.user.pk},salt='delete-confirmation')
        if request.method=='POST':
            try:
                signed=signing.loads(request.POST.get('token',''),salt='delete-confirmation',max_age=600)
                valid=signed=={'kind':kind,'pk':pk,'state':current,'actor':request.user.pk} and request.POST.get('confirm')=='yes'
            except signing.BadSignature: valid=False
            if not valid:
                return render(request,'delete_confirm.html',{'object':obj,'kind':kind,'back':back,'blockers':reasons,'token':token,'error':'A confirmação expirou ou o registro mudou. Revise e confirme novamente.'},status=400)
            if not reasons:
                label=str(obj)
                try:obj.delete()
                except ProtectedError:reasons=['Existem registros vinculados. Nada foi excluído.']
                else:
                    record(request.user,'delete',kind=kind,target=pk,label=label)
                    messages.success(request,f'{label}: exclusão concluída.');return redirect(back)
            messages.error(request,'Não foi possível excluir. Resolva as dependências indicadas.')
        return render(request,'delete_confirm.html',{'object':obj,'kind':kind,'back':back,'blockers':reasons,'token':token})
