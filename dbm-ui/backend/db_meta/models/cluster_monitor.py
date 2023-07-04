# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging

from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.bk_web.constants import LEN_X_LONG
from backend.bk_web.models import AuditedModel
from backend.components import CCApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import MachineType

logger = logging.getLogger("root")

INSTANCE_MONITOR_PLUGINS = {
    DBType.MySQL: {
        MachineType.PROXY: {"name": "proxy", "plugin_id": "dbm_mysqlproxy_exporter"},
        MachineType.BACKEND: {"name": "mysql", "plugin_id": "dbm_mysqld_exporter"},
        MachineType.SPIDER: {"name": "spider", "plugin_id": "dbm_spider_exporter"},
        MachineType.REMOTE: {"name": "mysql", "plugin_id": "dbm_mysqld_exporter"},
        MachineType.SINGLE: {"name": "mysql", "plugin_id": "dbm_mysqld_exporter"},
    },
    DBType.Redis: {
        MachineType.TWEMPROXY: {"name": "twemproxy", "plugin_id": "dbm_twemproxy_exporter"},
        MachineType.PREDIXY: {"name": "predixy", "plugin_id": "dbm_predixy_exporter"},
        MachineType.TENDISCACHE: {"name": "tendiscache", "plugin_id": "dbm_redis_exporter"},
        MachineType.TENDISPLUS: {"name": "tendisplus", "plugin_id": "dbm_redis_exporter"},
        MachineType.TENDISSSD: {"name": "tendisssd", "plugin_id": "dbm_redis_exporter"},
    },
    DBType.Es: {
        MachineType.ES_DATANODE: {"name": "es", "plugin_id": "dbm_elasticsearch_exporter"},
        MachineType.ES_MASTER: {"name": "es", "plugin_id": "dbm_elasticsearch_exporter"},
        MachineType.ES_CLIENT: {"name": "es", "plugin_id": "dbm_elasticsearch_exporter"},
    },
    DBType.Kafka: {
        MachineType.BROKER: {"name": "kafka", "plugin_id": "dbm_kafka_bkpull"},
        MachineType.ZOOKEEPER: {"name": "zookeeper", "plugin_id": "dbm_kafka_exporter"},
    },
    DBType.Hdfs: {
        MachineType.HDFS_MASTER: {"name": "hdfs", "plugin_id": "dbm_hdfs_exporter"},
        MachineType.HDFS_DATANODE: {"name": "hdfs", "plugin_id": "dbm_hdfs_exporter"},
    },
    DBType.Pulsar: {
        MachineType.PULSAR_BROKER: {"name": "broker", "plugin_id": "dbm_pulsarbroker_bkpull"},
        MachineType.PULSAR_ZOOKEEPER: {"name": "zookeeper", "plugin_id": "dbm_pulsarzookeeper_bkpull"},
        MachineType.PULSAR_BOOKKEEPER: {"name": "bookkeeper", "plugin_id": "dbm_pulsarbookkeeper_bkpull"},
    },
    DBType.InfluxDB: {
        MachineType.INFLUXDB: {"name": "influxdb", "plugin_id": "dbm_influxdb_bkpull"},
    },
    DBType.Riak: {
        MachineType.RIAK: {"name": "riak", "plugin_id": "dbm_riak_exporter"},
    },
}


def get_monitor_plugin(db_type, machine_type):
    """主机实例 -> 监控插件类型"""
    return INSTANCE_MONITOR_PLUGINS[db_type][machine_type]


