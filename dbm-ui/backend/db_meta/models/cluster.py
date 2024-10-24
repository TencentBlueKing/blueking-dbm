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
import itertools
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Count, Q, QuerySet
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.components.db_remote_service.client import DRSApi
from backend.configuration.constants import AffinityEnum, DBType
from backend.constants import CACHE_CLUSTER_STATS, DEFAULT_BK_CLOUD_ID, DEFAULT_TIME_ZONE, IP_PORT_DIVIDER
from backend.db_meta.enums import (
    ClusterDBHAStatusFlags,
    ClusterPhase,
    ClusterStatus,
    ClusterTenDBClusterStatusFlag,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    InstanceStatus,
    MachineType,
    TenDBClusterSpiderRole,
)
from backend.db_meta.enums.cluster_status import (
    ClusterCommonStatusFlags,
    ClusterDBSingleStatusFlags,
    ClusterRedisStatusFlags,
    ClusterSqlserverStatusFlags,
)
from backend.db_meta.exceptions import ClusterExclusiveOperateException, DBMetaException
from backend.db_services.version.constants import LATEST, PredixyVersion, TwemproxyVersion
from backend.exceptions import ApiError
from backend.flow.consts import DEFAULT_RIAK_PORT
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord

logger = logging.getLogger("root")


