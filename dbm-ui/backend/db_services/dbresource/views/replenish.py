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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_services.dbresource.constants import SWAGGER_TAG
from backend.db_services.dbresource.filters import ReplenishRecordFilter
from backend.db_services.dbresource.handlers import ResourceHandler, async_create_replenish
from backend.db_services.dbresource.models import ResourceReplenishRecord
from backend.db_services.dbresource.serializers import (  # CheckFaultHostsSerializer,
    CreateResourceReplenishSerializer,
    ExportReplenishTicketSerializer,
    ListTicketApplyCountSerializer,
    ReplenishRecordSerializer,
)
from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.exceptions import ApiRequestError
from backend.flow.consts import StateType
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from backend.ticket.constants import TicketStatus
from backend.utils.excel import ExcelHandler


class DBReplenishViewSet(viewsets.AuditedModelViewSet):
    """DB资源补货视图集"""

    action_permission_map = {
        ("create_resource_replenish",): [ResourceActionPermission([ActionEnum.RESOURCE_POLL_MANAGE])],
    }
    default_permission_class = [ResourceActionPermission([ActionEnum.RESOURCE_MANAGE])]

    queryset = ResourceReplenishRecord.objects.all().order_by("-create_at")
    serializer_class = ReplenishRecordSerializer
    filter_class = ReplenishRecordFilter
    pagination_class = AuditedLimitOffsetPagination

    @common_swagger_auto_schema(
        operation_summary=_("查询资源补货记录"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("查询正在运行的补货记录"),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], serializer_class=Serializer, filter_class=None, pagination_class=None)
    def get_running_replenish_record(self, request):
        return Response(ResourceReplenishRecord.is_latest_running())

    @common_swagger_auto_schema(
        operation_summary=_("海磊资源池主机补货"),
        request_body=CreateResourceReplenishSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=CreateResourceReplenishSerializer)
    def create_resource_replenish(self, request):
        data = self.params_validate(self.get_serializer_class())
        username = request.user.username

        if ResourceReplenishRecord.is_latest_running():
            raise ApiRequestError(_("有正在运行的补货记录，不允许提交"))
        if not data["infos"]:
            raise ValueError(_("不存在任何补货信息"))

        # 先创建空记录用于防重入和状态轮询，异步任务完成后更新 ticket_ids 和 details
        record = ResourceReplenishRecord.objects.create(creator=username, ticket_ids=[], details={})
        # 一次提单可能很多，所以异步发起
        kwargs = {"username": username, "bk_biz_id": data["bk_biz_id"], "infos": data["infos"], "record_id": record.id}
        async_create_replenish.apply_async(kwargs=kwargs)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("获取资源池单据申请交付信息"),
        query_serializer=ListTicketApplyCountSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], serializer_class=ListTicketApplyCountSerializer, filter_class=None)
    def list_ticket_apply_info(self, request):
        data = self.params_validate(self.get_serializer_class())
        ticket_ids = [int(ticket_id) for ticket_id in data["ticket_ids"].split(",") if ticket_id.strip()]
        ticket_apply_count_map = ResourceHandler.get_replenish_ticket_apply_info_map(ticket_ids)
        return Response(ticket_apply_count_map)

    @common_swagger_auto_schema(
        operation_summary=_("导出补货单据Excel"),
        request_body=ExportReplenishTicketSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=ExportReplenishTicketSerializer, filter_class=None)
    def export_replenish_tickets(self, request):
        data = self.params_validate(self.get_serializer_class())
        ticket_ids = data.get("ticket_ids", [])
        records = ResourceReplenishRecord.objects.filter(id__in=data.get("replenish_record_ids", []))
        ticket_ids.extend(itertools.chain(*list(records.values_list("ticket_ids", flat=True))))

        if not ticket_ids:
            raise ValueError(_("不存在需要导出的补货单据"))

        ticket_apply_count_map = ResourceHandler.get_replenish_ticket_apply_info_map(ticket_ids, runtime_info=True)

        rows = []
        error_log_map = {}

        def _query_ticket_error_log(ticket_id):
            info = ticket_apply_count_map.get(ticket_id, {})
            ticket = info.get("ticket")
            inner_flow = info.get("inner_flow")
            # 仅失败单据需要拉取节点错误日志
            if not ticket or not inner_flow or ticket.status != TicketStatus.FAILED:
                return ticket_id, ""

            taskflow_handler = TaskFlowHandler(root_id=inner_flow.flow_obj_id)
            failed_nodes = taskflow_handler.get_specific_nodes(status=StateType.FAILED)
            # 流程树上没有失败节点时，回退使用流程级错误信息
            if not failed_nodes:
                return ticket_id, inner_flow.err_msg or ""

            # failed_nodes 只会有一个错误节点
            node_id = failed_nodes[0]["node_id"]
            version_id = failed_nodes[0]["version_id"]
            logs = taskflow_handler.get_version_logs(node_id, version_id)
            err_log = "\n".join([log.get("message", "") for log in logs])
            # 节点日志为空时，回退到流程错误信息兜底
            if not err_log:
                err_log = inner_flow.err_msg or ""
            return ticket_id, err_log

        # 并发粒度按 ticket 维度，避免逐单据串行拉日志导致导出耗时过长
        with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as executor:
            for ticket_id, error_log in executor.map(_query_ticket_error_log, ticket_ids):
                error_log_map[ticket_id] = error_log

        for ticket_id in ticket_ids:
            if ticket_id not in ticket_apply_count_map:
                continue
            info = ticket_apply_count_map.get(ticket_id, {})
            ticket = info["ticket"]
            details = info["details"]
            spec = details["spec"]
            db_type = details["db_type"]
            spec_type = spec["spec_machine_type"]
            error_log = error_log_map.get(ticket_id, "")

            rows.append(
                {
                    "ticket_id": ticket_id,
                    "status": str(TicketStatus.get_choice_label(ticket.status)) if ticket else "",
                    "db_type": str(DBType.get_choice_label(db_type)) if db_type else "",
                    "spec_type": str(SpecMachineType.get_choice_label(spec_type)) if spec_type else "",
                    "spec": spec.get("spec_name", details.get("spec_id", "")),
                    "city": details.get("city", ""),
                    "subzone": details.get("subzone", ""),
                    "os_name": details.get("os_name", ""),
                    "apply_count": info.get("apply_count", 0),
                    "delivery_count": info.get("delivery_count", 0),
                    "error_log": error_log,
                }
            )

        headers = [
            {"id": "ticket_id", "name": _("单号")},
            {"id": "status", "name": _("状态")},
            {"id": "db_type", "name": _("DB 类型")},
            {"id": "spec_type", "name": _("规格类型")},
            {"id": "spec", "name": _("规格")},
            {"id": "city", "name": _("地域")},
            {"id": "subzone", "name": _("园区")},
            {"id": "os_name", "name": _("操作系统")},
            {"id": "apply_count", "name": _("申请数量")},
            {"id": "delivery_count", "name": _("已交付")},
            {"id": "error_log", "name": _("错误日志")},
        ]
        wb = ExcelHandler.serialize(rows, headers=headers, match_header=True, sheet_name=_("补货单据导出"))
        filename = f"replenish_tickets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return ExcelHandler.response(wb, filename)
