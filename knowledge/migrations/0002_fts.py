from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [('knowledge', '0001_initial')]
    operations = [migrations.RunSQL(
        """CREATE VIRTUAL TABLE article_fts USING fts5(title, description, tags, body, tokenize='unicode61 remove_diacritics 2');
        CREATE TRIGGER article_delete_fts AFTER DELETE ON knowledge_article BEGIN DELETE FROM article_fts WHERE rowid=old.id; END;""",
        "DROP TRIGGER article_delete_fts; DROP TABLE article_fts;")]
