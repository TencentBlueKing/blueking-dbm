# Generated by Django 3.2.19 on 2023-07-21 02:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rollback", "0002_auto_20230625_1123"),
    ]

    operations = [
        migrations.AddField(
            model_name="tbtendisrollbacktasks",
            name="prod_cluster_id",
            field=models.BigIntegerField(default=0, verbose_name="集群id，cluster.id"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="app",
            field=models.CharField(default="", max_length=64, verbose_name="业务名"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="bk_biz_id",
            field=models.BigIntegerField(verbose_name="业务id"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="bk_cloud_id",
            field=models.BigIntegerField(default=0, verbose_name="云区域id"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="host_count",
            field=models.IntegerField(verbose_name="构造的主机数量"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="is_destroyed",
            field=models.IntegerField(default=0, verbose_name="是否已销毁"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="prod_cluster",
            field=models.CharField(default="", max_length=128, verbose_name="构造的源集群，线上环境cluster"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="prod_cluster_type",
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
                    ("riak", "Riak集群"),
                ],
                default="",
                max_length=64,
                verbose_name="构造源集群类型",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="prod_instance_range",
            field=models.TextField(max_length=10000, verbose_name="源构造的实例范围"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="prod_temp_instance_pairs",
            field=models.TextField(default="", max_length=20000, verbose_name="构造源实例和临时实例一一对应关系"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="recovery_time_point",
            field=models.DateTimeField(verbose_name="构造到指定时间"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="related_rollback_bill_id",
            field=models.BigIntegerField(unique=True, verbose_name="单据号，关联单据"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="specification",
            field=models.JSONField(default=dict, verbose_name="规格需求"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="status",
            field=models.IntegerField(default=0, verbose_name="任务状态"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="temp_cluster_proxy",
            field=models.CharField(max_length=100, verbose_name="构造产物访问入口ip:port"),
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
                    ("riak", "Riak集群"),
                ],
                default="",
                max_length=64,
                verbose_name="临时集群类型",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="temp_instance_range",
            field=models.TextField(max_length=10000, verbose_name="临时集群构造实例范围"),
        ),
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="temp_password",
            field=models.CharField(default="", max_length=128, verbose_name="临时集群proxy密码base64值"),
        ),
    ]
