import importlib.util,json,subprocess
from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from knowledge.tools import command,environment
class Command(BaseCommand):
    help='Diagnóstico das ferramentas e da configuração sem revelar segredos.'
    def add_arguments(self,parser):
        parser.add_argument('--strict',action='store_true')
    def handle(self,*args,**opts):
        checks={}
        for tool in ['pdftotext','tesseract','ocrmypdf','clamscan']:
            required=tool=='pdftotext' or (settings.OCR_ENABLED and tool in ['tesseract','ocrmypdf']) or (settings.CLAMAV_ENABLED and tool=='clamscan')
            try:
                result=subprocess.run(command(tool)+(['-v'] if tool=='pdftotext' else ['--version']),capture_output=True,timeout=15,env=environment())
                ok=result.returncode==0
            except (OSError,subprocess.TimeoutExpired): ok=False
            checks[tool]={'disponivel':ok,'obrigatorio':required}
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA journal_mode');checks['sqlite_wal']={'disponivel':cursor.fetchone()[0]=='wal','obrigatorio':True}
        except Exception: checks['sqlite_wal']={'disponivel':False,'obrigatorio':True}
        self.stdout.write(json.dumps(checks,ensure_ascii=False,indent=2))
        if opts['strict'] and any(row['obrigatorio'] and not row['disponivel'] for row in checks.values()):raise CommandError('Há ferramentas obrigatórias indisponíveis.')
