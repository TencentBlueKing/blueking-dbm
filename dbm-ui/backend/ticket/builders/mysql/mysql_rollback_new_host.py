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
from typing import Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import MASTER_DOMAIN_INITIAL_VALUE, SLAVE_DOMAIN_INITIAL_VALUE, AffinityEnum
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.enums.comm import SystemTagEnum, TagType
from backend.db_meta.models import AppCache, Cluster, DBModule, Machine, Tag
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import RollbackType
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.exceptions import TicketParamsVerifyException
from backend.ticket.models import ClusterOperateRecord, Flow
from backend.utils.time import date2str


def get_backend_machines(cluster: Cluster) -> List[Machine]:
    """获取源集群的后端机器

    主从集群（TenDBHA）为一主一从两台，单节点集群（TenDBSingle）为一台；
    同一机器上可能存在多个实例，这里按 bk_host_id 去重
    """
    storages = cluster.storageinstance_set.select_related("machine").filter(
        instance_role__in=[
            InstanceRole.BACKEND_MASTER.value,
            InstanceRole.BACKEND_SLAVE.value,
            InstanceRole.ORPHAN.value,
        ]
    )
    return list({storage.machine.bk_host_id: storage.machine for storage in storages}.values())


def get_proxy_machines(cluster: Cluster) -> List[Machine]:
    """获取源集群的Proxy机器"""
    proxies = cluster.proxyinstance_set.select_related("machine").all()
    return list({proxy.machine.bk_host_id: proxy.machine for proxy in proxies}.values())


def get_role_spec_id(cluster: Cluster, machines: List[Machine], role: str) -> int:
    """获取某个角色机器的规格ID

    一个集群内同一角色的机器规格是统一的，因此直接取该角色任意一台机器的规格
    """
    if not machines:
        raise TicketParamsVerifyException(errors=_("源集群{}不存在{}机器，无法按源集群规格构造新集群").format(cluster.name, role))

    spec_id = machines[0].spec_id
    if not spec_id:
        raise TicketParamsVerifyException(errors=_("源集群{}的{}机器缺少规格信息，无法按源集群规格申请资源").format(cluster.name, role))
    return spec_id


def get_cluster_resource_spec(cluster: Cluster) -> Dict[str, Dict]:
    """按源集群机器的规格，构造目标集群的资源申请规格

    - 主从集群：一主一从作为一组 backend_group 申请，Proxy 与集群部署单据一致固定申请 2 台
    - 单节点集群：申请 1 台 backend
    """
    backend_spec = {"spec_id": get_role_spec_id(cluster, get_backend_machines(cluster), _("后端")), "count": 1}
    if cluster.cluster_type == ClusterType.TenDBSingle.value:
        return {"backend": backend_spec}

    proxy_spec = {
        "spec_id": get_role_spec_id(cluster, get_proxy_machines(cluster), _("Proxy")),
        # 与集群部署单据保持一致，固定部署两台Proxy
        "count": 2,
        # Proxy 两台一组部署，申请时按组分配，保证机器成对且相互反亲和
        "group_count": 2,
    }
    return {"backend_group": backend_spec, "proxy": proxy_spec}


class MySQLRollbackNewHostDetailSerializer(MySQLBaseOperateDetailSerializer):
    class RollbackNewHostSerializer(serializers.Serializer):

        cluster_id = serializers.IntegerField(help_text=_("源集群ID"))
        rollback_type = serializers.ChoiceField(help_text=_("回档类型"), choices=RollbackType.get_choices())

        rollback_time = DBTimezoneField(
            help_text=_("回档时间"), required=False, allow_blank=True, allow_null=True, default=""
        )
        backupinfo = serializers.DictField(
            help_text=_("备份文件信息"), required=False, allow_null=True, allow_empty=True, default={}
        )
        databases = serializers.ListField(help_text=_("目标库列表"), child=DBTableField(db_field=True))
        databases_ignore = serializers.ListField(
            help_text=_("忽略库列表"), child=DBTableField(db_field=True), required=False, default=list
        )
        tables = serializers.ListField(help_text=_("目标table列表"), child=DBTableField())
        tables_ignore = serializers.ListField(
            help_text=_("忽略table列表"), child=DBTableField(), required=False, default=list
        )
        affect_database_list = serializers.ListField(
            help_text=_("影响的DB"), child=serializers.CharField(), required=False, default=list
        )
        label = serializers.JSONField(help_text=_("资源标签信息"), required=False)

    # 目标集群机器全部按源集群机器的规格从资源池申请，不支持手动录入
    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"),
        choices=[IpSource.RESOURCE_POOL.value],
        required=False,
        default=IpSource.RESOURCE_POOL.value,
    )
    infos = serializers.ListSerializer(help_text=_("回档信息"), child=RollbackNewHostSerializer())
    ignore_check_db = serializers.BooleanField(help_text=_("是否忽略业务库"), required=False, default=False)


