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
import logging
from typing import List

from bk_audit.log.models import AuditContext
from celery import shared_task
from django.utils.translation import gettext as _
from rest_framework.permissions import BasePermission

from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, ExtraProcessInstance, Machine, ProxyInstance, StorageInstance
from backend.exceptions import AppBaseException
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ClusterResourceMeta, ResourceEnum
from backend.iam_app.handlers.drf_perm.base import (
    BizDBTypeResourceActionPermission,
    CommonInstance,
    IAMPermission,
    MoreResourceActionPermission,
    RejectPermission,
    ResourceActionPermission,
    bk_audit_client,
)
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.exceptions import ApprovalWrongOperatorException
from backend.ticket.models import Ticket, TicketFlowsConfig
from backend.utils.basic import get_target_items_from_details

logger = logging.getLogger("root")

audit_ticket_status = [TicketStatus.RUNNING, TicketStatus.SUCCEEDED, TicketStatus.FAILED, TicketStatus.TERMINATED]


class CreateTicketOneResourcePermission(ResourceActionPermission):
    """
    创建单据相关动作鉴权 -- 关联一个动作
    """

    def __init__(self, ticket_type: TicketType, batch: bool = False) -> None:
        self.ticket_type = ticket_type
        self.batch = batch
        action = BuilderFactory.get_ticket_iam_action(ticket_type)
        actions = [action] if action else []
        # 只考虑关联一种资源
        resource_meta = action.related_resource_types[0] if action else None

        # TODO: 暂时屏蔽对influxdb的鉴权
        # if resource_meta == ResourceEnum.INFLUXDB:
        #     # 对于influxdb没有集群概念，特殊考虑
        #     instance_ids_getter = self.instance_influxdb_ids_getter
        if resource_meta == ResourceEnum.BUSINESS:
            instance_ids_getter = self.instance_biz_ids_getter
        elif resource_meta in [ResourceEnum.TENDBCLUSTER_ACCOUNT, ResourceEnum.MYSQL_ACCOUNT]:
            instance_ids_getter = self.instance_account_ids_getter
        elif action in ActionEnum.get_match_actions("tbinlogdumper"):
            # 对应dumper相关操作，需要根据dumper的实例ID反查出相关的集群
            instance_ids_getter = self.instance_dumper_cluster_ids_getter
        # DB实例权限克隆执行, 查询源客户端IP已在哪些集群
        elif ticket_type in [TicketType.MYSQL_INSTANCE_CLONE_RULES, TicketType.TENDBCLUSTER_INSTANCE_CLONE_RULES]:
            instance_ids_getter = self.clonepriv_instance_cluster_ids_getter
        else:
            instance_ids_getter = self.instance_cluster_ids_getter

        super().__init__(actions, resource_meta, instance_ids_getter=instance_ids_getter)

    def clonepriv_instance_cluster_ids_getter(self, request, view):
        details = request.data.get("details") or request.data
        target_ips = [clone_data["target"] for clone_data in details.get("clone_data_list", [])]
        ips = [ip_port.split(":")[0] for ip_port in target_ips if ":" in ip_port]
        machines = Machine.objects.filter(ip__in=ips)
        ip_port_cluster_map = {}
        proxy_instances = (
            ProxyInstance.objects.filter(machine__in=machines).select_related("machine").prefetch_related("cluster")
        )
        storage_instances = (
            StorageInstance.objects.filter(machine__in=machines).select_related("machine").prefetch_related("cluster")
        )
        for pi in proxy_instances:
            ip = pi.machine.ip
            for cluster in pi.cluster.all():
                ip_port_cluster_map[f"{ip}:{pi.port}"] = cluster.id
                if pi.admin_port:
                    ip_port_cluster_map[f"{ip}:{pi.admin_port}"] = cluster.id
        for si in storage_instances:
            ip = si.machine.ip
            for cluster in si.cluster.all():
                ip_port_cluster_map[f"{ip}:{si.port}"] = cluster.id
        cluster_ids = []
        for target_ip in target_ips:
            if not ip_port_cluster_map.get(target_ip):
                raise AppBaseException(_("目标ip{}没找到对应的集群id").format(target_ip))
            cluster_ids.append(ip_port_cluster_map[target_ip])
        return cluster_ids

    def instance_biz_ids_getter(self, request, view):
        if self.batch:
            return [data["bk_biz_id"] for data in request.data["tickets"]]
        return [request.data["bk_biz_id"]]

    def instance_account_ids_getter(self, request, view):
        if self.batch:
            return [data["details"]["account_id"] for data in request.data["tickets"]]
        return [request.data["details"]["account_id"]]

    @staticmethod
    def instance_cluster_ids_getter(request, view):
        # 集群ID从details解析，如果没有detail(比如sql模拟执行)，则直接取request.data
        details = request.data.get("details") or request.data
        cluster_ids = fetch_cluster_ids(details)
        # 排除非int型的cluster id(比如redis的构造实例恢复集群使用ip表示的)
        cluster_ids = [int(id) for id in cluster_ids if isinstance(id, int) or (isinstance(id, str) and id.isdigit())]
        return cluster_ids

    @staticmethod
    def instance_influxdb_ids_getter(request, view):
        details = request.data.get("details") or request.data
        return get_target_items_from_details(details, match_keys=["instance_id", "instance_ids"])

    def instance_dumper_cluster_ids_getter(self, request, view):
        cluster_ids = []
        tickets = request.data.get("tickets", []) if self.batch else [request.data]

        for ticket in tickets:
            ticket_type = ticket.get("ticket_type")
            ticket_details = ticket.get("details", {})

            if ticket_type == TicketType.TBINLOGDUMPER_INSTALL:
                cluster_ids.extend(fetch_cluster_ids(ticket_details))
            else:
                dumper_instance_ids = ticket_details.get("dumper_instance_ids", [])
                if dumper_instance_ids:
                    cluster_ids.extend(
                        ExtraProcessInstance.objects.filter(id__in=dumper_instance_ids).values_list(
                            "cluster_id", flat=True
                        )
                    )
        return cluster_ids


