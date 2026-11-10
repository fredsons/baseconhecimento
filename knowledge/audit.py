import json,logging
from django.utils import timezone
def record(user,event,article=None,**extra):
 logging.getLogger('audit').info(json.dumps({'at':timezone.now().isoformat(),'user':user.pk,'event':event,'article':getattr(article,'pk',None),**extra},ensure_ascii=False))
