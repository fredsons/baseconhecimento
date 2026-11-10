import io,os,subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from pypdf import PdfReader,PdfWriter
from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
from .models import Article,Category,Version
from .uploads import attach
from .tasks import extract
from .tools import command
from .search import search
from .tests import pdf_bytes

def digital_pdf():
    writer=PdfWriter();page=writer.add_blank_page(width=595,height=842)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    text=DecodedStreamObject();text.set_data(b'BT /F1 22 Tf 50 700 Td (PROCEDIMENTO DIGITAL 7429) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(text)
    output=io.BytesIO();writer.write(output);return output.getvalue()

class ProcessingTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('editor',is_staff=True,is_superuser=True)
        self.category=Category.objects.create(name='Base')
        self.a=Article.objects.create(title='Documento',category=self.category,owner=self.user)
    def test_missing_program_records_error_and_preserves_pdf(self):
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)),patch('knowledge.uploads.async_task'):
            version=attach(self.a,SimpleUploadedFile('a.pdf',pdf_bytes()),self.user)
            with patch('knowledge.tasks.run',side_effect=FileNotFoundError()):
                with self.assertRaises(FileNotFoundError):extract(version.pk)
            self.a.refresh_from_db();self.assertEqual(self.a.indexing,'error');self.assertTrue(self.a.indexing_error)
            self.assertTrue((Path(tmp)/version.path).exists())
    def test_old_version_cannot_overwrite_current_text(self):
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)),patch('knowledge.uploads.async_task'):
            old=attach(self.a,SimpleUploadedFile('a.pdf',digital_pdf()),self.user)
            new=attach(self.a,SimpleUploadedFile('b.pdf',digital_pdf()),self.user)
            with patch('knowledge.tasks.run') as run:extract(old.pk);run.assert_not_called()
            self.a.refresh_from_db();self.assertEqual(self.a.current_version_id,new.pk)
    def test_retry_failure_preserves_state(self):
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)),patch('knowledge.uploads.async_task'):
            attach(self.a,SimpleUploadedFile('a.pdf',digital_pdf()),self.user)
            self.a.indexing='error';self.a.indexing_error='falha original';self.a.save()
            self.client.force_login(self.user)
            with patch('django_q.tasks.async_task',side_effect=RuntimeError('offline')):
                self.assertEqual(self.client.post(f'/painel/processamento/{self.a.pk}/repetir/').status_code,302)
            self.a.refresh_from_db();self.assertEqual(self.a.indexing_error,'falha original');self.assertEqual(self.a.indexing,'error')
    def test_retry_queues_once_and_processing_screen(self):
        from django_q.models import OrmQ
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)),patch('knowledge.uploads.async_task'):
            attach(self.a,SimpleUploadedFile('a.pdf',digital_pdf()),self.user)
            self.a.indexing='error';self.a.save();self.client.force_login(self.user)
            self.assertEqual(self.client.post(f'/painel/processamento/{self.a.pk}/repetir/').status_code,302)
            count=OrmQ.objects.count();self.assertEqual(count,1)
            self.assertEqual(self.client.post(f'/painel/processamento/{self.a.pk}/repetir/').status_code,302)
            self.assertEqual(OrmQ.objects.count(),count)
            self.assertContains(self.client.get('/painel/processamento/'),'Na fila')
    def test_audit_is_readable_and_escapes_values(self):
        import json
        with TemporaryDirectory() as tmp,override_settings(DATA_DIR=Path(tmp)):
            (Path(tmp)/'audit.log').write_text(json.dumps({'at':'2026-11-10T12:00:00Z','user':self.user.pk,'event':'upload','article':self.a.pk,'detail':'<script>alert(1)</script>'})+'\n')
            self.client.force_login(self.user)
            response=self.client.get('/painel/auditoria/')
            self.assertContains(response,'Enviou artigo');self.assertNotContains(response,'<script>alert(1)</script>')
    def test_replacement_preserves_publication_from_concurrent_update(self):
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)),patch('knowledge.uploads.async_task'):
            Article.objects.filter(pk=self.a.pk).update(status='published')
            attach(self.a,SimpleUploadedFile('a.pdf',digital_pdf()),self.user)
            self.a.refresh_from_db();self.assertEqual(self.a.status,'published')
    def test_metadata_edit_preserves_extracted_text(self):
        from .forms import ArticleForm
        self.client.force_login(self.user)
        def concurrent_form(*args,**kwargs):
            form=ArticleForm(*args,**kwargs)
            Article.objects.filter(pk=self.a.pk).update(extracted_text='Texto novo 9837',indexing='ready')
            return form
        with patch('knowledge.views.ArticleForm',side_effect=concurrent_form):
            response=self.client.post(f'/artigos/{self.a.pk}/editar/',{'title':'Novo título','description':'Atualizado','category':self.category.pk,'review_at':''})
        self.assertEqual(response.status_code,302)
        self.a.refresh_from_db();self.assertIn('9837',self.a.extracted_text)
        self.assertTrue(search(Article.objects.all(),'9837').filter(pk=self.a.pk).exists())