class CreateTicketMoreResourcePermission(MoreResourceActionPermission):
    """
    创建单据相关动作鉴权 -- 关联多个动作
    由于这种相关的单据类型很少，且资源独立，所以请根据单据类型来分别写instance_ids_getter函数
    """

    def __init__(self, ticket_type: TicketType, batch: bool = False) -> None:
        self.ticket_type = ticket_type
        self.batch = batch
        action = BuilderFactory.get_ticket_iam_action(ticket_type)
        resource_metes = action.related_resource_types
        # 根据单据类型来决定资源获取方式
        instance_ids_getters = None

        # 授权 - 关联：账号 + 集群
        if ticket_type in [
            TicketType.MYSQL_AUTHORIZE_RULES,
            TicketType.TENDBCLUSTER_AUTHORIZE_RULES,
            TicketType.SQLSERVER_AUTHORIZE_RULES,
            TicketType.MONGODB_AUTHORIZE_RULES,
        ]:
            instance_ids_getters = self.authorize_instance_ids_getters
        # 授权 - 关联：开区模板 + 集群
        elif ticket_type in [TicketType.MYSQL_OPEN_AREA, TicketType.TENDBCLUSTER_OPEN_AREA]:
            instance_ids_getters = self.openarea_instance_ids_getters

        super().__init__(actions=[action], resource_metes=resource_metes, instance_ids_getters=instance_ids_getters)

    def authorize_instance_ids_getters(self, request, view):
        def process_authorize_data(details):
            # 统一处理不同来源的 authorize_data
            authorize_data = details.get("authorize_data") or details.get("authorize_data_list")
            if isinstance(authorize_data, list):
                authorize_data_list.extend(authorize_data)
            else:
                authorize_data_list.append(authorize_data)

        authorize_resource_tuples = []
        authorize_data_list = []
        if self.batch:
            # 处理批量授权单据
            for data in request.data["tickets"]:
                details = data.get("details", {})
                process_authorize_data(details)
        else:
            # 处理单个授权单据
            details = request.data.get("details", {})
            process_authorize_data(details)

        for data in authorize_data_list:
            authorize_resource_tuples.extend(list(itertools.product([data["account_id"]], data["cluster_ids"])))
        return authorize_resource_tuples

    def openarea_instance_ids_getters(self, request, view):
        openarea_details = request.data["tickets"] if self.batch else [request.data]
        return [(details["details"]["config_id"], details["details"]["cluster_id"]) for details in openarea_details]


