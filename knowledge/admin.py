from django.contrib import admin
from .models import Category,Tag,Article,Version,Rule,Feedback,SearchMiss
from .audit import record
class AuditAdmin(admin.ModelAdmin):
 def save_model(self,request,obj,form,change):
  obj.full_clean(); super().save_model(request,obj,form,change); record(request.user,'admin_change',model=obj._meta.label,object=obj.pk)
 def delete_model(self,request,obj):
  record(request.user,'admin_delete',model=obj._meta.label,object=obj.pk); super().delete_model(request,obj)
 def delete_queryset(self,request,queryset):
  for obj in queryset: self.delete_model(request,obj)
@admin.register(Article)
class ArticleAdmin(AuditAdmin):
 list_display=['title','category','status','indexing','review_at']
 list_filter=['status','category','indexing','review_at']
 search_fields=['title','description']
 readonly_fields=['current_version','extracted_text','indexing']
 def save_related(self,request,form,formsets,change):
  super().save_related(request,form,formsets,change)
  from .search import index
  index(form.instance)
 def save_model(self,request,obj,form,change):
  super().save_model(request,obj,form,change)
  from .search import index
  index(obj)
admin.site.register([Category,Tag,Rule],AuditAdmin)
@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
 list_display=['article','created_at','uploaded_by','sha256']
 def has_add_permission(self,request): return False
 def has_change_permission(self,request,obj=None): return False
 def has_delete_permission(self,request,obj=None): return False
admin.site.register([Feedback,SearchMiss])
admin.site.site_header='Conhecimento · Administração'
