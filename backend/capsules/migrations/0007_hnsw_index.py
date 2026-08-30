from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('capsules', '0006_capsule_title'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE INDEX hnsw_index_on_embedding ON capsules_documentchunk USING hnsw (embedding vector_cosine_ops);",
            reverse_sql="DROP INDEX IF EXISTS hnsw_index_on_embedding;"
        ),
    ]
