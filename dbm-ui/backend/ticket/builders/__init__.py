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
import copy
import importlib
import itertools
import json
import logging
import math
import os
from collections import defaultdict
from typing import Callable, Dict, List, Union

from django.db.models import Count, Q
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend import env
from backend.configuration.constants import AffinityEnum, DBType, SystemSettingsEnum
from backend.configuration.models import DBAdministrator, SystemSettings
from backend.db_meta.enums import MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import AppCache, Cluster, Machine, ProxyInstance, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket.constants import TICKET_EXPIRE_DEFAULT_CONFIG, FlowRetryType, FlowType, TicketType
from backend.ticket.exceptions import TicketResourceApplyException
from backend.ticket.models import Flow, Ticket, TicketFlowsConfig
from backend.utils.register import re_import_modules

logger = logging.getLogger("root")


class CallBackBuilderMixin(object):
    """为节点添加前置/后继钩子函数信息"""

    def __init__(self, ticket: Ticket):
        self.ticket = ticket

    def pre_callback(self):
        pass

    def post_callback(self):
        pass

    def add_common_params(self):
        self.ticket_data.update(
            {
                "uid": self.ticket.id,
                "ticket_type": self.ticket.ticket_type,
                "created_by": self.ticket.creator,
                "bk_biz_id": self.ticket.bk_biz_id,
            }
        )

    def build_callback_info(self) -> Dict:
        return {
            "pre_callback_module": self.pre_callback.__module__,
            "pre_callback_class": self.pre_callback.__qualname__.split(".")[0],
            "post_callback_module": self.post_callback.__module__,
            "post_callback_class": self.post_callback.__qualname__.split(".")[0],
        }

    def inject_callback_in_params(self, params: Dict = None) -> Dict:
        params = params or {}
        params.update({"callback_info": self.build_callback_info()})
        return params


class FlowParamBuilder(CallBackBuilderMixin):
    """
    Flow 参数构建器
    职责：将单据详情（ticket.details）转化为 Flow 流程运行所需的参数
    """

    # 配置任务流程控制器：流程启动函数
    controller = None

    def __init__(self, ticket: Ticket):
        self.ticket = ticket
        self.ticket_data = copy.deepcopy(ticket.details)

    def build_controller_info(self) -> dict:
        return {
            "func_name": self.controller.__name__,
            "class_name": self.controller.__qualname__.split(".")[0],
            "module": self.controller.__module__,
        }

    def format_ticket_data(self):
        """格式化单据数据，由子类实现"""
        pass

    def get_params(self) -> dict:
        self.add_common_params()
        self.format_ticket_data()

        params = {
            "ticket_data": copy.deepcopy(self.ticket_data),
            "controller_info": self.build_controller_info(),
        }
        params = super().inject_callback_in_params(params=params)

        if env.ENVIRONMENT == "dev":
            logger.info("flow.bamboo.params: \n%s\n", json.dumps(params, indent=2))

        return params