@skipUnless(os.getenv('ACERVO_INTEGRATION')=='1','Ferramentas externas: defina ACERVO_INTEGRATION=1')
class RealToolsTests(TestCase):
    setUp=ProcessingTests.setUp
    def test_poppler_extracts_and_indexes_real_pdf(self):
        with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp)),patch('knowledge.uploads.async_task'):
            version=attach(self.a,SimpleUploadedFile('a.pdf',digital_pdf()),self.user)
            extract(version.pk);self.a.refresh_from_db()
            self.assertEqual(self.a.indexing,'ready');self.assertIn('7429',self.a.extracted_text)
            self.assertTrue(search(Article.objects.all(),'7429').exists())
    def test_ocr_on_scanned_and_mixed_pdf(self):
        from PIL import Image,ImageDraw,ImageFont
        image=Image.new('RGB',(1600,1000),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',64)
        draw.text((100,180),'PROTOCOLO ESCANEADO 8531',font=font,fill='black')
        scanned=io.BytesIO();image.save(scanned,format='PDF',resolution=150)
        for mixed in [False,True]:
            writer=PdfWriter()
            if mixed: writer.append(PdfReader(io.BytesIO(digital_pdf())))
            writer.append(PdfReader(io.BytesIO(scanned.getvalue())))
            content=io.BytesIO();writer.write(content)
            with TemporaryDirectory() as tmp,override_settings(PRIVATE_ROOT=Path(tmp),OCR_ENABLED=True),patch('knowledge.uploads.async_task'):
                version=attach(self.a,SimpleUploadedFile('scanned.pdf',content.getvalue()),self.user)
                extract(version.pk);self.a.refresh_from_db()
                self.assertEqual(self.a.indexing,'ready');self.assertIn('8531',self.a.extracted_text)
                if mixed: self.assertIn('7429',self.a.extracted_text)
    def test_clamav_accepts_clean_and_rejects_test_signature(self):
        marker=b'ACERVO_TEST_SIGNATURE_49867352'
        with TemporaryDirectory() as tmp:
            root=Path(tmp);database=root/'test.ndb'
            database.write_text('Acervo.Test:0:*:'+marker.hex()+'\n')
            files=root/'pdfs';files.mkdir()
            with override_settings(PRIVATE_ROOT=files,CLAMAV_ENABLED=True,CLAMAV_DATABASE=str(database)),patch('knowledge.uploads.async_task'):
                clean=attach(self.a,SimpleUploadedFile('clean.pdf',digital_pdf()),self.user)
                with self.assertRaises(ValidationError):attach(self.a,SimpleUploadedFile('test.pdf',digital_pdf()+marker),self.user)
                self.a.refresh_from_db();self.assertEqual(self.a.current_version_id,clean.pk);self.assertEqual(len(list(files.iterdir())),1)

