from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db_meta", "0067_cluster_bk_cloud_region_cluster_cloud_zone_list_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mysqldtscluster",
            name="status",
            field=models.CharField(
                choices=[
                    ("deploying", "deploying"),
                    ("running", "running"),
                    ("destroying", "destroying"),
                    ("destroyed", "destroyed"),
                ],
                default="deploying",
                max_length=32,
                verbose_name="状态",
            ),
        ),
    ]
