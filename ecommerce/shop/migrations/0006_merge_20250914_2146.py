# shop/migrations/0006_merge_*.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0004_consult_add_phone_and_handler'),
        ('shop', '0005_consult_add_missing_columns'),
    ]
    operations = []   # merge chỉ hợp nhất đồ thị, không làm gì thêm