class CreateTicketMysqlOrTendbclusterPermission(IAMPermission):
    """同一动作同时关联 MYSQL 与 TENDBCLUSTER 时，按集群类型分别鉴权（不是 MoreResource 的 AND 元组）。"""

    MYSQL_CLUSTER_TYPES = {ClusterType.TenDBSingle.value, ClusterType.TenDBHA.value}
    TENDBCLUSTER_TYPES = {ClusterType.TenDBCluster.value}

    def __init__(self, ticket_type: TicketType, batch: bool = False) -> None:
        self.ticket_type = ticket_type
        self.batch = batch
        action = BuilderFactory.ticket_type__iam_action.get(ticket_type)
        super().__init__(actions=[action] if action else [])

    def _cluster_ids(self, request) -> List[int]:
        tickets = request.data.get("tickets", []) if self.batch else [request.data]
        cluster_ids: List[int] = []
        for ticket in tickets:
            details = ticket.get("details") or ticket
            cluster_ids.extend(fetch_cluster_ids(details))
        return [int(cid) for cid in cluster_ids if isinstance(cid, int) or (isinstance(cid, str) and cid.isdigit())]

    def has_permission(self, request, view):
        if not self.actions:
            return True
        action = self.actions[0]
        cluster_ids = self._cluster_ids(request)
        if not cluster_ids:
            return True
        type_map = dict(Cluster.objects.filter(id__in=cluster_ids).values_list("id", "cluster_type"))
        mysql_ids = [cid for cid in cluster_ids if type_map.get(cid) in self.MYSQL_CLUSTER_TYPES]
        tendb_ids = [cid for cid in cluster_ids if type_map.get(cid) in self.TENDBCLUSTER_TYPES]
        if mysql_ids:
            perm = ResourceActionPermission([action], ResourceEnum.MYSQL, instance_ids_getter=lambda _r, _v: mysql_ids)
            if not perm.has_permission(request, view):
                return False
        if tendb_ids:
            perm = ResourceActionPermission(
                [action], ResourceEnum.TENDBCLUSTER, instance_ids_getter=lambda _r, _v: tendb_ids
            )
            if not perm.has_permission(request, view):
                return False
        return True

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


def create_ticket_permission(ticket_type: TicketType, batch: bool = False) -> List[IAMPermission]:
    action = BuilderFactory.get_ticket_iam_action(ticket_type)
    if not action:
        # 对于未注册到iam的单据动作，默认只开放给superuser
        logger.warning(_("单据动作ID:{} 不存在").format(action))
        return [RejectPermission()]
    if ticket_type == TicketType.MYSQL_RENAME_MIGRATE:
        return [CreateTicketMysqlOrTendbclusterPermission(ticket_type=ticket_type, batch=batch)]
    if len(action.related_resource_types) <= 1:
        return [CreateTicketOneResourcePermission(ticket_type=ticket_type, batch=batch)]
    else:
        return [CreateTicketMoreResourcePermission(ticket_type=ticket_type, batch=batch)]


