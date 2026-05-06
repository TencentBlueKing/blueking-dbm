import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db_meta", "0062_mongodbstorageinstanceext"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mongodbstorageinstanceext",
            name="instance",
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="db_meta.storageinstance"),
        ),
    ]
