import hashlib,json,sqlite3
from contextlib import closing
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
class Command(BaseCommand):
    def add_arguments(self,parser): parser.add_argument('directory')
    def handle(self,*args,**opts):
        root=Path(opts['directory'])
        with closing(sqlite3.connect(root/'knowledge.sqlite3')) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise CommandError('Banco corrompido')
            paths=dict(db.execute('SELECT path,sha256 FROM knowledge_version'))
        manifest=json.loads((root/'manifest.json').read_text())
        if set(paths)!=set(manifest): raise CommandError('Manifesto incompleto')
        for path,digest in manifest.items():
            if hashlib.sha256((root/'pdfs'/path).read_bytes()).hexdigest()!=digest or digest!=paths[path]: raise CommandError('PDF inválido: '+path)
        self.stdout.write('Banco e PDFs verificados.')
