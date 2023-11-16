# Generated by Django 3.2.19 on 2023-11-20 11:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("autofix", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TbRedisClusterNodesUpdateTask",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("bk_biz_id", models.IntegerField(default=0, verbose_name="业务ID")),
                ("cluster_id", models.IntegerField(default=0, verbose_name="集群ID")),
                (
                    "cluster_type",
                    models.CharField(
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
                            ("dbmon", "redis监控"),
                            ("MongoReplicaSet", "Mongo副本集"),
                            ("MongoShardedCluster", "Mongo分片集群"),
                            ("riak", "Riak集群"),
                        ],
                        max_length=64,
                        verbose_name="集群类型",
                    ),
                ),
                ("immute_domain", models.CharField(default="", max_length=255, verbose_name="集群域名")),
                ("message", models.TextField(default="", verbose_name="信息")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("todo", "待处理"),
                            ("canceled", "已取消"),
                            ("failed", "失败"),
                            ("doing", "执行中"),
                            ("success", "成功"),
                        ],
                        max_length=64,
                        verbose_name="任务状态",
                    ),
                ),
                ("report_server_ip", models.GenericIPAddressField(default="", verbose_name="上报IP")),
                ("report_server_port", models.IntegerField(default=0, verbose_name="上报端口")),
                ("report_nodes_data", models.TextField(default="", verbose_name="上报的nodes data")),
                ("report_time", models.DateTimeField(default="1970-01-01 08:00:01", verbose_name="上报时间")),
                ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
            ],
            options={
                "db_table": "tb_tendis_cluster_nodes_update_task",
            },
        ),
        migrations.AddIndex(
            model_name="tbredisclusternodesupdatetask",
            index=models.Index(fields=["create_time"], name="idx_create_time"),
        ),
        migrations.AddIndex(
            model_name="tbredisclusternodesupdatetask",
            index=models.Index(fields=["bk_biz_id", "create_time"], name="idx_biz_create_time"),
        ),
        migrations.AddIndex(
            model_name="tbredisclusternodesupdatetask",
            index=models.Index(fields=["immute_domain", "create_time"], name="idx_domain_create_time"),
        ),
    ]
