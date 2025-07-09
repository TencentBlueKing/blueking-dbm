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

from django.utils.translation import ugettext as _
from rest_framework.permissions import BasePermission

from backend.configuration.models import DBAdministrator
from backend.db_meta.models import ExtraProcessInstance
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.drf_perm.base import (
    BizDBTypeResourceActionPermission,
    IAMPermission,
    MoreResourceActionPermission,
    RejectPermission,
    ResourceActionPermission,
)
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.constants import TicketType
from backend.ticket.exceptions import ApprovalWrongOperatorException
from backend.ticket.models import Ticket, TicketFlowsConfig
from backend.utils.basic import get_target_items_from_details

logger = logging.getLogger("root")


class CreateTicketOneResourcePermission(ResourceActionPermission):
    """
    创建单据相关动作鉴权 -- 关联一个动作
    """

    def __init__(self, ticket_type: TicketType, batch: bool = False) -> None:
        self.ticket_type = ticket_type
        self.batch = batch
        action = BuilderFactory.ticket_type__iam_action.get(ticket_type)
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
        else:
            instance_ids_getter = self.instance_cluster_ids_getter

        super().__init__(actions, resource_meta, instance_ids_getter=instance_ids_getter)

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
        action = BuilderFactory.ticket_type__iam_action.get(ticket_type)
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

        # 处理特殊授权单据
        if self.batch:
            if request.data["tickets"][0]["ticket_type"] in [
                TicketType.SQLSERVER_AUTHORIZE_RULES,
                TicketType.MONGODB_AUTHORIZE_RULES,
            ]:
                authorize_data_list = authorize_data_list[0]
        elif request.data["ticket_type"] in [TicketType.SQLSERVER_AUTHORIZE_RULES, TicketType.MONGODB_AUTHORIZE_RULES]:
            authorize_data_list = authorize_data_list[0]

        for data in authorize_data_list:
            authorize_resource_tuples.extend(list(itertools.product([data["account_id"]], data["cluster_ids"])))
        return authorize_resource_tuples

    def openarea_instance_ids_getters(self, request, view):
        openarea_details = request.data["tickets"] if self.batch else [request.data]
        return [(details["details"]["config_id"], details["details"]["cluster_id"]) for details in openarea_details]


def create_ticket_permission(ticket_type: TicketType, batch: bool = False) -> List[IAMPermission]:
    action = BuilderFactory.ticket_type__iam_action.get(ticket_type)
    if not action:
        # 对于未注册到iam的单据动作，默认只开放给superuser
        logger.warning(_("单据动作ID:{} 不存在").format(action))
        return [RejectPermission()]
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

    if action in ["update_ticket_flow_config", "create_ticket_flow_config"]:
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
