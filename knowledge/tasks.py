import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from pypdf import PdfReader
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Article, Version
from .search import index
from .tools import command,environment

def run(args, timeout):
    return subprocess.run(args,capture_output=True,check=True,timeout=timeout,env=environment())

def extract(version_id):
    version=Version.objects.filter(pk=version_id).first()
    if not version: return
    started=timezone.now()
    with transaction.atomic():
        article=Article.objects.get(pk=version.article_id)
        if article.current_version_id!=version.pk: return
        if article.indexing=='processing' and article.processing_started_at and article.processing_started_at>started-timedelta(minutes=20): return
        article.indexing='processing';article.processing_started_at=started;article.indexing_error=''
        article.save(update_fields=['indexing','processing_started_at','indexing_error'])
    try:
        path=settings.PRIVATE_ROOT/version.path
        text=run(command('pdftotext')+['-enc','UTF-8',str(path),'-'],120).stdout.decode('utf-8','replace')
        needs_ocr=settings.OCR_ENABLED and any(not (page.extract_text() or '').strip() for page in PdfReader(path).pages)
        if needs_ocr:
            with tempfile.TemporaryDirectory() as tmp:
                target=Path(tmp)/'ocr.pdf'
                run(command('ocrmypdf')+['--skip-text','--output-type','pdf','--optimize','0','--jobs','1','-l',settings.OCR_LANGUAGES,str(path),str(target)],600)
                text=run(command('pdftotext')+['-enc','UTF-8',str(target),'-'],120).stdout.decode('utf-8','replace')
        with transaction.atomic():
            article.refresh_from_db()
            if article.current_version_id!=version.pk or article.processing_started_at!=started: return
            article.extracted_text=text;article.indexing='ready';article.indexing_error='';article.indexed_at=timezone.now()
            article.save(update_fields=['extracted_text','indexing','indexing_error','indexed_at'])
            index(article)
    except Exception as exc:
        if isinstance(exc,FileNotFoundError): message='Ferramenta de extração não encontrada. Confira os caminhos no diagnóstico.'
        elif isinstance(exc,subprocess.TimeoutExpired): message='O processamento excedeu o tempo limite.'
        elif isinstance(exc,subprocess.CalledProcessError): message=(exc.stderr or b'Falha ao processar o PDF.').decode('utf-8','replace')[-2000:]
        else: message=str(exc)[-2000:]
        Article.objects.filter(pk=article.pk,current_version=version,processing_started_at=started).update(indexing='error',indexing_error=message)
        raise
