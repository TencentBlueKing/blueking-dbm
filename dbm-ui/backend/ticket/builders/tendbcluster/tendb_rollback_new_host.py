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
import datetime
from collections import defaultdict
from typing import Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.components import DBConfigApi
from backend.components.dbconfig import constants as dbconf_const
from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.enums.comm import SystemTagEnum, TagType
from backend.db_meta.models import AppCache, Cluster, Machine, Tag
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder
from backend.ticket.builders.common.constants import FixpointRollbackType
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.mysql.base import DBTableField
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.exceptions import TicketParamsVerifyException
from backend.ticket.models import ClusterOperateRecord, Flow
from backend.utils.time import date2str


def get_cluster_role_machines(cluster: Cluster) -> Dict[str, List[Machine]]:
    """获取源集群 spider_master / spider_slave / remote_db / remote_dr 四种角色对应的机器

    @param cluster: 源集群
    @return: {资源申请角色: 机器列表}，机器按 bk_host_id 去重；
             源集群中不存在的角色不会出现在返回结果中（比如没有只读接入层的集群不会返回 spider_slave）
    """
    # 同一个机器上可能存在多个实例，这里用 dict 按 bk_host_id 去重
    role__host__map = defaultdict(dict)

    # 只部署主接入层和只读接入层：运维节点（spider_mnt / spider_slave_mnt）不参与部署，
    # 中控节点（spider_ctl）由部署流程随 spider_master 一起安装，都不需要单独申请机器
    spiders = cluster.proxyinstance_set.select_related("machine", "tendbclusterspiderext").filter(
        tendbclusterspiderext__spider_role__in=[
            TenDBClusterSpiderRole.SPIDER_MASTER.value,
            TenDBClusterSpiderRole.SPIDER_SLAVE.value,
        ]
    )
    for spider in spiders:
        role__host__map[spider.tendbclusterspiderext.spider_role][spider.machine.bk_host_id] = spider.machine

    # 存储层只取远端主库和远端从库，中继实例（remote_repeater）与主库同机部署，不需要单独申请
    storages = cluster.storageinstance_set.select_related("machine").filter(
        instance_role__in=[InstanceRole.REMOTE_MASTER.value, InstanceRole.REMOTE_SLAVE.value]
    )
    for storage in storages:
        role = "remote_db" if storage.instance_role == InstanceRole.REMOTE_MASTER.value else "remote_dr"
        role__host__map[role][storage.machine.bk_host_id] = storage.machine

    return {role: list(hosts.values()) for role, hosts in role__host__map.items()}


def get_role_spec_id(cluster: Cluster, role: str, machines: List[Machine]) -> int:
    """获取某个角色机器的规格ID

    一个集群内同一角色的机器规格是统一的（spider_master / spider_slave 各自统一，
    存储层的 remote 主从机器也统一），因此直接取该角色任意一台机器的规格
    """
    spec_id = machines[0].spec_id
    if not spec_id:
        raise TicketParamsVerifyException(errors=_("源集群{}的{}机器缺少规格信息，无法按源集群规格申请资源").format(cluster.name, role))
    return spec_id


def get_cluster_role_resource_spec(cluster: Cluster) -> Dict[str, Dict]:
    """按源集群各角色机器的规格，构造目标集群的资源申请规格

    存储层使用 backend_group 分组向资源池申请：一组包含一对 remote 主从机器，
    与 TenDB Cluster 集群部署单据一致，资源池会保证同组主从的反亲和；
    由于集群内 remote 机器规格统一，主从可以使用同一份规格。

    @param cluster: 源集群
    @return: {资源申请角色: {"spec_id": 规格ID, "count": 数量}}
             接入层的 count 为机器数量，backend_group 的 count 为机器组数（主从对数）
    """
    role__machines__map = get_cluster_role_machines(cluster)
    resource_spec = {}

    # 接入层：spider_master 与 spider_slave 的规格各自统一，分别申请
    for role in [TenDBClusterSpiderRole.SPIDER_MASTER.value, TenDBClusterSpiderRole.SPIDER_SLAVE.value]:
        machines = role__machines__map.get(role)
        if not machines:
            continue
        resource_spec[role] = {"spec_id": get_role_spec_id(cluster, role, machines), "count": len(machines)}

    # 存储层：remote_db 与 remote_dr 一台对一台，按机器组数申请 backend_group
    remote_db_machines = role__machines__map.get("remote_db") or []
    if remote_db_machines:
        resource_spec["backend_group"] = {
            "spec_id": get_role_spec_id(cluster, "remote_db", remote_db_machines),
            "count": len(remote_db_machines),
        }

    return resource_spec