class Cluster(AuditedModel):
    name = models.CharField(max_length=64, default="", help_text=_("集群英文名"))
    alias = models.CharField(max_length=64, default="", help_text=_("集群别名"))
    bk_biz_id = models.IntegerField(default=0)
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    db_module_id = models.BigIntegerField(default=0)
    immute_domain = models.CharField(max_length=255, default="", db_index=True)
    major_version = models.CharField(max_length=64, default="", help_text=_("主版本号"))
    phase = models.CharField(max_length=64, choices=ClusterPhase.get_choices(), default=ClusterPhase.ONLINE.value)
    status = models.CharField(max_length=64, choices=ClusterStatus.get_choices(), default=ClusterStatus.NORMAL.value)
    bk_cloud_id = models.IntegerField(default=DEFAULT_BK_CLOUD_ID, help_text=_("云区域 ID"))
    region = models.CharField(max_length=128, default="", help_text=_("地域"))
    disaster_tolerance_level = models.CharField(
        max_length=128, help_text=_("容灾要求"), choices=AffinityEnum.get_choices(), default=AffinityEnum.NONE.value
    )
    time_zone = models.CharField(max_length=16, default=DEFAULT_TIME_ZONE, help_text=_("集群所在的时区"))

    class Meta:
        unique_together = [("bk_biz_id", "immute_domain", "cluster_type", "db_module_id"), ("immute_domain",)]

        verbose_name = verbose_name_plural = _("集群(Cluster)")

    def __str__(self):
        return self.name

    def to_dict(self):
        """将集群所有字段转为字段"""
        return {**model_to_dict(self), "cluster_type_name": str(ClusterType.get_choice_label(self.cluster_type))}

    @property
    def simple_desc(self):
        """集群简略信息"""
        return model_to_dict(
            self,
            [
                "id",
                "name",
                "bk_biz_id",
                "bk_cloud_id",
                "region",
                "cluster_type",
                "immute_domain",
                "major_version",
            ],
        )

    @property
    def extra_desc(self):
        """追加额外信息，不适合大批量序列化场景"""

        simple_desc = self.simple_desc

        # 追加角色部署数量信息
        simple_desc["proxy_count"] = self.proxyinstance_set.all().count()
        for storage in (
            self.storageinstance_set.values("instance_role")
            .annotate(cnt=Count("machine__ip", distinct=True))
            .order_by()
        ):
            simple_desc["{}_count".format(storage["instance_role"])] = storage["cnt"]

        return simple_desc

    @classmethod
    def get_cluster_id_immute_domain_map(cls, cluster_ids: List[int]) -> Dict[int, str]:
        """查询集群ID和域名的映射关系"""
        clusters = cls.objects.filter(id__in=cluster_ids).only("id", "immute_domain")
        return {cluster.id: cluster.immute_domain for cluster in clusters}

    @classmethod
    def is_exclusive(cls, cluster_id, ticket_type=None, **kwargs):
        if not ticket_type:
            return None

        return ClusterOperateRecord.objects.has_exclusive_operations(ticket_type, cluster_id, **kwargs)

    @classmethod
    def handle_exclusive_operations(cls, cluster_ids: List[int], ticket_type: str, **kwargs):
        """
        处理当前的动作是否和集群正在运行的动作存在执行互斥
        """
        for cluster_id in cluster_ids:
            exclusive_infos = cls.is_exclusive(cluster_id, ticket_type, **kwargs)
            if not exclusive_infos:
                continue

            # 存在互斥操作，则抛出错误让用户后续重试该inner flow
            exclusive_infos = [
                (
                    f'{TicketType.get_choice_label(info["exclusive_ticket"].ticket_type)}'
                    f'(ticket_id:{info["exclusive_ticket"].id})'
                )
                for info in exclusive_infos
            ]
            raise ClusterExclusiveOperateException(
                _("当前操作「{}」与集群(id:{})的操作「{}」存在执行互斥").format(
                    TicketType.get_choice_label(ticket_type), cluster_id, ",".join(exclusive_infos)
                )
            )

    def can_access(self) -> (bool, str):
        # 判断集群的状态是否正常
        if self.status != ClusterStatus.NORMAL:
            return False, _("集群运行状态异常，请检查!")

        if self.phase != ClusterPhase.ONLINE:
            return False, _("集群已被禁用，请先启用!")

        return True, ""

    @property
    def proxy_version(self):
        if self.cluster_type in [
            ClusterType.TendisPredixyRedisCluster,
            ClusterType.TendisPredixyTendisplusCluster,
        ]:
            return PredixyVersion.PredixyLatest
        if self.cluster_type in [
            ClusterType.TendisTwemproxyTendisplusIns,
            ClusterType.TendisTwemproxyRedisInstance,
            ClusterType.TwemproxyTendisSSDInstance,
        ]:
            return TwemproxyVersion.TwemproxyLatest
        return LATEST

    @property
    def __status_flag(self):
        # tendb ha
        if self.cluster_type == ClusterType.TenDBHA.value:
            flag_obj = ClusterDBHAStatusFlags(0)
            if self.proxyinstance_set.filter(status=InstanceStatus.UNAVAILABLE.value).exists():
                flag_obj |= ClusterDBHAStatusFlags.ProxyUnavailable
            if self.storageinstance_set.filter(
                status=InstanceStatus.UNAVAILABLE.value, instance_inner_role=InstanceInnerRole.MASTER.value
            ).exists():
                flag_obj |= ClusterDBHAStatusFlags.BackendMasterUnavailable
            if self.storageinstance_set.filter(
                status=InstanceStatus.UNAVAILABLE.value, instance_inner_role=InstanceInnerRole.SLAVE.value
            ).exists():
                flag_obj |= ClusterDBHAStatusFlags.BackendSlaveUnavailable
        # tendbcluster
        elif self.cluster_type == ClusterType.TenDBCluster.value:
            flag_obj = ClusterTenDBClusterStatusFlag(0)
            if self.proxyinstance_set.filter(status=InstanceStatus.UNAVAILABLE.value).exists():
                flag_obj |= ClusterTenDBClusterStatusFlag.SpiderUnavailable
            if self.storageinstance_set.filter(
                status=InstanceStatus.UNAVAILABLE.value, instance_inner_role=InstanceInnerRole.MASTER.value
            ).exists():
                flag_obj |= ClusterTenDBClusterStatusFlag.RemoteMasterUnavailable
            if self.storageinstance_set.filter(
                status=InstanceStatus.UNAVAILABLE.value, instance_inner_role=InstanceInnerRole.SLAVE.value
            ).exists():
                flag_obj |= ClusterTenDBClusterStatusFlag.RemoteSlaveUnavailable
        # tendb single
        elif self.cluster_type == ClusterType.TenDBSingle.value:
            flag_obj = ClusterDBSingleStatusFlags(0)
            if self.storageinstance_set.filter(status=InstanceStatus.UNAVAILABLE.value).exists():
                flag_obj |= ClusterDBSingleStatusFlags.SingleUnavailable
        # redis
        elif self.cluster_type in ClusterType.redis_cluster_types():
            flag_obj = ClusterRedisStatusFlags(0)
            if self.storageinstance_set.filter(status=InstanceStatus.UNAVAILABLE.value).exists():
                flag_obj |= ClusterRedisStatusFlags.RedisUnavailable
        # sqlserver ha
        if self.cluster_type == ClusterType.SqlserverHA.value:
            flag_obj = ClusterSqlserverStatusFlags(0)
            if self.storageinstance_set.filter(
                status=InstanceStatus.UNAVAILABLE.value, instance_inner_role=InstanceInnerRole.MASTER.value
            ).exists():
                flag_obj |= ClusterSqlserverStatusFlags.BackendMasterUnavailable
            if self.storageinstance_set.filter(
                status=InstanceStatus.UNAVAILABLE.value, instance_inner_role=InstanceInnerRole.SLAVE.value
            ).exists():
                flag_obj |= ClusterSqlserverStatusFlags.BackendSlaveUnavailable
        # 默认
        else:
            logger.debug(_("{} 未实现 status flag, 认为实例异常会导致集群异常".format(self.cluster_type)))
            flag_obj = ClusterCommonStatusFlags(0)

        return flag_obj

    @property
    def status_flag(self):
        return self.__status_flag.value

    @property
    def status_flag_text(self) -> List[str]:
        return self.__status_flag.flag_text()

    def main_storage_instances(self) -> QuerySet:
        if self.cluster_type == ClusterType.TenDBSingle.value:
            return self.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.ORPHAN.value)
        elif self.cluster_type == ClusterType.TenDBHA.value:
            return self.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER.value)
        elif self.cluster_type == ClusterType.TenDBCluster.value:
            return self.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER.value)
        else:
            raise DBMetaException(message=_("{} 未实现 main_storage_instance".format(self.cluster_type)))

    @property
    def access_port(self) -> int:
        """
        获取集群的访问端口，如果要批量查询，请使用prefetch预存instance得queryset
        TODO: 是否考虑将此字段作为表字段，而不是实时计算
        tendbsingle: 只有一台机器，直接取那个port
        tendbha, redis: 取proxy的一台port
        tendbcluster: 主域名取spider master的port   从域名取spider slave的port
        es: es_datanode_hot
        kafka: broker
        hdfs: namenode
        pulsar: broker
        riak: 固定为8087
        mongo_cluster: proxy的port
        mongo_replicaset: 去存储节点的port
        sqlserver: ?
        """
        try:
            if hasattr(self, "storages") and hasattr(self, "proxies"):
                return self.prefetched_access_port
            if self.cluster_type == ClusterType.TenDBSingle:
                return self.storageinstance_set.first().port
            elif self.cluster_type == ClusterType.RedisInstance:
                return self.storageinstance_set.first().port
            elif self.cluster_type in [ClusterType.TenDBHA, *ClusterType.db_type_to_cluster_types(DBType.Redis)]:
                return self.proxyinstance_set.first().port
            elif self.cluster_type == ClusterType.TenDBCluster:
                spider_master_filter = Q(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER)
                return self.proxyinstance_set.filter(spider_master_filter).first().port
            elif self.cluster_type == ClusterType.Es:
                return self.storageinstance_set.filter(instance_role=InstanceRole.ES_MASTER).first().port
            elif self.cluster_type == ClusterType.Kafka:
                return self.storageinstance_set.filter(instance_role=InstanceRole.BROKER).first().port
            elif self.cluster_type == ClusterType.Hdfs:
                return self.storageinstance_set.filter(instance_role=InstanceRole.HDFS_NAME_NODE).first().port
            elif self.cluster_type == ClusterType.Pulsar:
                return self.storageinstance_set.filter(instance_role=InstanceRole.PULSAR_BROKER).first().port
            elif self.cluster_type == ClusterType.Riak:
                return DEFAULT_RIAK_PORT
            elif self.cluster_type == ClusterType.MongoShardedCluster:
                return self.proxyinstance_set.filter(machine_type=MachineType.MONGOS).first().port
            elif self.cluster_type == ClusterType.MongoReplicaSet:
                return self.storageinstance_set.filter(machine_type=MachineType.MONGODB).first().port
            elif self.cluster_type == ClusterType.Doris:
                return self.storageinstance_set.filter(instance_role=InstanceRole.DORIS_FOLLOWER).first().port
        except (AttributeError, IndexError, Exception):
            logger.warning(_("无法访问集群[]的访问端口，请检查实例信息").format(self.name))
            return 0

    @property
    def prefetched_access_port(self):
        """
        加速获取集群的访问端口，
        适用于预取了storageinstance和proxyinstance的情况，避免N+1查询
        """
        if self.cluster_type == ClusterType.TenDBSingle:
            return self.storages[0].port
        elif self.cluster_type == ClusterType.RedisInstance:
            return self.storages[0].port
        elif self.cluster_type in [ClusterType.TenDBHA, *ClusterType.db_type_to_cluster_types(DBType.Redis)]:
            return self.proxies[0].port
        elif self.cluster_type == ClusterType.TenDBCluster:
            role = TenDBClusterSpiderRole.SPIDER_MASTER
            return next(inst.port for inst in self.proxies if inst.tendbclusterspiderext.spider_role == role)
        elif self.cluster_type == ClusterType.Es:
            return next(inst.port for inst in self.storages if inst.instance_role == InstanceRole.ES_MASTER)
        elif self.cluster_type == ClusterType.Kafka:
            return next(inst.port for inst in self.storages if inst.instance_role == InstanceRole.BROKER)
        elif self.cluster_type == ClusterType.Hdfs:
            return next(inst.port for inst in self.storages if inst.instance_role == InstanceRole.HDFS_NAME_NODE)
        elif self.cluster_type == ClusterType.Pulsar:
            return next(inst.port for inst in self.storages if inst.instance_role == InstanceRole.PULSAR_BROKER)
        elif self.cluster_type == ClusterType.Riak:
            return DEFAULT_RIAK_PORT
        elif self.cluster_type == ClusterType.MongoShardedCluster:
            return next(inst.port for inst in self.proxies if inst.machine_type == MachineType.MONGOS)
        elif self.cluster_type == ClusterType.MongoReplicaSet:
            return next(inst.port for inst in self.storages if inst.machine_type == MachineType.MONGODB)
        elif self.cluster_type == ClusterType.Doris:
            return next(inst.port for inst in self.storages if inst.instance_role == InstanceRole.DORIS_FOLLOWER)
        else:
            return 0

    def get_partition_port(self):
        """
        获取集群在分区管理的端口号
        tendbsingle 是mysql的端口
        tendbcluster 是proxy的端口
        """
        if self.cluster_type == ClusterType.TenDBSingle:
            return self.storageinstance_set.first().port
        elif self.cluster_type == ClusterType.TenDBHA:
            return self.proxyinstance_set.first().port
        # TODO: tendbcluster的端口是spider master？
        elif self.cluster_type == ClusterType.TenDBCluster:
            return (
                self.proxyinstance_set.filter(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER)
                .first()
                .port
            )

    def tendbcluster_ctl_primary_address(self) -> str:
        """
        查询并返回 tendbcluster 的中控 primary
        集群类型不是 TenDBCluster 时会抛出异常
        返回值是 "ip:port" 形式的字符串
        """
        if self.cluster_type != ClusterType.TenDBCluster.value:
            raise DBMetaException(message=_("{} 类型集群没有中控节点".format(self.cluster_type)))

        # 取一个状态正常的 spider-master 接入层
        spider_instance = self.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
            status=InstanceStatus.RUNNING.value,
        ).first()

        ctl_address = "{}{}{}".format(spider_instance.machine.ip, IP_PORT_DIVIDER, spider_instance.port + 1000)

        logger.info("ctl address: {}".format(ctl_address))
        try:
            res = DRSApi.short_rpc(
                {
                    "addresses": [ctl_address],
                    "cmds": ["tdbctl get primary"],
                    "force": False,
                    "bk_cloud_id": self.bk_cloud_id,
                }
            )
        except (ApiError, Exception) as e:
            logger.error(_("get primary failed: {}".format(e)))
            return ""

        logger.info("tdbctl get primary res: {}".format(res))

        if res[0]["error_msg"]:
            raise DBMetaException(message=_("get primary failed: {}".format(res[0]["error_msg"])))

        primary_info_table_data = res[0]["cmd_results"][0]["table_data"]
        if primary_info_table_data:
            return "{}{}{}".format(
                primary_info_table_data[0]["HOST"], IP_PORT_DIVIDER, primary_info_table_data[0]["PORT"]
            )
        else:
            return ctl_address

    @classmethod
    def get_cluster_stats(cls, bk_biz_id, cluster_types) -> dict:
        cluster_stats = {}
        for cluster_type in cluster_types:
            cluster_stats.update(json.loads(cache.get(f"{CACHE_CLUSTER_STATS}_{bk_biz_id}_{cluster_type}", "{}")))

        return cluster_stats

    def is_dbha_disabled(self) -> bool:
        try:
            return self.clusterdbhaext.end_time >= datetime.now(timezone.utc)
        except ObjectDoesNotExist:
            return False

    def disable_dbha(self, username: str, end_time: datetime):
        ClusterDBHAExt.objects.update_or_create(
            cluster_id=self.id,
            defaults={
                "creator": username,
                "updater": username,
                "cluster": self,
                "end_time": end_time,
            },
        )
        self.refresh_from_db()

    def enable_dbha(self):
        ClusterDBHAExt.objects.filter(cluster=self).delete()
        self.refresh_from_db()

    @classmethod
    def get_cluster_id__primary_address_map(cls, cluster_ids: List[int]) -> Dict[int, str]:
        """
        通过集群id列表批量
        查询并返回 tendbcluster 的中控 primary
        集群类型不是 TenDBCluster 时会抛出异常
        返回值是 {cluster_id:"ip:port"} 形式的字典
        """
        clusters = cls.objects.filter(id__in=cluster_ids).order_by("bk_cloud_id")

        cluster_id__primary_address_map = {}
        ctl_address__cluster_id_map = {}

        grouped_clusters = itertools.groupby(clusters, key=lambda x: x.bk_cloud_id)
        for bk_cloud_id, group in grouped_clusters:
            addresses = []
            for cluster in group:
                if cluster.cluster_type != ClusterType.TenDBCluster.value:
                    logger.error(_("集群id:{} {} 类型集群没有中控节点".format(cluster.id, cluster.cluster_type)))
                    continue

                # 取一个状态正常的 spider-master 接入层
                spider_instance = cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
                    status=InstanceStatus.RUNNING.value,
                ).first()

                ctl_address = "{}{}{}".format(spider_instance.machine.ip, IP_PORT_DIVIDER, spider_instance.port + 1000)
                addresses.append(ctl_address)
                ctl_address__cluster_id_map[ctl_address] = cluster.id

            logger.info("addresses: {}".format(addresses))

            try:
                res = DRSApi.short_rpc(
                    {
                        "addresses": addresses,
                        "cmds": ["tdbctl get primary"],
                        "force": False,
                        "bk_cloud_id": bk_cloud_id,
                    }
                )
            except (ApiError, Exception) as e:
                logger.error(_("get primary failed: {}".format(e)))
                continue

            logger.info("tdbctl get primary res: {}".format(res))

            for item in res:
                if item["error_msg"]:
                    logger.error(_("get primary failed: {}".format(item["error_msg"])))
                    continue

                primary_info_table_data = item["cmd_results"][0]["table_data"]
                if primary_info_table_data:
                    cluster_id__primary_address_map[ctl_address__cluster_id_map[item["address"]]] = "{}{}{}".format(
                        primary_info_table_data[0]["HOST"], IP_PORT_DIVIDER, primary_info_table_data[0]["PORT"]
                    )
                else:
                    cluster_id__primary_address_map[ctl_address__cluster_id_map[item["address"]]] = item["address"]

        return cluster_id__primary_address_map


class ClusterDBHAExt(AuditedModel):
    """
    这个model如果放在独立文件会循环引用, 解决起来比较麻烦
    """

    cluster = models.OneToOneField(Cluster, on_delete=models.PROTECT, unique=True)
    begin_time = models.DateTimeField(null=False, auto_now=True, help_text=_("屏蔽开始时间"), db_index=True)
    end_time = models.DateTimeField(default=None, null=False, auto_now=False, help_text=_("屏蔽结束时间"), db_index=True)
