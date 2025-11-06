from django.db import migrations

def add_missing_columns(apps, schema_editor):
    conn = schema_editor.connection
    cursor = conn.cursor()

    def cols(table):
        try:
            return {c.name for c in conn.introspection.get_table_description(cursor, table)}
        except Exception:
            return set()

    tbl = "shop_consultationrequest"
    if "customer_phone" not in cols(tbl):
        schema_editor.execute(
            "ALTER TABLE shop_consultationrequest ADD COLUMN customer_phone VARCHAR(40) NULL"
        )
    if "handled_by_id" not in cols(tbl):
        schema_editor.execute(
            "ALTER TABLE shop_consultationrequest "
            "ADD COLUMN handled_by_id INTEGER NULL "
            "REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED"
        )
    if "handled_at" not in cols(tbl):
        schema_editor.execute(
            "ALTER TABLE shop_consultationrequest ADD COLUMN handled_at DATETIME NULL"
        )

def noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0002_repair_schema'),  # nếu tên khác, đổi cho khớp migration trước đó
    ]
    operations = [
        migrations.RunPython(add_missing_columns, reverse_code=noop),
    ]