class ItsmParamBuilder(CallBackBuilderMixin):
    """
    ITSM 参数构建器
    职责：将单据详情（ticket.details）转化为 ITSM 单据创建所需的参数
    - 定义单据的审批人，默认取对应 DB 类型的管理员
    - 格式化单据概览，提高单据的可读性
    """

    def __init__(self, ticket: Ticket):
        self.ticket = ticket
        self.details = copy.deepcopy(ticket.details)

    def get_approvers(self):
        db_type = BuilderFactory.registry[self.ticket.ticket_type].group
        approvers = DBAdministrator.get_biz_db_type_admins(self.ticket.bk_biz_id, db_type)
        # 审批默认加上admin
        if "admin" not in approvers:
            approvers.append("admin")
        return ",".join(approvers)

    def format(self):
        pass

    def get_params(self):
        self.format()
        # clusters只是为了给服务单详情展示的信息，不需要在单据中体现
        cluster_domains = [cluster["immute_domain"] for cluster in self.details.pop("clusters", {}).values()]
        service_id = SystemSettings.get_setting_value(SystemSettingsEnum.BK_ITSM_SERVICE_ID.value)
        title = _("【DBM单据审批】{}").format(self.ticket.get_ticket_type_display())
        app = AppCache.objects.get(bk_biz_id=self.ticket.bk_biz_id)
        params = {
            "service_id": service_id,
            "creator": self.ticket.creator,
            "fields": [
                {"key": "title", "value": title},
                {"key": "app", "value": f"{app.bk_biz_name}(#{app.bk_biz_id}, {app.db_app_abbr})"},
                {"key": "domain", "value": "\n".join(cluster_domains)},
                {"key": "summary", "value": self.ticket.remark},
                {"key": "approver", "value": self.get_approvers()},
                {"key": "ticket_url", "value": self.ticket.iframe_url},
            ],
            "dynamic_fields": [],
            "meta": {
                "callback_url": f"{env.BK_SAAS_CALLBACK_URL}/apis/tickets/{self.ticket.id}/callback/",
                "state_processors": {},
            },
        }
        params = super().inject_callback_in_params(params=params)

        if env.ENVIRONMENT == "dev":
            logger.debug("flow.itsm.params: \n%s\n", json.dumps(params, indent=2))

        return params


class PauseParamBuilder(CallBackBuilderMixin):
    """
    Pause 参数构造器
    职责：为暂停任务提供单据参数
    预写参数:
     - pause_type: 可表示暂停的类型
    """

    def __init__(self, ticket: Ticket):
        self.ticket = ticket
        self.ticket_data = copy.deepcopy(ticket.details)
        self.params = {"pause_type": None}

    @property
    def operators(self):
        """当前单据指定处理人"""
        return []

    def format(self):
        """
        这里可以为params添加更多参数
        适配更加复杂的场景
        """
        pass

    def get_params(self):
        self.format()
        self.params.update(operators=self.operators)
        self.params = super().inject_callback_in_params(params=self.params)
        return self.params


