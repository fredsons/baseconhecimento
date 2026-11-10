"""Teste isolado de fila, extração e restauração; não toca no banco da instalação."""
import os,sys,tempfile,subprocess,io,shutil,secrets
from pathlib import Path

def main():
    root=Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='acervo-runtime-') as scratch:
        temp=Path(scratch);data=temp/'data';data.mkdir()
        os.environ.update(DEBUG='1',DATA_DIR=str(data),DJANGO_SETTINGS_MODULE='config.settings',SECRET_KEY=secrets.token_urlsafe(64))
        sys.path.insert(0,str(root))
        import django;django.setup()
        from django.core.management import call_command
        from django.contrib.auth.models import User
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import Client
        from django.db import connections
        from knowledge.models import Article,Category
        from knowledge.uploads import attach
        from knowledge.test_processing import digital_pdf
        from knowledge.search import search
        call_command('migrate',verbosity=0)
        user=User.objects.create_user('verificacao',password='Runtime-test-4938!',is_superuser=True,is_staff=True)
        category=Category.objects.create(name='Procedimentos')
        article=Article(title='Procedimento',owner=user,category=category,status='published')
        attach(article,SimpleUploadedFile('procedimento.pdf',digital_pdf()),user)
        try:
            for _ in range(3):
                result=subprocess.run([sys.executable,str(root/'manage.py'),'qcluster','--run-once'],cwd=root,env=os.environ.copy(),capture_output=True,timeout=90)
                if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))
                article.refresh_from_db()
                if article.indexing=='ready':break
            assert article.indexing=='ready',article.indexing_error
            assert search(Article.objects.all(),'7429').exists()
            client=Client();assert client.login(username=user.username,password='Runtime-test-4938!')
            response=client.get(f'/artigos/{article.pk}/pdf/',HTTP_RANGE='bytes=0-31')
            assert response.status_code==206 and len(b''.join(response.streaming_content))==32
            output=io.StringIO();call_command('backup',str(temp/'backup'),stdout=output)
            backup=Path(output.getvalue().strip());call_command('verify_backup',str(backup))
            restored=temp/'restored';restored.mkdir();shutil.copy2(backup/'knowledge.sqlite3',restored/'knowledge.sqlite3');shutil.copytree(backup/'pdfs',restored/'pdfs')
            env=os.environ.copy();env['DATA_DIR']=str(restored)
            code="from django.test import Client;from knowledge.search import search;from knowledge.models import Article;c=Client();assert c.login(username='verificacao',password='Runtime-test-4938!');a=search(Article.objects.all(),'7429').first();assert a;r=c.get('/artigos/%s/pdf/'%a.pk);assert r.status_code==200;assert b''.join(r.streaming_content).startswith(b'%PDF-')"
            result=subprocess.run([sys.executable,str(root/'manage.py'),'shell','-c',code],env=env,capture_output=True,timeout=30)
            if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))
            print('OK: worker real, extração, busca, PDF parcial e restauração com login/busca/PDF.')
        finally:
            connections.close_all()
            import logging;logging.shutdown()

if __name__=='__main__':main()
