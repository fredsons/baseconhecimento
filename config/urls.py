from django.contrib import admin
from django.urls import path,include
from django.contrib.auth import views as auth
from knowledge import views
urlpatterns=[path('admin/',admin.site.urls),path('entrar/',auth.LoginView.as_view(template_name='login.html'),name='login'),path('sair/',auth.LogoutView.as_view(),name='logout'),path('conta/',include('django.contrib.auth.urls')),path('',views.home,name='home'),path('enviar/',views.upload,name='upload'),path('artigos/<int:pk>/',views.detail,name='article'),path('artigos/<int:pk>/pdf/',views.pdf,name='pdf'),path('artigos/<int:pk>/editar/',views.edit,name='edit'),path('artigos/<int:pk>/acao/<str:action>/',views.transition,name='transition'),path('artigos/<int:pk>/feedback/',views.feedback,name='feedback'),path('artigos/<int:pk>/permissoes/',views.effective,name='effective')]

urlpatterns += [path('metricas/',views.metrics,name='metrics'),path('artigos/<int:pk>/regras/',views.rules,name='rules')]
urlpatterns += [path('categorias/<int:pk>/regras/',views.category_rules,name='category_rules')]
urlpatterns += [path('painel/',include('knowledge.panel_urls'))]
from django.conf import settings
if settings.SERVE_STATIC:
 from django.urls import re_path
 from django.views.static import serve
 urlpatterns += [re_path(r'^static/(?P<path>.*)$',serve,{'document_root':settings.STATIC_ROOT})]