class ResourceApplyParamBuilder(CallBackBuilderMixin):
    """
    ResourceApply资源申请 参数构造器
    职责：为资源申请提供额外参数，并为后继的inner flow节点更新信息
    """

    # 是否运行申请资源为空，运行的情况下跳过该item的资源申请
    allow_resource_empty: bool = False

    def __init__(self, ticket: Ticket):
        self.ticket = ticket
        self.ticket_data = copy.deepcopy(ticket.details)

    def format(self):
        """
        这里可以为params添加更多参数
        适配更加复杂的场景
        """
        pass

    def validate_spec(self):
        if self.allow_resource_empty:
            return

        resource_list = []
        if self.ticket_data.get("infos"):
            for info in self.ticket_data["infos"]:
                if info.get("resource_spec"):
                    resource_list.append(info["resource_spec"])
        if self.ticket_data.get("resource_spec"):
            resource_list.append(self.ticket_data["resource_spec"])

        for resource in resource_list:
            for role in resource:
                if not resource[role]:
                    continue
                spec_id = resource[role].get("spec_id")
                hosts = resource[role].get("hosts")
                apply_count = resource[role].get("count")
                # spec_id 为0 且有hosts为手动选择资源
                if not spec_id and not hosts:
                    raise TicketResourceApplyException(_("申请资源的规格id不能为0或为空"))
                if not apply_count and not hosts:
                    raise TicketResourceApplyException(_("申请资源的数量不能为0或为空"))

    def get_params(self):
        self.format()
        self.ticket_data.update(allow_resource_empty=self.allow_resource_empty)
        self.validate_spec()
        super().add_common_params()
        super().inject_callback_in_params(params=self.ticket_data)
        return self.ticket_data

    def post_callback(self):
        """
        部署单据需要有特殊的参数填充或者逻辑处理，
        需要在各自的ResourceApplyParamBuilder重写post_callback
        """
        pass

    @staticmethod
    def patch_common_affinity(
        info: dict,
        role: str,
        cluster: Cluster,
        exclusive_hosts: List[Machine] = None,
        tolerance: float = 0,
        no_need_affinity: bool = False,
    ):
        """
        针对扩容、替换、部署场景，补充亲和性参数
        @param info: 申请信息
        @param role: 分组名称
        @param cluster: 集群
        @param exclusive_hosts: 互斥主机(要求园区/机架亲和性)
        @param tolerance: 亲和性容忍度
        @param no_need_affinity: 是否需要亲和性
        """

        # 补充云区域和业务信息
        info.update(bk_cloud_id=cluster.bk_cloud_id, bk_biz_id=cluster.bk_biz_id)

        # 如果不存在资源池匹配，或者是资源池手动选择，则跳过
        if role not in info["resource_spec"] or "hosts" in info["resource_spec"][role]:
            return

        resource_spec = info["resource_spec"]
        affinity = cluster.disaster_tolerance_level
        # 对互斥主机进行去重
        exclusive_hosts = exclusive_hosts or []
        exclusive_hosts = list({host.bk_host_id: host for host in exclusive_hosts}.values())

        # 如果不需要亲和性，则更新城市，亲和性固定为None
        if no_need_affinity:
            resource_spec[role]["location_spec"] = {"city": cluster.region, "sub_zone_ids": []}
            resource_spec[role]["affinity"] = AffinityEnum.NONE
            return

        # 获取互斥机器园区、园区信息
        current_hosts = [
            {
                "ip": host.ip,
                "bk_host_id": host.bk_host_id,
                "sub_zone": host.bk_sub_zone,
                "sub_zone_id": str(host.bk_sub_zone_id),
                "rack_id": str(host.bk_rack_id),
            }
            for host in exclusive_hosts
        ]

        resource_spec[role].update(
            affinity=affinity,
            location_spec={"city": cluster.region, "sub_zone_ids": cluster.zone_list or []},
            tolerance=tolerance,
            current_hosts=current_hosts,
        )

    def patch_info_common_affinity(
        self,
        role: str,
        remain_machine_type: str = None,
        replace_key: str = None,
        tolerance: Union[Callable, float] = None,
        no_need_affinity: bool = False,
        tolerance_type: str = None,
    ):
        """
        针对批量扩容、替换补充亲和性参数
        @param role 分组名称
        @param remain_machine_type 库存机器类型
        @param replace_key 替换实例key
        @param tolerance: 亲和性容忍度
        @param no_need_affinity: 是否需要亲和性
        @param tolerance_type: 亲和性容忍度类型
        """
        # 获得infos中的集群信息
        from backend.ticket.builders.common.base import fetch_cluster_ids

        def __get_exclusive_hosts():
            """找到集群和存量机型的映射"""

            # 存量主机的通用过滤
            common_filters = Q(machine__machine_type=remain_machine_type, cluster__in=cluster_ids) & ~Q(
                machine__bk_host_id__in=off_host_ids
            )

            # 如果是slave替换，则找到对应master
            if remain_machine_type == "master":
                slave_insts = StorageInstance.objects.prefetch_related("as_receiver__ejector__machine").filter(
                    machine__bk_host_id__in=off_host_ids
                )
                for slave in slave_insts:
                    master = slave.as_receiver.first().ejector.machine
                    cluster__remain_hosts_map[slave.cluster.first().id].append(master)
            # 如果机器类型是spider，则考虑spider master
            elif remain_machine_type == MachineType.SPIDER.value:
                spider_masters = ProxyInstance.objects.select_related("machine").filter(
                    common_filters, tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                )
                for spider_master in spider_masters:
                    cluster__remain_hosts_map[spider_master.cluster.first().id].append(spider_master.machine)
            # 找到集群和存量机型的映射
            elif remain_machine_type:
                storage_insts = list(StorageInstance.objects.select_related("machine").filter(common_filters))
                proxy_insts = list(ProxyInstance.objects.select_related("machine").filter(common_filters))
                for inst in storage_insts + proxy_insts:
                    cluster__remain_hosts_map[inst.cluster.first().id].append(inst.machine)

            return cluster__remain_hosts_map

        infos = self.ticket_data["infos"]
        cluster_ids = fetch_cluster_ids(infos)
        cluster_map = Cluster.objects.in_bulk(cluster_ids)
        tolerance = tolerance or 0

        cluster__remain_hosts_map = defaultdict(list)
        off_host_ids = []
        # 如果有replace_key，则说明是替换单据，找到替换的机器
        if replace_key:
            off_host_ids = [host["bk_host_id"] for info in infos for host in info["old_nodes"][replace_key]]
        # 考虑存量机型
        if remain_machine_type:
            cluster__remain_hosts_map = __get_exclusive_hosts()

        for info in infos:
            cluster = cluster_map[fetch_cluster_ids(info)[0]]
            cluster_tolerance = (
                tolerance(cluster.disaster_tolerance_level, tolerance_type)
                if isinstance(tolerance, Callable)
                else tolerance
            )
            exclusive_hosts = cluster__remain_hosts_map.get(cluster.id, [])
            self.patch_common_affinity(info, role, cluster, exclusive_hosts, cluster_tolerance, no_need_affinity)

    def patch_info_affinity_location(self, roles=None, replace_zone=None):
        """
        批量节点变更的时候，补充亲和性和位置参数
        TODO: 暂定废弃，改用patch_common_affinity/patch_info_common_affinity
        """
        from backend.ticket.builders.common.base import fetch_cluster_ids, fetch_host_ips

        machine_zone_map = {}
        # 处理替换指定园区
        if replace_zone:
            host_ips = fetch_host_ips(self.ticket_data["infos"])
            machine_zone_map = {host.ip: host.bk_sub_zone_id for host in Machine.objects.filter(ip__in=host_ips)}

        cluster_ids = fetch_cluster_ids(self.ticket_data["infos"])
        cluster_id_map = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in self.ticket_data["infos"]:
            cluster = cluster_id_map[fetch_cluster_ids(info)[0]]
            affinity = cluster.disaster_tolerance_level
            if (
                affinity
                in [AffinityEnum.CROS_SUBZONE, AffinityEnum.CROSS_SUBZONE_STRONG, AffinityEnum.CROSS_SUBZONE_WEAK]
                and machine_zone_map
            ):
                replace_zone = [machine_zone_map[fetch_host_ips(info["old_nodes"])[0]]]
            else:
                replace_zone = []
            self.patch_affinity_location(cluster, info["resource_spec"], roles, replace_zone)
            # 工具箱操作，补充业务和云区域ID
            info.update(bk_cloud_id=cluster.bk_cloud_id, bk_biz_id=self.ticket.bk_biz_id)

    @classmethod
    def patch_affinity_location(cls, cluster, resource_spec, roles=None, replace_zone: list = None):
        """
        节点变更的时候，补充亲和性和位置参数
        TODO: 暂定废弃，改用patch_common_affinity/patch_info_common_affinity
        """

        bk_sub_zone_ids = replace_zone or cluster.zone_list
        resource_role = roles or resource_spec.keys()
        for role in resource_role:
            resource_spec[role]["affinity"] = cluster.disaster_tolerance_level
            resource_spec[role]["location_spec"] = {"city": cluster.region, "sub_zone_ids": []}
            if bk_sub_zone_ids:
                resource_spec[role]["location_spec"].update(sub_zone_ids=bk_sub_zone_ids, include_or_exclue=True)


