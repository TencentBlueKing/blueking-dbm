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

from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_dirty.constants import SWAGGER_TAG
from backend.db_dirty.filters import DirtyMachinePoolFilter, MachineEventFilter
from backend.db_dirty.handlers import DBDirtyMachineHandler
from backend.db_dirty.models import DirtyMachine, MachineEvent
from backend.db_dirty.serializers import (
    ListMachineEventResponseSerializer,
    ListMachineEventSerializer,
    ListMachinePoolResponseSerializer,
    ListMachinePoolSerializer,
    TransferDirtyMachineSerializer,
)
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission


class DBDirtyMachineViewSet(viewsets.SystemViewSet):
    pagination_class = AuditedLimitOffsetPagination
    filter_class = None

    action_permission_map = {("query_operation_list",): []}
    default_permission_class = [ResourceActionPermission([ActionEnum.DIRTY_POLL_MANAGE])]

    @common_swagger_auto_schema(
        operation_summary=_("将主机转移至待回收/故障池模块"),
        request_body=TransferDirtyMachineSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=TransferDirtyMachineSerializer)
    def transfer_hosts_to_pool(self, request):
        data = self.params_validate(self.get_serializer_class())
        DBDirtyMachineHandler.transfer_hosts_to_pool(operator=request.user.username, **data)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("机器事件列表"),
        responses={status.HTTP_200_OK: ListMachineEventResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], filter_class=MachineEventFilter, queryset=MachineEvent.objects.all())
    def list_machine_events(self, request):
        events_qs = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        events_data = ListMachineEventSerializer(events_qs, many=True).data
        return self.paginator.get_paginated_response(data=events_data)

    @common_swagger_auto_schema(
        operation_summary=_("主机池查询"),
        responses={status.HTTP_200_OK: ListMachinePoolResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], filter_class=DirtyMachinePoolFilter, queryset=DirtyMachine.objects.all())
    def query_machine_pool(self, request):
        machine_qs = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        # 查询主机池主机信息
        machine_data = ListMachinePoolSerializer(machine_qs, many=True).data
        # 补充主机agent状态
        ResourceQueryHelper.fill_agent_status(machine_data, fill_key="agent_status")
        return self.paginator.get_paginated_response(data=machine_data)
