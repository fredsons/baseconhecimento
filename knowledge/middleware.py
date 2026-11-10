import hashlib
from datetime import timedelta
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.signals import user_login_failed,user_logged_in
from django.dispatch import receiver
from django.db.models import F
from .models import LoginAttempt
def key(request,username): return hashlib.sha256(username.lower().strip().encode()).hexdigest()
@receiver(user_login_failed)
def failed(sender,credentials,request,**kwargs):
 if request:
  k=key(request,credentials.get('username','')); obj,_=LoginAttempt.objects.get_or_create(key=k)
  if obj.last<timezone.now()-timedelta(minutes=15): obj.failures=0; obj.save()
  LoginAttempt.objects.filter(pk=obj.pk).update(failures=F('failures')+1,last=timezone.now())
@receiver(user_logged_in)
def success(sender,request,user,**kwargs): LoginAttempt.objects.filter(key=key(request,user.username)).delete()
class LoginGuard:
 def __init__(self,get_response): self.get_response=get_response
 def __call__(self,request):
  if request.path.startswith('/admin/') and request.user.is_authenticated and not request.user.is_superuser:
   from django.shortcuts import redirect
   return redirect('panel')
  if request.method=='POST' and request.path in ['/entrar/','/admin/login/']:
   if LoginAttempt.objects.filter(key=key(request,request.POST.get('username','')),failures__gte=5,last__gt=timezone.now()-timedelta(minutes=15)).exists(): return HttpResponse('Muitas tentativas. Tente novamente em 15 minutos.',status=429)
  return self.get_response(request)