class RecycleCleanMachineParamBuilder(FlowParamBuilder):
    """
    回收清理主机流程 参数构建器
    职责：获取单据中的下架机器，并走回收流程
    """

    controller_map = {
        DBType.MySQL.value: "mysql.MySQLController.mysql_machine_clear_scene",
        DBType.TenDBCluster.value: "spider.SpiderController.tendbcluster_machine_clear_scene",
        DBType.Doris.value: "doris.DorisController.doris_machine_clear_scene",
        DBType.Kafka.value: "kafka.KafkaController.kafka_machine_clear_scene",
        DBType.Es.value: "es.EsController.es_machine_clear_scene",
        DBType.Hdfs.value: "hdfs.HdfsController.hdfs_machine_clear_scene",
        DBType.Pulsar.value: "pulsar.PulsarController.pulsar_machine_clear_scene",
        DBType.Vm.value: "vm.VmController.vm_machine_clear_scene",
        DBType.Redis.value: "redis.RedisController.redis_machine_clear_scene",
        # TODO sqlserver，mongo，riak清理流程暂时没有
        DBType.Sqlserver.value: "",
        DBType.MongoDB.value: "",
        DBType.Riak.value: "",
    }

    def __init__(self, ticket: Ticket):
        super().__init__(ticket)

    def build_controller_info(self) -> dict:
        db_type = self.ticket_data["db_type"]
        # TODO: 暂时兼容没有清理流程的组件，默认用mysql
        clear_db_type = db_type if self.controller_map.get(db_type) else DBType.MySQL.value

        file_name, class_name, flow_name = self.controller_map[clear_db_type].split(".")
        module = importlib.import_module(f"backend.flow.engine.controller.{file_name}")
        self.controller = getattr(getattr(module, class_name), flow_name)

        return super().build_controller_info()

    def format_ticket_data(self):
        hosts = self.ticket_data["recycle_hosts"]
        self.ticket_data.update(
            {
                "hosts": hosts,
                # 一批机器的操作系统类型一致，任取一个即可
                "os_name": hosts[0]["os_name"],
                "os_type": hosts[0]["os_type"],
                "db_type": self.ticket_data["group"],
            }
        )


