from django.db import migrations

def repair_schema(apps, schema_editor):
    """
    Database-only repair:
    - Thêm cột thiếu vào shop_product: compare_price, is_active, updated_at
    - Tạo bảng shop_consultationrequest nếu chưa có
    - Tạo index cho (status, created_at)
    """
    conn = schema_editor.connection
    cursor = conn.cursor()

    # ===== helpers =====
    def table_exists(name: str) -> bool:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=%s",
            [name],
        )
        return cursor.fetchone() is not None

    def columns_of(table: str):
        # trả về set tên cột của bảng
        cols = set()
        try:
            for col in conn.introspection.get_table_description(cursor, table):
                cols.add(col.name)
        except Exception:
            pass
        return cols

    # ===== 1) shop_product: bổ sung cột còn thiếu =====
    if table_exists("shop_product"):
        cols = columns_of("shop_product")

        if "compare_price" not in cols:
            # Decimal trên SQLite -> NUMERIC NULL
            schema_editor.execute(
                "ALTER TABLE shop_product ADD COLUMN compare_price NUMERIC NULL"
            )

        if "is_active" not in cols:
            # Boolean trên SQLite -> INTEGER 0/1
            schema_editor.execute(
                "ALTER TABLE shop_product ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
            )

        if "updated_at" not in cols:
            # auto_now -> để NULL, Django sẽ set khi save
            schema_editor.execute(
                "ALTER TABLE shop_product ADD COLUMN updated_at DATETIME NULL"
            )

    # ===== 2) shop_consultationrequest: tạo bảng nếu thiếu =====
    if not table_exists("shop_consultationrequest"):
        schema_editor.execute("""
            CREATE TABLE shop_consultationrequest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL
                    REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED,
                product_id INTEGER NOT NULL
                    REFERENCES shop_product(id) DEFERRABLE INITIALLY DEFERRED,
                note VARCHAR(255),
                status VARCHAR(16) NOT NULL DEFAULT 'pending',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # index cho (status, created_at DESC)
        schema_editor.execute("""
            CREATE INDEX IF NOT EXISTS shop_consult_status_created_idx
            ON shop_consultationrequest (status, created_at DESC)
        """)

def noop(apps, schema_editor):
    # không rollback
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(repair_schema, reverse_code=noop),
    ]