def get_apply_city(cluster: Cluster) -> str:
    """目标集群与源集群同城部署，城市为空时取默认城市"""
    return cluster.region or "default"


def get_apply_zone_list(cluster: Cluster) -> List[str]:
    """与集群部署单据保持一致：只有子zone级别的容灾才限定机房列表"""
    if cluster.disaster_tolerance_level in [
        AffinityEnum.CROS_SUBZONE,
        AffinityEnum.SAME_SUBZONE,
        AffinityEnum.SAME_SUBZONE_CROSS_SWTICH,
    ]:
        return cluster.zone_list or []
    return []


class TendbRollbackNewHostDetailSerializer(TendbBaseOperateDetailSerializer):
    class RollbackNewHostSerializer(serializers.Serializer):

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        rollback_type = serializers.ChoiceField(help_text=_("回档类型"), choices=FixpointRollbackType.get_choices())

        rollback_time = DBTimezoneField(
            help_text=_("回档时间"), required=False, allow_blank=True, allow_null=True, default=""
        )
        backupinfo = serializers.DictField(
            help_text=_("备份文件信息"), required=False, allow_null=True, allow_empty=True, default={}
        )
        databases = serializers.ListField(help_text=_("目标库列表"), child=DBTableField(db_field=True))
        databases_ignore = serializers.ListField(
            help_text=_("忽略库列表"), child=DBTableField(db_field=True), required=False
        )
        tables = serializers.ListField(help_text=_("目标table列表"), child=DBTableField())
        tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=DBTableField(), required=False)
        affect_database_list = serializers.ListField(
            help_text=_("影响的DB"), child=serializers.CharField(), allow_null=True, required=False
        )
        label = serializers.JSONField(help_text=_("资源标签信息"), required=False)

    # 目标集群机器全部按源集群各角色机器的规格从资源池申请，不支持手动录入
    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"),
        choices=[IpSource.RESOURCE_POOL.value],
        required=False,
        default=IpSource.RESOURCE_POOL.value,
    )
    infos = serializers.ListSerializer(help_text=_("回档信息"), child=RollbackNewHostSerializer())
    ignore_check_db = serializers.BooleanField(help_text=_("是否忽略业务库"), required=False, default=False)


class TendbApplyTempClusterFlowParamBuilder(builders.FlowParamBuilder):
    """回档目标集群部署：部署一个与源集群完全一致的集群（spider_master + remote master + remote slave）"""

    controller = SpiderController.spider_cluster_apply_scene

    def format_ticket_data(self):
        # 部署集群所需的参数已经在 patch_apply_ticket_detail 中组装到 apply_details 中，
        # 目标机器信息由资源申请节点写入 nodes 后，在资源申请的后置动作中补充
        self.ticket_data = self.ticket_data["apply_details"]
        super().add_common_params()
        # 流程内部按集群部署单据类型处理（介质包、账号等），这里对齐为 TENDBCLUSTER_APPLY
        self.ticket_data.update(ticket_type=TicketType.TENDBCLUSTER_APPLY)


