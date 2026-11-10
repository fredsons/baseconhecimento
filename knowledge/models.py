from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
class Category(models.Model):
 name=models.CharField('nome',max_length=160)
 parent=models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT,verbose_name='categoria superior')
 managers=models.ManyToManyField('auth.Group',blank=True,related_name='managed_categories',verbose_name='grupos gestores')
 def clean(self):
  seen={self.pk}; node=self.parent; depth=1
  while node:
   if node.pk in seen: raise ValidationError('Hierarquia circular.')
   seen.add(node.pk); depth+=1; node=node.parent
  if depth>3: raise ValidationError('Máximo de três níveis.')
  if self.pk and self.category_set.exists() and depth>1:
   def height(c): return 1+max([height(x) for x in c.category_set.all()] or [0])
   if depth+height(self)-1>3: raise ValidationError('Descendentes excederiam três níveis.')
 def __str__(self): return self.name
class Tag(models.Model):
 name=models.CharField('nome',max_length=60,unique=True)
 def __str__(self): return self.name
class Article(models.Model):
 STATUS=[('draft','Rascunho'),('published','Publicado'),('archived','Arquivado')]
 title=models.CharField('título',max_length=240)
 description=models.TextField('descrição',blank=True,max_length=1000)
 category=models.ForeignKey(Category,on_delete=models.PROTECT,verbose_name='categoria')
 tags=models.ManyToManyField(Tag,blank=True)
 owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,verbose_name='responsável')
 status=models.CharField('status',max_length=12,choices=STATUS,default='draft')
 published_at=models.DateTimeField('publicado em',null=True,blank=True)
 updated_at=models.DateTimeField('atualizado em',auto_now=True)
 review_at=models.DateTimeField('revisar em',null=True,blank=True)
 indexing=models.CharField(max_length=20,default='pending')
 indexing_error=models.TextField(blank=True)
 queued_at=models.DateTimeField(null=True,blank=True)
 processing_started_at=models.DateTimeField(null=True,blank=True)
 indexed_at=models.DateTimeField(null=True,blank=True)
 extracted_text=models.TextField(blank=True)
 current_version=models.ForeignKey('Version',null=True,blank=True,on_delete=models.SET_NULL,related_name='+')
 def __str__(self): return self.title
class Version(models.Model):
 article=models.ForeignKey(Article,on_delete=models.CASCADE,related_name='versions')
 path=models.CharField(max_length=255)
 sha256=models.CharField(max_length=64)
 uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
 created_at=models.DateTimeField(auto_now_add=True)
class Rule(models.Model):
 ACTIONS=[(s,s) for s in ['view','download','upload','edit','publish','archive','manage']]
 group=models.ForeignKey('auth.Group',on_delete=models.CASCADE)
 category=models.ForeignKey(Category,null=True,blank=True,on_delete=models.CASCADE)
 article=models.ForeignKey(Article,null=True,blank=True,on_delete=models.CASCADE)
 action=models.CharField(max_length=10,choices=ACTIONS)
 deny=models.BooleanField(default=False)
 expires_at=models.DateTimeField(null=True,blank=True)
 class Meta:
  constraints=[models.CheckConstraint(condition=(models.Q(category__isnull=False,article__isnull=True)|models.Q(category__isnull=True,article__isnull=False)),name='one_rule_target')]
class Feedback(models.Model):
 article=models.ForeignKey(Article,on_delete=models.CASCADE)
 user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 helpful=models.BooleanField()
 class Meta: constraints=[models.UniqueConstraint(fields=['article','user'],name='one_feedback')]
class LoginAttempt(models.Model):
 key=models.CharField(max_length=64,unique=True)
 failures=models.PositiveIntegerField(default=0)
 last=models.DateTimeField(auto_now=True)
class SearchMiss(models.Model):
 query=models.CharField(max_length=200)
 created_at=models.DateTimeField(auto_now_add=True)
