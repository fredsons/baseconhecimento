from .models import Rule
from .permissions import active,allowed,category_ids,granted,category_allowed

LABELS={'view':'Visualizar','download':'Baixar PDF','upload':'Enviar artigo','edit':'Editar','publish':'Publicar','archive':'Arquivar','manage':'Gerenciar permissões'}

def explain(user,article,action):
    base={'action':LABELS[action],'allowed':allowed(user,article,action),'rules':[]}
    if not user.is_active:return {**base,'allowed':False,'reason':'Conta desativada: esta pessoa não pode entrar no sistema.'}
    if user.is_superuser:
        return {**base,'reason':'Administrador principal: acesso completo.'}
    own=active(user,action).filter(article=article).select_related('group','category')
    inherited=active(user,action).filter(category_id__in=category_ids(article.category)).select_related('group','category')
    chosen=list(own) or list(inherited)
    reasons=[f'{r.group.name}: {"bloquear" if r.deny else "permitir"} em '+('este artigo' if r.article_id else r.category.name) for r in chosen]
    if action=='manage' and not list(own) and category_allowed(user,article.category,'manage'):
        reason='Gestão concedida na categoria, por regra ou grupo gestor.'
    elif any(r.deny for r in chosen): reason='Bloqueado: uma negação explícita prevalece neste conjunto de regras.'
    elif chosen: reason='Permitido por regra própria do artigo.' if list(own) else 'Permitido por regra herdada da categoria.'
    else: reason='Negado: nenhum dos grupos desta pessoa possui concessão aplicável.'
    if granted(user,action).filter(pk=article.pk).exists() and not base['allowed']:
        if action in ['edit','publish','archive','download'] and not granted(user,'view').filter(pk=article.pk).exists():
            reason='Negado: esta ação também exige permissão para visualizar o artigo.'
        elif article.status!='published' and action in ['view','download']:
            reason='Conteúdo não publicado: esta pessoa não tem função editorial neste artigo.'
    return {**base,'reason':reason,'rules':reasons}
