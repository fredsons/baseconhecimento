"""Instala dependências públicas fixadas; nunca carrega PDF privado pela rede."""
import hashlib
import urllib.request
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError

ASSETS={
    'pdf.mjs':'a209a2124baa35cbb9015b809926f1bcec9dd1c247296290e205dd9d76cb9128',
    'pdf.worker.mjs':'7c237f83fa56bce645d8af51d183c9c56ba7b2d2928ff42754dc7020bea36323',
}
class Command(BaseCommand):
    help='Prepara PDF.js local com versão e SHA-256 fixados.'
    def add_arguments(self,parser):parser.add_argument('--check',action='store_true')
    def handle(self,*args,**options):
        folder=settings.BASE_DIR/'static'/'vendor';folder.mkdir(parents=True,exist_ok=True)
        for name,digest in ASSETS.items():
            target=folder/name
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise CommandError('Hash inesperado em '+name)
                continue
            if options['check']:raise CommandError('Recurso ausente: '+name)
            url='https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/'+name
            try:
                with urllib.request.urlopen(url,timeout=45) as response:data=response.read(8*1024*1024)
            except OSError as exc:raise CommandError('Não foi possível baixar '+name) from exc
            if hashlib.sha256(data).hexdigest()!=digest:raise CommandError('Download rejeitado: hash inesperado em '+name)
            temporary=target.with_suffix(target.suffix+'.tmp')
            try:temporary.write_bytes(data);temporary.replace(target)
            finally:temporary.unlink(missing_ok=True)
        self.stdout.write('PDF.js local verificado.')
