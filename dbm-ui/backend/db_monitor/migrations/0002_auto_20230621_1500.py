# Generated by Django 3.2.19 on 2023-06-21 07:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db_monitor", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="collectinstance",
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
                default="mysql",
                max_length=64,
                verbose_name="DB类型",
            ),
        ),
        migrations.AlterField(
            model_name="collecttemplate",
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
                default="mysql",
                max_length=64,
                verbose_name="DB类型",
            ),
        ),
        migrations.AlterField(
            model_name="dashboard",
            name="cluster_type",
            field=models.CharField(
                choices=[
                    ("tendbsingle", "tendbsingle"),
                    ("tendbha", "tendbha"),
                    ("tendbcluster", "tendbcluster"),
                    ("redis", "Redis集群"),
                    ("PredixyRedisCluster", "Redis集群"),
                    ("PredixyTendisplusCluster", "Tendisplus存储版集群"),
                    ("TwemproxyRedisInstance", "TendisCache集群"),
                    ("TwemproxyTendisSSDInstance", "TendisSSD集群"),
                    ("TwemproxyTendisplusInstance", "Tendis存储版集群"),
                    ("RedisInstance", "RedisCache主从版"),
                    ("TendisSSDInstance", "TendisSSD主从版"),
                    ("TendisplusInstance", "Tendisplus主从版"),
                    ("RedisCluster", "RedisCluster集群"),
                    ("TendisplusCluster", "TendisplusCluster集群"),
                    ("es", "ES集群"),
                    ("kafka", "Kafka集群"),
                    ("hdfs", "Hdfs集群"),
                    ("influxdb", "Influxdb实例"),
                    ("pulsar", "Pulsar集群"),
                    ("MongoReplicaSet", "Mongo副本集"),
                    ("MongoShardedCluster", "Mongo分片集群"),
                ],
                default="",
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="noticegroup",
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
            model_name="ruletemplate",
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
                default="mysql",
                max_length=64,
                verbose_name="DB类型",
            ),
        ),
    ]
