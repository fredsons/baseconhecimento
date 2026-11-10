import os,sys
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
DEBUG=os.getenv('DEBUG','0')=='1'
SECRET_KEY=os.getenv('SECRET_KEY','development-only-change-before-deployment')
if not DEBUG and (len(SECRET_KEY)<50 or SECRET_KEY.startswith(('development-','substitua-'))): raise RuntimeError('Configure SECRET_KEY aleatória com pelo menos 50 caracteres ou DEBUG=1 para uso local')
ALLOWED_HOSTS=os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(',')
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','django_q','knowledge.apps.KnowledgeConfig']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','knowledge.middleware.LoginGuard','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['knowledge.context_processors.panel_access','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATA_DIR=Path(os.getenv('DATA_DIR',str(BASE_DIR/'var'))); DATA_DIR.mkdir(parents=True,exist_ok=True)
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':DATA_DIR/'knowledge.sqlite3','CONN_MAX_AGE':60,'OPTIONS':{'timeout':20,'transaction_mode':'IMMEDIATE'}}}
DATABASES['default']['TEST']={'NAME':str(DATA_DIR/'test.sqlite3')}
PRIVATE_ROOT=DATA_DIR/'pdfs'; PRIVATE_ROOT.mkdir(exist_ok=True)
MAX_PDF_BYTES=int(os.getenv('MAX_PDF_BYTES',str(50*1024*1024)))
CLAMAV_ENABLED=os.getenv('CLAMAV_ENABLED','0')=='1'
OCR_ENABLED=os.getenv('OCR_ENABLED','1')=='1'
OCR_LANGUAGES=os.getenv('OCR_LANGUAGES','por+eng')
PDFTOTEXT_COMMAND=os.getenv('PDFTOTEXT_COMMAND','')
OCRMYPDF_COMMAND=os.getenv('OCRMYPDF_COMMAND','')
CLAMSCAN_COMMAND=os.getenv('CLAMSCAN_COMMAND','')
CLAMAV_DATABASE=os.getenv('CLAMAV_DATABASE','')
TESSERACT_COMMAND=os.getenv('TESSERACT_COMMAND','')
Q_CLUSTER={'name':'knowledge','workers':1,'timeout':900,'retry':960,'orm':'default','bulk':1,'recycle':100,'max_attempts':2}
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE='pt-br'; TIME_ZONE='America/Sao_Paulo'; USE_TZ=True
STATIC_URL='/static/'; STATIC_ROOT=BASE_DIR/'staticfiles'; STATICFILES_DIRS=[BASE_DIR/'static']
SERVE_STATIC=os.getenv('SERVE_STATIC','1' if os.name=='nt' else '0')=='1'
if DATA_DIR.resolve().is_relative_to(STATIC_ROOT.resolve()): raise RuntimeError('DATA_DIR não pode ficar dentro da pasta pública.')
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='/entrar/'; LOGIN_REDIRECT_URL='/'; LOGOUT_REDIRECT_URL='/entrar/'
SESSION_COOKIE_SECURE=not DEBUG; CSRF_COOKIE_SECURE=not DEBUG
SECURE_SSL_REDIRECT=not DEBUG; SECURE_HSTS_SECONDS=0 if DEBUG else 31536000
SECURE_CONTENT_TYPE_NOSNIFF=True; X_FRAME_OPTIONS='SAMEORIGIN'
SESSION_COOKIE_HTTPONLY=True
# Somente Nginx local pode alcançar Gunicorn; Nginx sobrescreve o cabeçalho.
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
LOGGING={'version':1,'disable_existing_loggers':False,'handlers':{'audit':{'class':'logging.handlers.RotatingFileHandler','filename':str(DATA_DIR/('test-audit.log' if 'test' in sys.argv else 'audit.log')),'maxBytes':10000000,'backupCount':10}},'loggers':{'audit':{'handlers':['audit'],'level':'INFO','propagate':False}}}

