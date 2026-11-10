from django.core.management.base import BaseCommand,CommandError
class Command(BaseCommand):
    help='Servidor Windows com Waitress; use 127.0.0.1 para acesso local ou proxy HTTPS.'
    def add_arguments(self,parser):
        parser.add_argument('--host',default='127.0.0.1')
        parser.add_argument('--port',type=int,default=8000)
    def handle(self,*args,**opts):
        from django.conf import settings
        try: from waitress import serve
        except ImportError as exc: raise CommandError('Instale requirements.txt neste ambiente Windows.') from exc
        from config.wsgi import application
        self.stdout.write(f'Acervo em http://{opts["host"]}:{opts["port"]}')
        serve(application,host=opts['host'],port=opts['port'],threads=4,max_request_body_size=settings.MAX_PDF_BYTES+2*1024*1024,clear_untrusted_proxy_headers=True,trusted_proxy='127.0.0.1',trusted_proxy_headers={'x-forwarded-proto'})
