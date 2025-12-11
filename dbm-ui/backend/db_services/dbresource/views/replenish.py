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

from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbresource.constants import SWAGGER_TAG
from backend.db_services.dbresource.filters import ReplenishRecordFilter
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.db_services.dbresource.models import ResourceReplenishRecord
from backend.db_services.dbresource.serializers import (  # CheckFaultHostsSerializer,
    CreateResourceReplenishSerializer,
    ListTicketApplyCountSerializer,
    ReplenishRecordSerializer,
)
from backend.exceptions import ApiRequestError
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


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
        return Response(ResourceHandler.create_replenish(username, data["bk_biz_id"], data["infos"]))

    @common_swagger_auto_schema(
        operation_summary=_("获取资源池单据申请交付信息"),
        query_serializer=ListTicketApplyCountSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], serializer_class=ListTicketApplyCountSerializer, filter_class=None)
    def list_ticket_apply_info(self, request):
        data = self.params_validate(self.get_serializer_class())
        # 获取单据和关联的流程信息
        tickets = Ticket.objects.prefetch_related("flows").filter(
            id__in=data["ticket_ids"].split(","), ticket_type=TicketType.RESOURCE_HCM_REPLENISH.value
        )
        # 获取补货记录和单据之间的关系
        replenish_records = ResourceReplenishRecord.objects.all().values("ticket_ids", "id")
        ticket_replenish_map = {tid: record["id"] for record in replenish_records for tid in record["ticket_ids"]}

        ticket_apply_count_map = {}
        for ticket in tickets:
            inner_flow = list(ticket.flows.all())[-1]
            # 申请数量从需求信息获取，交付数量从流程摘要获取
            delivery_count = len(inner_flow.output_data[0]["values"]) if inner_flow.output_data else 0
            ticket_apply_count_map[ticket.id] = {
                "apply_count": ticket.details["count"],
                "delivery_count": delivery_count,
                "details": ticket.details,
                "record_id": ticket_replenish_map.get(ticket.id, ""),
            }

        return Response(ticket_apply_count_map)