class TendbApplyTempClusterSlaveFlowParamBuilder(builders.FlowParamBuilder):
    """回档目标集群只读接入层部署：源集群存在 spider_slave 时，目标集群也需要部署 read-only 接入层"""

    controller = SpiderController.spider_slave_cluster_apply_scene

    def format_ticket_data(self):
        # 集群部署所需的公共参数（端口、字符集、版本、云区域等）沿用集群部署的入参，
        # 只有目标集群ID需要等集群部署流程执行后才能拿到，因此在 pre_callback 中填充 infos
        self.ticket_data = dict(self.ticket.details["apply_details"])
        self.ticket_data["infos"] = []
        super().add_common_params()
        # 与集群部署流程保持一致，按部署单据类型处理介质包与账号
        self.ticket_data.update(ticket_type=TicketType.TENDBCLUSTER_APPLY)

    def pre_callback(self):
        # 目标集群由前置的集群部署流程创建，此处才能拿到目标集群ID
        self.ticket.refresh_from_db(fields=["details"])
        apply_details = self.ticket.details["apply_details"]
        spider_slave_hosts = self.ticket.details.get("nodes", {}).get("spider_slave") or []
        if not spider_slave_hosts:
            raise TicketParamsVerifyException(errors=_("源集群存在只读接入层，但未申请到spider_slave机器，无法部署目标集群的只读接入层"))

        target_cluster = Cluster.objects.get(name=apply_details["cluster_name"])
        slave_flow = self.ticket.current_flow()
        slave_flow.details["ticket_data"].update(
            infos=[
                {
                    "cluster_id": target_cluster.id,
                    "spider_slave_ip_list": spider_slave_hosts,
                    "slave_domain": apply_details["slave_domain"],
                }
            ]
        )
        slave_flow.save(update_fields=["details"])


class TendbRollbackNewHostFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendb_cluster_rollback_data

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["source_cluster_id"] = info.pop("cluster_id")

    def pre_callback(self):
        # 目标集群由前置的集群部署流程创建，此处回填回档目标集群信息
        rollback_flow = self.ticket.current_flow()
        ticket_data = rollback_flow.details["ticket_data"]
        # 新部署集群的回档，infos只会有一个元素
        info = ticket_data["infos"][0]
        target_cluster = Cluster.objects.get(name=self.ticket.details["apply_details"]["cluster_name"])
        info.update(target_cluster_id=target_cluster.id)
        rollback_flow.save(update_fields=["details"])
        # 记录回档目标集群，后续人工确认执行时据此发起构造回档切换单据
        self.ticket.update_details(target_cluster_id=target_cluster.id)

        # 对临时集群记录变更
        temporary_tag, __ = Tag.get_builtin_tag(key=SystemTagEnum.TEMPORARY, value=True, type=TagType.CLUSTER)
        target_cluster.tags.add(temporary_tag)
        ClusterOperateRecord.objects.get_or_create(
            cluster_id=target_cluster.id, ticket=self.ticket, flow=rollback_flow
        )


