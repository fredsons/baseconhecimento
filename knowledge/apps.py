from django.apps import AppConfig
from django.db.backends.signals import connection_created
def configure(sender,connection,**kwargs):
 if connection.vendor=='sqlite':
  with connection.cursor() as c:
   c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA busy_timeout=20000')
class KnowledgeConfig(AppConfig):
 name='knowledge'
 def ready(self): connection_created.connect(configure,dispatch_uid='sqlite-config')