class MySQLRollbackNewHostDeployFlowParamBuilder(builders.FlowParamBuilder):
    """回档目标集群部署：部署一个与源集群拓扑一致的临时集群

    部署集群所需的参数已经在 patch_apply_ticket_detail 中组装到 apply_details 中，
    目标机器申请到之后，由资源申请节点的后置动作补充成部署流程所需的 apply_infos
    """

    # 部署流程内部按部署单据类型处理介质包、账号与交付摘要
    deploy_ticket_type = TicketType.MYSQL_HA_APPLY

    def format_ticket_data(self):
        self.ticket_data = dict(self.ticket.details["apply_details"])
        super().add_common_params()
        self.ticket_data.update(ticket_type=self.deploy_ticket_type)


class MySQLRollbackNewHostHADeployFlowParamBuilder(MySQLRollbackNewHostDeployFlowParamBuilder):
    """主从集群部署"""

    controller = MySQLController.mysql_ha_apply_scene
    deploy_ticket_type = TicketType.MYSQL_HA_APPLY


class MySQLRollbackNewHostSingleDeployFlowParamBuilder(MySQLRollbackNewHostDeployFlowParamBuilder):
    """单节点集群部署"""

    controller = MySQLController.mysql_single_apply_scene
    deploy_ticket_type = TicketType.MYSQL_SINGLE_APPLY


class MySQLRollbackNewHostFlowParamBuilder(builders.FlowParamBuilder):
    """回档执行：走定点构造到已有集群的流程（MYSQL_FIXPOINT_EXIST_CLUSTER）"""

    controller = MySQLController.mysql_rollback_to_cluster_scene

    def format_ticket_data(self):
        # 目标集群由前置的集群部署流程创建，这里先占位，实际集群ID在 pre_callback 中回填
        for info in self.ticket_data["infos"]:
            info["rollback_cluster_id"] = 0
        # 流程内部按 MYSQL_FIXPOINT_EXIST_CLUSTER 单据类型处理
        self.ticket_data.update(ticket_type=TicketType.MYSQL_FIXPOINT_EXIST_CLUSTER)

    def pre_callback(self):
        # 目标集群由前置的集群部署流程创建，此处才能拿到目标集群ID
        self.ticket.refresh_from_db(fields=["details"])
        rollback_flow = self.ticket.current_flow()
        apply_details = self.ticket.details["apply_details"]
        target_cluster = Cluster.objects.get(bk_biz_id=self.ticket.bk_biz_id, name=apply_details["cluster_name"])

        ticket_data = rollback_flow.details["ticket_data"]
        # 新机构造的回档目标集群只会有一个
        for info in ticket_data["infos"]:
            info["rollback_cluster_id"] = target_cluster.id
        rollback_flow.save(update_fields=["details"])

        # 记录回档目标集群，便于后续构造回档切换单据
        self.ticket.update_details(target_cluster_id=target_cluster.id)

        # 临时集群打标，并记录本次变更
        temporary_tag, __ = Tag.get_builtin_tag(key=SystemTagEnum.TEMPORARY, value=True, type=TagType.CLUSTER)
        target_cluster.tags.add(temporary_tag)
        ClusterOperateRecord.objects.get_or_create(
            cluster_id=target_cluster.id, ticket=self.ticket, flow=rollback_flow
        )