class TicketFlowBuilder:
    """
    单据流程构建器
    职责：定义单据流程（ticket_flow），实例化单据流程对象并结合 FlowParamBuilder/ItsmParamBuilder 生成所需参数
    """

    ticket_type = None
    group = None
    serializer = None
    alarm_transform_serializer = None

    # 默认任务参数构造器
    inner_flow_name: str = ""
    inner_flow_builder: FlowParamBuilder = None
    # 默认暂停参数构造器
    pause_node_builder: PauseParamBuilder = PauseParamBuilder
    # 默认审批参数构造器
    itsm_flow_builder: ItsmParamBuilder = ItsmParamBuilder
    # 默认资源申请参数构造器
    # resource_apply_builder和resource_batch_apply_builder只能存在其一，表示是资源池单次申请还是批量申请
    resource_apply_builder: ResourceApplyParamBuilder = None
    resource_batch_apply_builder: ResourceApplyParamBuilder = None

    # inner flow互斥的重试类型，默认为手动重试
    retry_type: FlowRetryType = FlowRetryType.MANUAL_RETRY
    # 默认是否需要审批,人工确认。后续用于初始化单据配置表
    default_need_itsm: bool = True
    default_need_manual_confirm: bool = True
    # 默认过期时间配置
    default_expire_config: dict = TICKET_EXPIRE_DEFAULT_CONFIG
    # 是否用户可修改单据流程(在单据配置表中)
    editable: bool = True
    # 参数校验器
    validator = None

    def __init__(self, ticket: Ticket):
        self.ticket = ticket

    @classmethod
    def name(cls):
        return cls.__name__

    @classmethod
    def type(cls):
        return cls.__name__.lower()

    @classmethod
    def enabled(cls) -> bool:
        """
        是否开启，默认开启
        可考虑使用功能开关控制
        """
        return True

    @property
    def ticket_configs(self):
        if not hasattr(self, "_ticket_configs"):
            from backend.ticket.builders.common.base import fetch_cluster_ids

            cluster_ids = fetch_cluster_ids(self.ticket.details)
            configs = TicketFlowsConfig.get_cluster_configs(self.ticket_type, self.ticket.bk_biz_id, cluster_ids)
            setattr(self, "_ticket_configs", configs)
        return getattr(self, "_ticket_configs")

    @property
    def need_itsm(self):
        """是否需要itsm审批节点。后续默认从单据配置表获取。子类可覆写，覆写以后editable为False"""
        need_itsm = any([c.configs["need_itsm"] for c in self.ticket_configs])
        return need_itsm

    @property
    def need_manual_confirm(self):
        """是否需要人工确认节点。后续默认从单据配置表获取。子类可覆写，覆写以后editable为False"""
        need_manual_confirm = any([c.configs["need_manual_confirm"] for c in self.ticket_configs])
        return need_manual_confirm

    @property
    def need_timer(self):
        """是否需要定时节点，默认为False，只有在特殊单据下需要这个节点"""
        return False

    @property
    def need_resource_pool(self):
        """是否存在资源池接入"""
        return self.ticket.details.get("ip_source") == IpSource.RESOURCE_POOL

    def custom_ticket_flows(self):
        return []

    def init_ticket_flows(self):
        """
        自定义流程，默认流程是：
        单据审批(可选, 默认有) --> 人工确认(可选, 默认无) --> 资源申请(由单据参数判断) ---> inner节点
        如果有特殊的flow需求，可在custom_ticket_flows中定制，会替换掉inner节点为custom流程
        对于复杂流程，可以直接覆写init_ticket_flows
        """
        flows = []

        # 判断并添加审批节点
        if self.need_itsm:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.BK_ITSM.value,
                    details=self.itsm_flow_builder(self.ticket).get_params(),
                    flow_alias=_("单据审批"),
                )
            )

        # 判断并添加定时节点
        if self.need_timer:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.TIMER.value,
                    flow_alias=_("定时执行"),
                )
            )

        # 判断并添加人工确认节点
        if self.need_manual_confirm:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.PAUSE.value,
                    details=self.pause_node_builder(self.ticket).get_params(),
                    flow_alias=_("人工确认"),
                ),
            )

        # 判断并添加资源申请节点
        if self.need_resource_pool:
            if not self.resource_apply_builder:
                flow_type, resource_builder = FlowType.RESOURCE_BATCH_APPLY, self.resource_batch_apply_builder
            else:
                flow_type, resource_builder = FlowType.RESOURCE_APPLY, self.resource_apply_builder
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=flow_type,
                    details=resource_builder(self.ticket).get_params(),
                    flow_alias=_("资源申请"),
                ),
            )

        # 若单据有特殊的自定义流程，则优先使用。否则使用默认的 inner_param_builder
        custom_ticket_flows = self.custom_ticket_flows()
        if custom_ticket_flows:
            flows.extend(custom_ticket_flows)
        else:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=self.inner_flow_builder(self.ticket).get_params(),
                    flow_alias=self.inner_flow_name,
                    retry_type=self.retry_type,
                )
            )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    def transform_alarm_to_ticket_details(self):
        """把监控时间转换为单据详情"""
        pass

    def patch_ticket_detail(self):
        """自定义补充单据详情，留给子类实现"""
        pass

    def alarm_callback_to_ticket_detail(self):
        """告警回调转化为单据详情"""
        pass

    @classmethod
    def _add_itsm_pause_describe(cls, flow_desc, flow_config_map):
        if flow_config_map[cls.ticket_type]["need_itsm"]:
            flow_desc.append(FlowType.get_choice_label(FlowType.BK_ITSM))
        if flow_config_map[cls.ticket_type]["need_manual_confirm"]:
            flow_desc.append(FlowType.get_choice_label(FlowType.PAUSE))
        return flow_desc

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        """
        @param flow_config_map: 单据类型与配置的映射
        单据构造类的默认流程描述，固定为：
        单据审批(可选, 默认有) --> 人工确认(可选, 默认有) --> 资源申请(由单据参数判断) ---> inner节点
        如果子类覆写了custom_ticket_flows/init_ticket_flows，则同时需要覆写该方法
        """
        need_resource = (cls.resource_apply_builder or cls.resource_batch_apply_builder) is not None
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        if need_resource:
            flow_desc.append(FlowType.get_choice_label(FlowType.RESOURCE_APPLY))
        if cls.inner_flow_name:
            flow_desc.append(cls.inner_flow_name)

        return flow_desc


