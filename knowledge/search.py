import re
from django.db import connection,transaction
def search(queryset,query):
 words=re.findall(r'[^\W_]+',query,flags=re.UNICODE)[:20]
 if not words: return queryset.none()
 term=' AND '.join('"'+w+'"*' for w in words)
 return queryset.extra(where=['knowledge_article.id IN (SELECT rowid FROM article_fts WHERE article_fts MATCH %s)'],params=[term])
@transaction.atomic
def index(article):
 with connection.cursor() as c:
  c.execute('DELETE FROM article_fts WHERE rowid=%s',[article.pk])
  c.execute('INSERT INTO article_fts(rowid,title,description,tags,body) VALUES (%s,%s,%s,%s,%s)',[article.pk,article.title,article.description,' '.join(article.tags.values_list('name',flat=True)),article.extracted_text])
