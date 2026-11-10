from django import forms
from .models import Article,Rule
class RuleForm(forms.ModelForm):
 deny=forms.TypedChoiceField(label='Acesso',choices=[('False','Permitir'),('True','Bloquear')],coerce=lambda value: value=='True',initial='False')
 class Meta:
  model=Rule
  fields=['group','action','deny','expires_at']
  labels={'group':'Grupo / departamento','action':'Ação','deny':'Negar acesso','expires_at':'Acesso válido até (opcional)'}
  widgets={'expires_at':forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local'})}
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.fields['group'].empty_label='Selecione um grupo'
  self.fields['action'].choices=[('','Selecione uma ação'),('view','Visualizar'),('download','Baixar PDF'),('upload','Enviar artigo'),('edit','Editar'),('publish','Publicar'),('archive','Arquivar'),('manage','Gerenciar permissões')]
class ArticleForm(forms.ModelForm):
 pdf=forms.FileField(label='Arquivo PDF',required=True)
 class Meta:
  model=Article
  fields=['title','description','category','tags','review_at']
  widgets={'review_at':forms.DateTimeInput(attrs={'type':'datetime-local'})}
class ReplacementForm(forms.Form): pdf=forms.FileField(label='Novo PDF')