class BuilderFactory:
    # 单据的注册器类集合
    registry = {}
    # 部署类单据集合
    apply_ticket_type = []
    # 回收类单据集合
    recycle_ticket_type = []
    # 敏感类单据集合
    sensitive_ticket_type = []
    # 单据与集群状态的映射
    ticket_type__cluster_phase = {}
    # 单据和权限动作/资源类型的映射
    ticket_type__iam_action = {}

    @classmethod
    def register(cls, ticket_type: str, **kwargs) -> Callable:
        """
        将单据构造类注册到注册器中
        @param ticket_type: 单据类型
        @param kwargs: 单据注册的额外信息，主要是将单据归为不同的集合中，目前有这几种类型
        1. is_apply: bool ---- 表示单据是否是部署类单据(类似集群的部署，扩容，替换等)
        2. is_recycle: bool ---- 表示单据是否是下架类单据(类似集群的下架，缩容，替换等)
        3. phase: ClusterPhase ---- 表示单据与集群状态的映射
        4. action: ActionMeta ---- 表示单据与权限动作的映射
        5. is_sensitive: bool --- 是否为敏感类单据（有特殊鉴权）
        """

        def inner_wrapper(wrapped_class: TicketFlowBuilder) -> TicketFlowBuilder:
            wrapped_class.ticket_type = ticket_type
            # 若未自定义 flow 流程名称，则使用 单据类型
            if not getattr(wrapped_class, "inner_flow_name", ""):
                setattr(wrapped_class, "inner_flow_name", TicketType.get_choice_label(ticket_type))

            if ticket_type in cls.registry:
                logger.warning(f"Builder [{ticket_type}] already exists. Will replace it")
            cls.registry[ticket_type] = wrapped_class

            if kwargs.get("is_apply") and kwargs.get("is_apply") not in cls.apply_ticket_type:
                cls.apply_ticket_type.append(ticket_type)
            if kwargs.get("is_recycle") and kwargs.get("is_recycle") not in cls.recycle_ticket_type:
                cls.recycle_ticket_type.append(ticket_type)
            if kwargs.get("is_sensitive") and kwargs.get("is_sensitive") not in cls.sensitive_ticket_type:
                cls.sensitive_ticket_type.append(ticket_type)
            if kwargs.get("phase"):
                cls.ticket_type__cluster_phase[ticket_type] = kwargs["phase"]
            if hasattr(ActionEnum, ticket_type) or kwargs.get("iam"):
                # 单据类型和权限动作默认一一对应，如果是特殊指定的则通过iam参数传递
                cls.ticket_type__iam_action[ticket_type] = getattr(ActionEnum, ticket_type, None) or kwargs.get("iam")

            return wrapped_class

        return inner_wrapper

    @classmethod
    def get_builder_cls(cls, ticket_type: str):
        """获取构造器类"""
        if ticket_type not in cls.registry:
            logger.warning(f"Ticket Type: [{ticket_type}] does not exist in the registry")
            raise NotImplementedError

        return cls.registry[ticket_type]

    @classmethod
    def get_serializer(cls, ticket_type: str):
        try:
            return cls.get_builder_cls(ticket_type).serializer()
        except NotImplementedError:
            return serializers.Serializer()

    @classmethod
    def create_builder(cls, ticket: Ticket):
        """创建构造器实例"""
        builder_cls = cls.get_builder_cls(ticket.ticket_type)
        return builder_cls(ticket)


def register_all_builders():
    re_import_modules(path=os.path.dirname(__file__), module_path="backend.ticket.builders")