class BatchApprovalPermission(BasePermission):
    def has_permission(self, request, view):
        ticket_ids = request.data.get("ticket_ids")
        user = request.user.username
        tickets = Ticket.objects.filter(id__in=ticket_ids).values("bk_biz_id", "ticket_type", "group")
        # 缓存approvers字典
        approver_cache = {}

        for ticket in tickets:
            # 获取所有有权限的审批人
            db_type = ticket["group"]
            cache_key = (ticket["bk_biz_id"], db_type)
            # 缓存没有命中，则查询并存入缓存
            if cache_key not in approver_cache:
                approver_cache[cache_key] = DBAdministrator.get_biz_db_type_admins(ticket["bk_biz_id"], db_type)
            if user not in approver_cache[cache_key]:
                raise ApprovalWrongOperatorException(
                    _("{}不在处理人:{}中, 无权进行审批操作").format(user, approver_cache[cache_key])
                )

        return True


def ticket_flows_config_permission(action, request):
    dbtype_cov = TicketType.get_db_type_by_ticket
    permission: IAMPermission = None

    if action in ["save_ticket_flow_config", "update_ticket_flow_config", "create_ticket_flow_config"]:
        if request.data.get("bk_biz_id"):
            permission = BizDBTypeResourceActionPermission(
                [ActionEnum.BIZ_TICKET_CONFIG_SET],
                instance_biz_getter=lambda req, view: [req.data["bk_biz_id"]],
                instance_dbtype_getter=lambda req, view: list(set([dbtype_cov(d) for d in req.data["ticket_types"]])),
            )
        else:
            permission = ResourceActionPermission(
                [ActionEnum.GLOBAL_TICKET_CONFIG_SET],
                ResourceEnum.DBTYPE,
                instance_ids_getter=lambda req, view: [req.data["bk_biz_id"]],
            )
    elif action == "delete_ticket_flow_config":
        configs = list(TicketFlowsConfig.objects.filter(id__in=request.data["config_ids"]))
        groups, bk_biz_ids = [c.group for c in configs], [c.bk_biz_id for c in configs]
        # 只允许一个业务下的一种db类型
        if len(set(groups)) > 1 or len(set(bk_biz_ids)) > 1:
            permission = RejectPermission()
        else:
            permission = BizDBTypeResourceActionPermission(
                [ActionEnum.BIZ_TICKET_CONFIG_SET],
                instance_biz_getter=lambda req, view: bk_biz_ids,
                instance_dbtype_getter=lambda req, view: groups,
            )

    return [permission]


@shared_task
def add_ticket_audit_event(ticket_id):
    """
    添加单据审计事件
    目前只有在任务开始执行和任务执行失败/终止的时候才上报事件
    """
    ticket = Ticket.objects.get(id=ticket_id)

    # 非审计状态，忽略
    if ticket.status not in audit_ticket_status:
        return

    # 无集群ID，忽略
    cluster_ids = fetch_cluster_ids(ticket.details)
    if not cluster_ids:
        return

    # 获取单据执行相关的iam资源
    action = BuilderFactory.get_ticket_iam_action(ticket.ticket_type)
    if not action:
        return

    # 如果资源不为集群类型，则忽略
    resource_meta = action.related_resource_types[0] if action.related_resource_types else None
    if not issubclass(resource_meta.__class__, ClusterResourceMeta):
        return

    resources = resource_meta.batch_create_instances(cluster_ids)
    # 按照资源上报事件
    event_data = {
        "username": ticket.creator,
        "bk_biz_id": ticket.bk_biz_id,
        "ticket_type": ticket.ticket_type,
        "status": ticket.status,
        "ticket_id": ticket.id,
    }
    for resource in resources:
        try:
            bk_audit_client.add_event(
                action=action,
                resource_type=resource,
                audit_context=AuditContext(**event_data),
                instance=CommonInstance(resource.attribute),
                extend_data=event_data,
            )
        except TypeError as e:
            logger.error("bk audit add event error...%s", e)
