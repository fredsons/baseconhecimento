from django.urls import path
from . import panel

urlpatterns=[
    path('processamento/',panel.processing,name='panel_processing'),
    path('processamento/<int:pk>/repetir/',panel.retry_processing,name='panel_retry'),
    path('auditoria/',panel.audit,name='panel_audit'),
    path('',panel.dashboard,name='panel'),
    path('artigos/',panel.articles,name='panel_articles'),
    path('categorias/',panel.categories,name='panel_categories'),
    path('categorias/nova/',panel.category_edit,name='panel_category_new'),
    path('categorias/<int:pk>/',panel.category_edit,name='panel_category_edit'),
    path('usuarios/',panel.users,name='panel_users'),
    path('usuarios/novo/',panel.user_edit,name='panel_user_new'),
    path('usuarios/<int:pk>/',panel.user_edit,name='panel_user_edit'),
    path('grupos/',panel.groups,name='panel_groups'),
    path('grupos/novo/',panel.group_edit,name='panel_group_new'),
    path('grupos/<int:pk>/',panel.group_edit,name='panel_group_edit'),
    path('tags/',panel.tags,name='panel_tags'),
    path('tags/nova/',panel.tag_edit,name='panel_tag_new'),
    path('tags/<int:pk>/',panel.tag_edit,name='panel_tag_edit'),
]