class AppMonitorTopo(AuditedModel):
    """
    业务监控顶层拓扑配置 -> INSTANCE_MONITOR_PLUGINS

    dba业务
        mysql.proxy
            c1.a.b.c
        mysql.spider
            c1.a.b.c
        redis.twemproxy
        ...
    """

    bk_biz_id = models.IntegerField(default=0)
    db_type = models.CharField(max_length=64, choices=DBType.get_choices(), default="")
    machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), default="")
    monitor_plugin = models.CharField(max_length=64, default="")
    monitor_plugin_id = models.CharField(max_length=128, default="")

    bk_set_id = models.BigIntegerField(default=0)
    bk_set_name = models.CharField(max_length=64, default="")

    @classmethod
    def get_set_by_dbtype(cls, db_type):
        return [
            {"machine_type": obj.machine_type, "bk_set_id": obj.bk_set_id, "bk_set_name": obj.bk_set_name}
            for obj in cls.objects.filter(db_type=db_type)
        ]

    @classmethod
    def get_set_by_plugin_id(cls, plugin_id):
        return list(
            cls.objects.filter(monitor_plugin_id__contains=plugin_id).values_list("bk_set_id", flat=True).distinct()
        )

    @classmethod
    @transaction.atomic
    def init_topo(cls):
        """拓扑初始化"""

        for db_type, machine_monitor_plugins in INSTANCE_MONITOR_PLUGINS.items():
            for machine_type, monitor_plugin in machine_monitor_plugins.items():
                monitor_plugin_id, monitor_plugin_name = monitor_plugin["plugin_id"], monitor_plugin["name"]
                plugin_set = cls.objects.filter(
                    db_type=db_type,
                    monitor_plugin=monitor_plugin_name,
                    bk_set_id__gt=0,
                    bk_biz_id=env.DBA_APP_BK_BIZ_ID,
                ).first()

                # logger.info("init_topo:[%s, %s, %s], start.", db_type, machine_type, monitor_plugin_name)

                obj, created = cls.objects.update_or_create(
                    defaults={"monitor_plugin_id": monitor_plugin_id},
                    bk_biz_id=env.DBA_APP_BK_BIZ_ID,
                    machine_type=machine_type,
                    db_type=db_type,
                    monitor_plugin=monitor_plugin_name,
                    # monitor_plugin_id=monitor_plugin_id,
                )

                # 不同machine类型复用相同plugin及topo
                if plugin_set:
                    logger.info(
                        "init_topo -> [%s, %s, %s], skip same plugin topo.", db_type, machine_type, monitor_plugin_name
                    )
                    obj.bk_set_id = plugin_set.bk_set_id
                    obj.bk_set_name = plugin_set.bk_set_name
                    obj.save()
                    continue

                bk_set_name = f"db.{db_type}.{monitor_plugin_name}"

                # 本地没有 -> 远程没有 -> 创建远程   |
                #        ->  远程有               |---> 更新本地
                if obj.bk_set_id:
                    exist = True
                    bk_set_id = obj.bk_set_id
                else:
                    # 需要申请接口权限并添加白名单
                    res = CCApi.search_set(
                        params={
                            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                            "fields": [
                                "bk_set_name",
                                "bk_set_id",
                            ],
                            "condition": {"bk_set_name": bk_set_name},
                        }
                    )

                    exist = res["count"] > 0
                    bk_set_id = res["info"][0]["bk_set_id"] if exist else 0

                if not exist:
                    logger.info(
                        "init_topo -> [%s, %s, %s], create_set(%s).",
                        db_type,
                        machine_type,
                        monitor_plugin_name,
                        bk_set_name,
                    )
                    res = CCApi.create_set(
                        params={
                            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                            "data": {
                                "bk_parent_id": env.DBA_APP_BK_BIZ_ID,
                                "bk_set_name": bk_set_name,
                            },
                        }
                    )
                    bk_set_id = res["bk_set_id"]
                    # logger.info(
                    #     "init_topo -> [%s, %s, %s], create_set(%s) -> %s.",
                    #     db_type,
                    #     machine_type,
                    #     monitor_plugin_name,
                    #     bk_set_name,
                    #     bk_set_id,
                    # )

                if not obj.bk_set_id:
                    logger.info(
                        "init_topo -> [%s, %s, %s], update local(%s) -> %s.",
                        db_type,
                        machine_type,
                        monitor_plugin_name,
                        bk_set_name,
                        bk_set_id,
                    )
                    obj.bk_set_name = bk_set_name
                    obj.bk_set_id = bk_set_id
                    obj.save()

    class Meta:
        verbose_name = _("业务监控拓扑")
        verbose_name_plural = _("业务监控拓扑")


class ClusterMonitorTopo(AuditedModel):
    """
    背景：通过CMDB的服务实例+事件订阅实现服务发现，通过一张表映射DB集群的组件与CMDB模块的关系
    CMDB模块映射
        DB集群+组件类型 -> CMDB模块 -> 特定的exporter与服务实例
    """

    bk_biz_id = models.IntegerField(default=0)
    cluster_id = models.BigIntegerField(default=0)
    instance_id = models.BigIntegerField(help_text=_("实例ID，兼容单实例存储组件influxdb"), default=0)
    bk_set_id = models.BigIntegerField(default=0)
    bk_module_id = models.BigIntegerField(default=0)
    machine_type = models.CharField(max_length=64, choices=MachineType.get_choices(), default="")

    class Meta:
        verbose_name = _("CMDB模块映射")
        verbose_name_plural = _("CMDB模块映射")


class SyncFailedMachine(AuditedModel):
    """同步失败的IP"""

    bk_host_id = models.PositiveBigIntegerField(primary_key=True, default=0)
    error = models.CharField(max_length=LEN_X_LONG)

    class Meta:
        verbose_name = _("同步失败的IP")
        verbose_name_plural = _("同步失败的IP")
