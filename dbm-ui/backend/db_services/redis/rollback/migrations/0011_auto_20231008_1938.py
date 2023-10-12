# Generated by Django 3.2.19 on 2023-10-08 11:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rollback", "0010_alter_tbtendisrollbacktasks_destroyed_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="prod_cluster_type",
            field=models.CharField(
                choices=[
                    ("tendbsingle", "tendbsingle"),
                    ("tendbha", "tendbha"),
                    ("tendbcluster", "tendbcluster"),
                    ("redis", "Redis集群"),
                    ("PredixyRedisCluster", "Tendisplus集群"),
                    ("PredixyTendisplusCluster", "Tendisplus存储版集群"),
                    ("TwemproxyRedisInstance", "TendisCache集群"),
                    ("TwemproxyTendisSSDInstance", "TendisSSD集群"),
                    ("TwemproxyTendisplusInstance", "Tendis存储版集群"),
                    ("RedisInstance", "RedisCache主从版"),
                    ("TendisSSDInstance", "TendisSSD主从版"),
                    ("TendisplusInstance", "Tendisplus主从版"),
                    ("RedisCluster", "RedisCluster集群"),
                    ("TendisplusCluster", "TendisplusCluster集群"),
                    ("TendisplusInstance", "Tendisplus存储版集群 GetTendisType 获取redis类型值"),
                    ("RedisInstance", "TendisCache集群 GetTendisType 获取redis类型值"),
                    ("TendisSSDInstance", "TendisSSD集群 GetTendisType 获取redis类型值"),
                    ("es", "ES集群"),
                    ("kafka", "Kafka集群"),
                    ("hdfs", "Hdfs集群"),
                    ("influxdb", "Influxdb实例"),
                    ("pulsar", "Pulsar集群"),
                    ("MongoReplicaSet", "Mongo副本集"),
                    ("MongoShardedCluster", "Mongo分片集群"),
                    ("riak", "Riak集群"),
                ],
                default="",
                max_length=64,
                verbose_name="构造源集群类型",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="temp_cluster_type",
            field=models.CharField(
                choices=[
                    ("tendbsingle", "tendbsingle"),
                    ("tendbha", "tendbha"),
                    ("tendbcluster", "tendbcluster"),
                    ("redis", "Redis集群"),
                    ("PredixyRedisCluster", "Tendisplus集群"),
                    ("PredixyTendisplusCluster", "Tendisplus存储版集群"),
                    ("TwemproxyRedisInstance", "TendisCache集群"),
                    ("TwemproxyTendisSSDInstance", "TendisSSD集群"),
                    ("TwemproxyTendisplusInstance", "Tendis存储版集群"),
                    ("RedisInstance", "RedisCache主从版"),
                    ("TendisSSDInstance", "TendisSSD主从版"),
                    ("TendisplusInstance", "Tendisplus主从版"),
                    ("RedisCluster", "RedisCluster集群"),
                    ("TendisplusCluster", "TendisplusCluster集群"),
                    ("TendisplusInstance", "Tendisplus存储版集群 GetTendisType 获取redis类型值"),
                    ("RedisInstance", "TendisCache集群 GetTendisType 获取redis类型值"),
                    ("TendisSSDInstance", "TendisSSD集群 GetTendisType 获取redis类型值"),
                    ("es", "ES集群"),
                    ("kafka", "Kafka集群"),
                    ("hdfs", "Hdfs集群"),
                    ("influxdb", "Influxdb实例"),
                    ("pulsar", "Pulsar集群"),
                    ("MongoReplicaSet", "Mongo副本集"),
                    ("MongoShardedCluster", "Mongo分片集群"),
                    ("riak", "Riak集群"),
                ],
                default="",
                max_length=64,
                verbose_name="临时集群类型",
            ),
        ),
    ]
