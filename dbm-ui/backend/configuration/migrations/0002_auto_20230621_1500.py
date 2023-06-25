# Generated by Django 3.2.19 on 2023-06-21 07:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dbadministrator",
            name="db_type",
            field=models.CharField(
                choices=[
                    ("mysql", "MySQL"),
                    ("tendbcluster", "TendbCluster"),
                    ("redis", "Redis"),
                    ("kafka", "Kafka"),
                    ("hdfs", "HDFS"),
                    ("es", "ElasticSearch"),
                    ("pulsar", "Pulsar"),
                    ("influxdb", "InfluxDB"),
                    ("cloud", "Cloud"),
                ],
                max_length=32,
                verbose_name="数据库类型",
            ),
        ),
        migrations.AlterField(
            model_name="passwordpolicy",
            name="account_type",
            field=models.CharField(
                choices=[
                    ("mysql", "MySQL"),
                    ("tendbcluster", "TendbCluster"),
                    ("redis", "Redis"),
                    ("kafka", "Kafka"),
                    ("hdfs", "HDFS"),
                    ("es", "ElasticSearch"),
                    ("pulsar", "Pulsar"),
                    ("influxdb", "InfluxDB"),
                    ("cloud", "Cloud"),
                ],
                max_length=32,
                primary_key=True,
                serialize=False,
                verbose_name="账号类型",
            ),
        ),
    ]
