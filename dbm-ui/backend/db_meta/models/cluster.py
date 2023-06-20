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
from typing import Dict, List

from django.db import models
from django.db.models import QuerySet, Count
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.components.db_remote_service.client import DRSApi
from backend.constants import DEFAULT_BK_CLOUD_ID, DEFAULT_TIME_ZONE, IP_PORT_DIVIDER
from backend.db_meta.enums import (
    ClusterDBHAStatusFlags,
    ClusterPhase,
    ClusterStatus,
    ClusterTenDBClusterStatusFlag,
    ClusterType,
    InstanceInnerRole,
    InstanceStatus,
    TenDBClusterSpiderRole,
)
from backend.db_meta.exceptions import ClusterExclusiveOperateException, DBMetaException
from backend.db_meta.models.spec import ClusterDeployPlan
from backend.db_services.version.constants import LATEST, PredixyVersion, TwemproxyVersion
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord

logger = logging.getLogger("root")


class Cluster(AuditedModel):
    name = models.CharField(max_length=36, default="", help_text=_("集群英文名"))
    alias = models.CharField(max_length=64, default="", help_text=_("集群别名"))
    bk_biz_id = models.IntegerField(default=0)
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    db_module_id = models.BigIntegerField(default=0)
    immute_domain = models.CharField(max_length=200, default="", db_index=True)
    major_version = models.CharField(max_length=64, default="", help_text=_("主版本号"))
    phase = models.CharField(max_length=64, choices=ClusterPhase.get_choices(), default=ClusterPhase.ONLINE.value)
    status = models.CharField(max_length=64, choices=ClusterStatus.get_choices(), default=ClusterStatus.NORMAL.value)
    bk_cloud_id = models.IntegerField(default=DEFAULT_BK_CLOUD_ID, help_text=_("云区域 ID"))
    region = models.CharField(max_length=128, default="", help_text=_("地域"))
    time_zone = models.CharField(max_length=16, default=DEFAULT_TIME_ZONE, help_text=_("集群所在的时区"))
    deploy_plan_id = models.BigIntegerField(default=0, help_text=_("部署方法ID"))

    # tag = models.ManyToManyField(Tag, blank=True)

    class Meta:
        unique_together = ("bk_biz_id", "name", "cluster_type", "db_module_id")

    def __str__(self):
        return self.name

    def to_dict(self):
        return {**model_to_dict(self), "cluster_type_name": str(ClusterType.get_choice_label(self.cluster_type))}

    @property
    def simple_desc(self):
        return model_to_dict(self, ["id", "name", "bk_cloud_id", "deploy_plan_id", "region", "cluster_type"])

    @property
    def extra_desc(self):
        """追加额外信息，不适合大批量序列化场景"""

        simple_desc = self.simple_desc

        # 填充额外统计信息
        simple_desc["proxy_count"] = self.proxyinstance_set.all().count()
        for storage in self.storageinstance_set.values(
                "instance_role"
        ).annotate(cnt=Count('machine__ip', distinct=True)).order_by():
            simple_desc["{}_count".format(storage["instance_role"])] = storage["cnt"]

        # 填充部署方案详情
        simple_desc["deploy_plan"] = getattr(ClusterDeployPlan.objects.filter(id=self.deploy_plan_id).last(),
                                             "simple_desc", {})
        return simple_desc

    @classmethod
    def get_cluster_id_immute_domain_map(cls, cluster_ids: List[int]) -> Dict[int, str]:
        """查询集群ID和域名的映射关系"""
        clusters = cls.objects.filter(id__in=cluster_ids).only("id", "immute_domain")
        return {cluster.id: cluster.immute_domain for cluster in clusters}

    @classmethod
    def is_exclusive(cls, cluster_id, ticket_type=None):
        if not ticket_type:
            return None

        return ClusterOperateRecord.objects.has_exclusive_operations(ticket_type, cluster_id)

    @classmethod
    def handle_exclusive_operations(cls, cluster_ids: List[int], ticket_type: str):
        """
        处理当前的动作是否和集群正在运行的动作存在执行互斥
        """

        for cluster_id in cluster_ids:
            exclusive_infos = cls.is_exclusive(cluster_id, ticket_type)
            if not exclusive_infos:
                continue

            # 存在互斥操作，则抛出错误让用户后续重试该inner flow
            exclusive_infos = [
                str(TicketType.get_choice_label(info["exclusive_ticket"].ticket_type)) for info in exclusive_infos
            ]
            raise ClusterExclusiveOperateException(
                _("当前操作「{}」与集群{}的操作「{}」存在执行互斥").format(
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
        else:
            raise DBMetaException(message=_("{} 未实现 status flag".format(self.cluster_type)))

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

    @classmethod
    def is_refer_deploy_plan(cls, deploy_plan_ids):
        return cls.objects.filter(deploy_plan_id__in=deploy_plan_ids).exists()

    def tendbcluster_ctl_primary_address(self) -> str:
        """
        查询并返回 tendbcluster 的中控 primary
        集群类型不是 TenDBCluster 时会抛出异常
        返回值是 "ip:port" 形式的字符串
        """
        if self.cluster_type != ClusterType.TenDBCluster.value:
            raise DBMetaException(message=_("{} 类型集群没有中控节点".format(self.cluster_type)))

        spider_instance = self.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        ).first()  # 随便拿一个spider-master接入层

        ctl_address = "{}{}{}".format(spider_instance.machine.ip, IP_PORT_DIVIDER, spider_instance.port + 1000)

        logger.info("ctl address: {}".format(ctl_address))
        res = DRSApi.rpc(
            {
                "addresses": [ctl_address],
                "cmds": ["set tc_admin=0", "show slave status"],
                "force": False,
                "bk_cloud_id": self.bk_cloud_id,
            }
        )
        logger.info("find primary show slave status res: {}".format(res))

        if res[0]["error_msg"]:
            raise DBMetaException(message=_("find primary show slave status failed: {}".format(res[0]["error_msg"])))

        slave_info_table_data = res[0]["cmd_results"][1]["table_data"]
        if slave_info_table_data:
            return "{}{}{}".format(
                slave_info_table_data[0]["Master_Host"], IP_PORT_DIVIDER, slave_info_table_data[0]["Master_Port"]
            )
        else:
            return ctl_address
