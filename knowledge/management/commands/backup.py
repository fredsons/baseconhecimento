import hashlib,json,shutil,sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime,timezone
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError

class Command(BaseCommand):
    help='Snapshot SQLite consistente e cópia dos PDFs imutáveis, com verificação.'
    def add_arguments(self,parser): parser.add_argument('destination')
    def handle(self,*args,**options):
        target=Path(options['destination']).resolve()/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        if target.is_relative_to(settings.DATA_DIR.resolve()): raise CommandError('Backup deve ficar fora de DATA_DIR.')
        target.mkdir(parents=True)
        with closing(sqlite3.connect(settings.DATABASES['default']['NAME'])) as src,closing(sqlite3.connect(target/'knowledge.sqlite3')) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise CommandError('Falha na integridade.')
            paths=dict(dst.execute('SELECT path,sha256 FROM knowledge_version'))
        (target/'pdfs').mkdir()
        manifest={}
        for path in paths:
            source=settings.PRIVATE_ROOT/path; dest=target/'pdfs'/path
            shutil.copy2(source,dest)
            manifest[path]=hashlib.sha256(dest.read_bytes()).hexdigest()
            if manifest[path]!=paths[path]: raise CommandError('O PDF não corresponde à versão registrada: '+path)
        (target/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        self.stdout.write(str(target))