class MySQLRollbackNewHostResourceParamBuilder(BaseOperateResourceParamBuilder):
    """按源集群机器的规格，申请临时集群所需的机器"""

    def format(self):
        info = self.ticket_data["infos"][0]
        cluster = Cluster.objects.get(id=info["cluster_id"])
        apply_details = self.ticket.details["apply_details"]
        resource_spec = get_cluster_resource_spec(cluster)
        # 资源标签由提单时指定，各角色共用同一份：labels 为标签ID，label_names 为标签名称
        label = info.get("label") or {}

        self.ticket_data = {"resource_spec": resource_spec}
        for role in resource_spec:
            # 临时集群与源集群同城部署，亲和性沿用源集群的容灾级别
            self.patch_common_affinity(info=self.ticket_data, role=role, cluster=cluster, tolerance=0)
            role_spec = self.ticket_data["resource_spec"][role]
            # 与集群部署单据保持一致：非子zone容灾不限定机房
            role_spec["location_spec"] = {
                "city": apply_details["city"],
                "sub_zone_ids": apply_details["zone_list"],
            }
            # 标签与 spec_id 同层，资源池据此精确匹配机器
            role_spec.update(labels=label.get("labels") or [], label_names=label.get("label_names") or [])

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        # 资源申请节点已经把申请到的机器写入 nodes，这里转换成部署集群流程所需的参数
        nodes = ticket_data.pop("nodes", {})

        apply_details = self.ticket.details["apply_details"]
        cluster_name = apply_details["cluster_name"]
        domain = apply_details["domains"][0]
        resource_spec = ticket_data["resource_spec"]

        if apply_details["cluster_type"] == ClusterType.TenDBHA.value:
            backend_groups = nodes.get("backend_group") or []
            proxy_nodes = nodes.get("proxy") or []
            # 一组 backend_group 是一主一从，Proxy 与集群部署单据一致固定两台
            if len(backend_groups) != 1 or len(proxy_nodes) != 2:
                raise TicketParamsVerifyException(
                    errors=_("申请到的backend_group机器组数{}或proxy机器数{}不符合主从集群部署要求").format(
                        len(backend_groups), len(proxy_nodes)
                    )
                )
            # 一组 backend_group 即一主一从，部署流程按 mysql_ip_list[0] 为主库、[1] 为从库
            backend_group = backend_groups[0]
            ticket_data["apply_infos"] = [
                {
                    "clusters": [{"name": cluster_name, "master": domain["master"], "slave": domain["slave"]}],
                    "mysql_ip_list": [backend_group["master"], backend_group["slave"]],
                    "proxy_ip_list": proxy_nodes,
                }
            ]
            # 元数据落库只按 backend/proxy 记录机器规格
            resource_spec["backend"] = resource_spec.pop("master")
            resource_spec.pop("slave", None)
        else:
            backend_nodes = nodes.get("backend") or []
            if not backend_nodes:
                raise TicketParamsVerifyException(errors=_("申请到的backend机器为空，无法部署回档目标集群"))
            ticket_data["apply_infos"] = [
                {
                    "new_ip": backend_nodes[0],
                    "clusters": [{"name": cluster_name, "master": domain["master"]}],
                }
            ]
            resource_spec["single"] = resource_spec.pop("backend")

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_ROLLBACK_NEW_HOST, is_apply=True, iam=ActionEnum.MYSQL_ROLLBACK)
class MySQLRollbackNewHostFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLRollbackNewHostDetailSerializer
    inner_flow_builder = MySQLRollbackNewHostFlowParamBuilder
    inner_flow_name = _("MySQL 新机构造回档执行")
    # 这里不要用batch_builder，因为下一节点是部署临时集群
    resource_apply_builder = MySQLRollbackNewHostResourceParamBuilder
    validator = MySQLController.mysql_rollback_to_cluster_scene.validator

    @classmethod
    def get_target_cluster_name(cls, cluster: Cluster, ticket_id: int) -> str:
        """目标集群名：源集群名加上临时标识，长度过长时退化为固定前缀"""
        cluster_name = f"{cluster.name}-tmp{date2str(datetime.date.today(), '%Y%m%d')}-{ticket_id}"
        return cluster_name if len(cluster_name) <= 48 else f"tmp-rollback-{ticket_id}"

    @classmethod
    def get_cluster_domains(cls, cluster: Cluster, cluster_name: str) -> Dict[str, str]:
        """按集群部署单据的域名规则，生成目标集群的主从域名"""
        db_module_name = DBModule.objects.get(db_module_id=cluster.db_module_id).alias_name
        db_app_abbr = AppCache.get_app_attr(cluster.bk_biz_id)
        # 域名不允许出现下划线，使用连字符替换
        domains = {
            "master": MASTER_DOMAIN_INITIAL_VALUE.format(
                db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=cluster_name
            ).replace("_", "-")
        }
        if cluster.cluster_type == ClusterType.TenDBHA.value:
            domains["slave"] = SLAVE_DOMAIN_INITIAL_VALUE.format(
                db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=cluster_name
            ).replace("_", "-")
        return domains

    @staticmethod
    def get_apply_zone_list(cluster: Cluster) -> List[str]:
        """与集群部署单据保持一致：只有子zone级别的容灾才限定机房列表"""
        if cluster.disaster_tolerance_level in [
            AffinityEnum.CROS_SUBZONE,
            AffinityEnum.SAME_SUBZONE,
            AffinityEnum.SAME_SUBZONE_CROSS_SWTICH,
        ]:
            return cluster.zone_list or []
        return []

    def patch_apply_ticket_detail(self):
        """补充目标集群部署的参数，保证版本、端口、字符集、机器规格与源集群一致

        Proxy 与集群部署单据保持一致固定 2 台，不与源集群的 Proxy 数量对齐；
        后续如需更多 Proxy，由人工提单扩容，不在本流程里自动化补齐
        """
        infos = self.ticket.details["infos"]
        # 目标集群的全部信息都来源于源集群，后续流程都是按 infos[0] 编排的
        if len(infos) != 1:
            raise TicketParamsVerifyException(errors=_("回档新机构造仅支持单个源集群"))

        cluster = Cluster.objects.filter(id=infos[0]["cluster_id"]).first()
        if not cluster:
            raise TicketParamsVerifyException(errors=_("源集群{}不存在").format(infos[0]["cluster_id"]))

        # 目标集群固定按一主一从部署，因此源集群也必须是一主一从的拓扑
        if cluster.cluster_type == ClusterType.TenDBHA.value:
            instance_roles = list(cluster.storageinstance_set.values_list("instance_role", flat=True))
            if (
                len(instance_roles) != 2
                or instance_roles.count(InstanceRole.BACKEND_MASTER.value) != 1
                or instance_roles.count(InstanceRole.BACKEND_SLAVE.value) != 1
            ):
                raise TicketParamsVerifyException(
                    errors=_("主从集群仅支持一主一从的拓扑构造回档，源集群{}的实例角色为{}").format(cluster.name, instance_roles)
                )
        elif cluster.cluster_type != ClusterType.TenDBSingle.value:
            raise TicketParamsVerifyException(
                errors=_("仅支持主从集群或单节点集群构造回档，集群{}的类型为{}").format(cluster.name, cluster.cluster_type)
            )

        cluster_name = self.get_target_cluster_name(cluster, self.ticket.id)
        domains = self.get_cluster_domains(cluster, cluster_name)
        charset, db_version = get_version_and_charset(cluster.bk_biz_id, cluster.db_module_id, cluster.cluster_type)
        # 目标集群的版本要与源集群实际版本一致，模块配置缺失时才退化为模块配置的版本
        db_version = cluster.major_version or db_version

        # 目标集群的端口与源集群保持一致，回档时按端口匹配备份文件
        master = cluster.storageinstance_set.filter(
            instance_role__in=[InstanceRole.BACKEND_MASTER.value, InstanceRole.ORPHAN.value]
        ).first()
        if not master:
            raise TicketParamsVerifyException(errors=_("源集群{}不存在主库实例，无法构造新集群").format(cluster.name))

        apply_details = {
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_name": cluster_name,
            "cluster_type": cluster.cluster_type,
            "db_module_id": cluster.db_module_id,
            "module": str(cluster.db_module_id),
            "city": cluster.region or "default",
            "charset": charset,
            "db_version": db_version,
            "disaster_tolerance_level": cluster.disaster_tolerance_level,
            "zone_list": self.get_apply_zone_list(cluster),
            "ip_source": IpSource.RESOURCE_POOL,
            "inst_num": 1,
            "cluster_count": 1,
            "start_mysql_port": master.port,
            "domains": [{"key": cluster_name, **domains}],
            # 按源集群机器的规格申请资源
            "resource_spec": get_cluster_resource_spec(cluster),
        }
        # 主从集群还需要部署Proxy，端口与源集群保持一致
        proxy = cluster.proxyinstance_set.first()
        if proxy:
            apply_details["start_proxy_port"] = proxy.port

        self.ticket.update_details(apply_details=apply_details)

    def patch_ticket_detail(self):
        self.patch_apply_ticket_detail()
        super().patch_ticket_detail()

    def custom_ticket_flows(self):
        """资源申请（基类按 ip_source=resource_pool 自动插入） → 临时集群部署
        → 定点构造执行 → 确认执行构造回档切换"""
        cluster = Cluster.objects.get(id=self.ticket.details["infos"][0]["cluster_id"])
        deploy_builder = (
            MySQLRollbackNewHostHADeployFlowParamBuilder
            if cluster.cluster_type == ClusterType.TenDBHA.value
            else MySQLRollbackNewHostSingleDeployFlowParamBuilder
        )

        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=deploy_builder(self.ticket).get_params(),
                flow_alias=_("回档临时集群部署"),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            )
        ]

        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=MySQLRollbackNewHostFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("MySQL 定点构造执行"),
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
            )
        )

        return flows

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend(
            [
                _("资源申请"),
                _("回档临时集群部署"),
                _("MySQL 定点构造执行"),
                _("确认执行构造回档切换"),
            ]
        )
        return flow_desc