class TendbRollbackNewHostResourceParamBuilder(BaseOperateResourceParamBuilder):
    """按源集群各角色机器的规格，申请目标集群所需的机器"""

    def format(self):
        info = self.ticket_data["infos"][0]
        cluster = Cluster.objects.get(id=info["cluster_id"])
        resource_spec = get_cluster_role_resource_spec(cluster)
        # 位置信息与集群部署单据保持一致：同城部署，非子zone容灾不限定机房
        location_spec = {"city": get_apply_city(cluster), "sub_zone_ids": get_apply_zone_list(cluster)}
        # 资源标签由提单时指定，各角色共用同一份：labels 为标签ID，label_names 为标签名称
        label = info.get("label") or {}

        self.ticket_data = {"resource_spec": resource_spec}
        for role in resource_spec:
            role_spec = self.ticket_data["resource_spec"][role]
            # 目标集群机器与源集群同城部署，亲和性沿用源集群的容灾级别；
            # 接入层允许一定程度的机型偏差，与集群部署单据保持一致
            self.patch_common_affinity(
                info=self.ticket_data,
                role=role,
                cluster=cluster,
                tolerance=0.5 if role.startswith("spider") else 0,
            )
            role_spec["location_spec"] = dict(location_spec)
            # 标签与 spec_id 同层，资源池据此精确匹配机器
            role_spec.update(labels=label.get("labels") or [], label_names=label.get("label_names") or [])

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        # 资源申请节点已经把申请到的机器写入 nodes，这里转换成部署集群流程所需的参数
        nodes = ticket_data.pop("nodes", {})

        spider_ip_list = nodes.get("spider_master") or []
        # backend_group 中的每一组即一对 remote 主从机器，可直接作为部署流程的 remote_group
        remote_group = nodes.get("backend_group") or []
        if not spider_ip_list or not remote_group:
            raise TicketParamsVerifyException(errors=_("申请到的spider_master或remote机器为空，无法部署回档目标集群"))

        # 目标集群与源集群分片数保持一致，按实际申请到的机器组数计算单机分片数
        cluster_shard_num = int(ticket_data["cluster_shard_num"])
        remote_machine_count = len(remote_group)
        if cluster_shard_num % remote_machine_count:
            raise TicketParamsVerifyException(
                errors=_("集群分片数{}无法按申请到的机器组数{}均分，无法部署回档目标集群").format(cluster_shard_num, remote_machine_count)
            )

        ticket_data.update(
            # 中控节点复用spider机器，随集群部署流程自动安装
            spider_ip_list=spider_ip_list,
            remote_group=remote_group,
            remote_shard_num=cluster_shard_num // remote_machine_count,
        )

        # 元数据落库时只按 spider/remote 两种机器类型记录规格，这里补充对应规格信息
        resource_spec = ticket_data["resource_spec"]
        resource_spec["spider"] = resource_spec["spider_master"]
        resource_spec["remote"] = resource_spec.pop("master")
        resource_spec.pop("slave", "")

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(
    TicketType.TENDBCLUSTER_ROLLBACK_NEW_HOST, is_apply=True, iam=ActionEnum.TENDBCLUSTER_ROLLBACK
)
class TendbRollbackNewHostFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbRollbackNewHostDetailSerializer
    inner_flow_builder = TendbRollbackNewHostFlowParamBuilder
    inner_flow_name = _("TenDBCluster 新机构造回档执行")
    # 这里不要用batch_builder，因为下一节点是部署临时集群
    resource_apply_builder = TendbRollbackNewHostResourceParamBuilder
    validator = SpiderController.tendb_cluster_rollback_data.validator

    @classmethod
    def get_spider_port(cls, cluster: Cluster) -> int:
        """获取源集群spider_master的端口，作为目标集群的访问端口"""
        spider = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        ).first()
        if not spider:
            raise TicketParamsVerifyException(errors=_("源集群{}不存在spider_master节点").format(cluster.name))
        return spider.port

    @classmethod
    def get_cluster_config(cls, cluster: Cluster, details: Dict):
        """获取源集群所在db模块的字符集、版本信息"""
        db_config = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": dbconf_const.LevelName.MODULE,
                "level_value": str(cluster.db_module_id),
                "conf_file": dbconf_const.DEPLOY_FILE_NAME,
                "conf_type": dbconf_const.ConfType.DEPLOY,
                "namespace": ClusterType.TenDBCluster,
                "format": dbconf_const.FormatType.MAP,
            }
        )["content"]

        details.update(
            charset=db_config.get("charset"),
            db_version=db_config.get("db_version"),
            spider_version=db_config.get("spider_version"),
        )

    def patch_apply_ticket_detail(self):
        """补充目标集群部署的参数，保证目标集群与源集群完全一致"""
        infos = self.ticket.details["infos"]
        # 目标集群的全部信息都来源于源集群，后续流程都是按 infos[0] 编排的
        if len(infos) != 1:
            raise TicketParamsVerifyException(errors=_("回档新机构造仅支持单个源集群"))

        cluster = Cluster.objects.filter(id=infos[0]["cluster_id"]).first()
        if not cluster:
            raise TicketParamsVerifyException(errors=_("源集群{}不存在").format(infos[0]["cluster_id"]))

        cluster_name = f"{cluster.name}-tmp{date2str(datetime.date.today(), '%Y%m%d')}-{self.ticket.id}"
        db_app_abbr = AppCache.get_app_attr(cluster.bk_biz_id)
        role__machines__map = get_cluster_role_machines(cluster)

        # 目标集群与源集群的分片数、单机分片数保持一致
        cluster_shard_num = cluster.tendbclusterstorageset_set.count()
        remote_db_machines = role__machines__map.get("remote_db") or []
        if not remote_db_machines:
            raise TicketParamsVerifyException(errors=_("源集群{}不存在remote_db节点，无法构造新集群").format(cluster.name))
        remote_db_count = len(remote_db_machines)

        # 存储层按 remote 主从一对一申请 backend_group，主从机器数必须一致
        remote_dr_count = len(role__machines__map.get("remote_dr") or [])
        if remote_db_count != remote_dr_count:
            raise TicketParamsVerifyException(
                errors=_("源集群{}的remote_db机器数{}与remote_dr机器数{}不一致，无法构造新集群").format(
                    cluster.name, remote_db_count, remote_dr_count
                )
            )

        apply_details = {
            "bk_cloud_id": cluster.bk_cloud_id,
            "db_app_abbr": db_app_abbr,
            "cluster_name": cluster_name,
            "city": get_apply_city(cluster),
            "module": cluster.db_module_id,
            "db_module_id": cluster.db_module_id,
            "disaster_tolerance_level": cluster.disaster_tolerance_level,
            "zone_list": get_apply_zone_list(cluster),
            "immutable_domain": f"spider.{cluster_name}.{db_app_abbr}.db",
            "slave_domain": f"spider-slave.{cluster_name}.{db_app_abbr}.db",
            "ip_source": IpSource.RESOURCE_POOL,
            "spider_port": self.get_spider_port(cluster),
            "cluster_shard_num": cluster_shard_num,
            "remote_shard_num": cluster_shard_num // remote_db_count,
            # 源集群是否存在只读接入层，决定目标集群是否需要部署 spider_slave
            "has_spider_slave": bool(role__machines__map.get("spider_slave")),
            # 按源集群各角色机器的规格申请资源
            "resource_spec": get_cluster_role_resource_spec(cluster),
        }
        # 填充字符集、版本信息
        self.get_cluster_config(cluster, apply_details)

        self.ticket.update_details(apply_details=apply_details)

    def patch_ticket_detail(self):
        self.patch_apply_ticket_detail()
        super().patch_ticket_detail()

    def custom_ticket_flows(self):
        flows = []

        # 部署目标集群
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TendbApplyTempClusterFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("回档临时集群部署"),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            )
        )

        # 部署目标集群的只读接入层，源集群没有spider_slave时无需部署
        if self.ticket.details["apply_details"]["has_spider_slave"]:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=TendbApplyTempClusterSlaveFlowParamBuilder(self.ticket).get_params(),
                    flow_alias=_("回档临时集群只读接入层部署"),
                    retry_type=FlowRetryType.MANUAL_RETRY.value,
                )
            )

        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TendbRollbackNewHostFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("TenDBCluster 回档执行"),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            )
        )
        # 回档执行完成后的人工确认节点，确认执行后由单据状态钩子发起构造回档切换单据
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.PAUSE.value,
                details=self.pause_node_builder(self.ticket).get_params(),
                flow_alias=_("确认执行构造回档切换"),
            ),
        )

        return flows

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend([_("回档临时集群部署"), _("回档临时集群只读接入层部署"), _("TenDBCluster 回档执行"), _("确认执行构造回档切换")])
        return flow_desc
