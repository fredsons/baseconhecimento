import hashlib,uuid,subprocess
from pathlib import Path
from pypdf import PdfReader
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django_q.tasks import async_task
from .models import Version
from .search import index
from django.utils import timezone
from .tools import command
def validate(upload):
 if upload.size>settings.MAX_PDF_BYTES: raise ValidationError('PDF excede o limite de tamanho.')
 if upload.read(5)!=b'%PDF-': raise ValidationError('O arquivo não é um PDF válido.')
 upload.seek(0)
 try:
  reader=PdfReader(upload,strict=True)
  if reader.is_encrypted or not len(reader.pages): raise ValueError()
 except Exception: raise ValidationError('PDF inválido, vazio ou protegido por senha.')
 finally: upload.seek(0)
def attach(article,upload,user):
 validate(upload)
 filename=uuid.uuid4().hex+'.pdf'; path=settings.PRIVATE_ROOT/filename
 digest=hashlib.sha256()
 try:
  with path.open('xb') as f:
   for chunk in upload.chunks(): digest.update(chunk); f.write(chunk)
  if settings.CLAMAV_ENABLED:
   scan=command('clamscan')+['--no-summary']
   if settings.CLAMAV_DATABASE: scan+=['--database',settings.CLAMAV_DATABASE]
   try: subprocess.run(scan+[str(path)],check=True,capture_output=True,timeout=120)
   except (subprocess.SubprocessError,OSError): raise ValidationError('Verificação antivírus rejeitou o arquivo ou está indisponível. Consulte a administração.')
  with transaction.atomic():
   if article.pk:
    # Não sobrescrever publicação, categoria ou versão com um objeto desatualizado.
    article.save(update_fields=['title','description','review_at','updated_at'])
    article.refresh_from_db()
   else: article.save()
   v=Version.objects.create(article=article,path=filename,sha256=digest.hexdigest(),uploaded_by=user)
   article.current_version=v; article.indexing='pending'; article.extracted_text=''
   article.indexing_error='';article.queued_at=timezone.now();article.processing_started_at=None;article.indexed_at=None;article.save()
   index(article)
   # O broker ORM usa a mesma conexão: artigo, versão e fila confirmam juntos.
   try: async_task('knowledge.tasks.extract',v.pk)
   except Exception as exc: raise ValidationError('Não foi possível agendar a extração. O envio não foi salvo; tente novamente.') from exc
  return v
 except Exception:
  path.unlink(missing_ok=True); raise
