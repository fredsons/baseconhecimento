from django.db.models import Q,Exists,OuterRef
from django.utils import timezone
from .models import Article,Rule,Category
def active(user,action):
 return Rule.objects.filter(group__in=user.groups.all(),action=action).filter(Q(expires_at__isnull=True)|Q(expires_at__gt=timezone.now()))
def category_ids(category):
 ids=[]
 while category:
  ids.append(category.pk); category=category.parent
 return ids
def category_allowed(user,category,action):
 if not user.is_active: return False
 if user.is_superuser: return True
 rules=active(user,action).filter(category_id__in=category_ids(category))
 if rules.filter(deny=True).exists(): return False
 if rules.filter(deny=False).exists(): return True
 return action=='manage' and Category.objects.filter(pk__in=category_ids(category),managers__in=user.groups.all()).exists()
def granted(user,action='view'):
 if not user.is_authenticated or not user.is_active: return Article.objects.none()
 if user.is_superuser: return Article.objects.all()
 # Three category levels, correlated subqueries: filtering takes place in SQL.
 inherited=active(user,action).filter(Q(category_id=OuterRef('category_id'))|Q(category_id=OuterRef('category__parent_id'))|Q(category_id=OuterRef('category__parent__parent_id')))
 direct=active(user,action).filter(article_id=OuterRef('pk'))
 return Article.objects.annotate(_direct=Exists(direct),_allow=Exists(direct.filter(deny=False)),_deny=Exists(direct.filter(deny=True)),_inherited_allow=Exists(inherited.filter(deny=False)),_inherited_deny=Exists(inherited.filter(deny=True))).filter(Q(_direct=True,_allow=True,_deny=False)|Q(_direct=False,_inherited_allow=True,_inherited_deny=False))

def visible(user,action='view'):
 qs=granted(user,action)
 if not user.is_authenticated or user.is_superuser: return qs
 if action not in ['view','download']: return qs
 # Publicação é uma barreira adicional à concessão de leitura, aplicada em SQL.
 editorial=granted(user,'edit').values('pk').union(granted(user,'publish').values('pk'),granted(user,'archive').values('pk'))
 return qs.filter(Q(status='published')|Q(pk__in=editorial))
def allowed(user,article,action):
 if action=='manage' and category_allowed(user,article.category,'manage'):
  rules=active(user,action).filter(article=article)
  if rules.exists(): return rules.filter(deny=False).exists() and not rules.filter(deny=True).exists()
  return True
 if action in ['edit','publish','archive','download'] and not visible(user).filter(pk=article.pk).exists(): return False
 return visible(user,action).filter(pk=article.pk).exists()
