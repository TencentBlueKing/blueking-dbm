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
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.hcm.client import HCMApi
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models.system import SystemSettings
from backend.db_dirty.constants import SWAGGER_TAG, MachineEventType
from backend.db_dirty.filters import DirtyMachinePoolFilter, MachineEventFilter
from backend.db_dirty.handlers import DBDirtyMachineHandler
from backend.db_dirty.models import DirtyMachine, MachineEvent
from backend.db_dirty.serializers import (
    CheckHostIsDissolvedSerializer,
    GetHostCurrentEvents,
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

    action_permission_map = {
        (
            "list_machine_events",
            "get_host_current_events",
            "query_machine_pool",
            "check_host_is_dissolved",
            "check_host_has_uwork",
            "get_dissolved_uwork_info",
        ): [ResourceActionPermission([ActionEnum.RESOURCE_MANAGE])],
        ("transfer_hosts_to_pool",): [ResourceActionPermission([ActionEnum.RESOURCE_POLL_MANAGE])],
    }
    default_permission_class = [ResourceActionPermission([ActionEnum.RESOURCE_POLL_MANAGE])]

    @common_swagger_auto_schema(
        operation_summary=_("将主机转移至待回收/故障池模块"),
        request_body=TransferDirtyMachineSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=TransferDirtyMachineSerializer)
    def transfer_hosts_to_pool(self, request):
        data = self.params_validate(self.get_serializer_class())
        return Response(DBDirtyMachineHandler.transfer_hosts_to_pool(operator=request.user.username, **data))

    @common_swagger_auto_schema(
        operation_summary=_("查询主机是否为待裁撤"),
        request_body=CheckHostIsDissolvedSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=CheckHostIsDissolvedSerializer)
    def check_host_is_dissolved(self, request):
        data = self.params_validate(self.get_serializer_class())
        return Response(HCMApi.check_host_is_dissolved(data["bk_host_ids"]))

    @common_swagger_auto_schema(
        operation_summary=_("查询主机是否有故障"),
        request_body=CheckHostIsDissolvedSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=CheckHostIsDissolvedSerializer)
    def check_host_has_uwork(self, request):
        data = self.params_validate(self.get_serializer_class())
        has_uwork_hosts_map = HCMApi.check_host_has_uwork(data["bk_host_ids"])
        return Response(list(has_uwork_hosts_map.values()))

    @common_swagger_auto_schema(
        operation_summary=_("获取待裁撤和故障主机开关信息"),
        responses={status.HTTP_200_OK: ListMachineEventResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"])
    def get_dissolved_uwork_info(self, request):
        dissolved_switch = SystemSettings.get_setting_value(
            key=SystemSettingsEnum.HOST_DISSOLVED_SWITCH, default=False
        )
        host_to_fault_switch = SystemSettings.get_setting_value(
            key=SystemSettingsEnum.HOST_TO_FAULT_SWITCH, default=False
        )
        return Response(
            {
                SystemSettingsEnum.HOST_DISSOLVED_SWITCH: dissolved_switch,
                SystemSettingsEnum.HOST_TO_FAULT_SWITCH: host_to_fault_switch,
            }
        )

    @common_swagger_auto_schema(
        operation_summary=_("机器事件列表"),
        responses={status.HTTP_200_OK: ListMachineEventResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["GET"],
        filter_class=MachineEventFilter,
        queryset=MachineEvent.objects.all().order_by("-update_at"),
    )
    def list_machine_events(self, request):
        events_qs = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        events_data = ListMachineEventSerializer(events_qs, many=True).data
        return self.paginator.get_paginated_response(data=events_data)

    @common_swagger_auto_schema(
        operation_summary=_("获取主机当前周期的事件"),
        query_serializer=GetHostCurrentEvents(),
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False, methods=["GET"], serializer_class=GetHostCurrentEvents, filter_class=None, pagination_class=None
    )
    def get_host_current_events(self, request):
        host_id = self.params_validate(self.get_serializer_class())["bk_host_id"]
        event_qs = MachineEvent.objects.filter(bk_host_id=host_id).order_by("-create_at")
        st = next((i for i, d in enumerate(event_qs) if d.event == MachineEventType.ImportResource), event_qs.count())
        events = ListMachineEventSerializer(event_qs[: st + 1], many=True).data
        return Response(events)

    @common_swagger_auto_schema(
        operation_summary=_("主机池查询"),
        responses={status.HTTP_200_OK: ListMachinePoolResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["GET"],
        filter_class=DirtyMachinePoolFilter,
        queryset=DirtyMachine.objects.all().order_by("-update_at"),
    )
    def query_machine_pool(self, request):
        machine_qs = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        # 查询主机池主机信息
        machine_data = ListMachinePoolSerializer(machine_qs, many=True).data
        # 补充主机agent状态
        ResourceQueryHelper.fill_agent_status(machine_data, fill_key="agent_status")
        # 补充主机最新主机事件
        MachineEvent.fill_hosts_latest_event(machine_data)
        return self.paginator.get_paginated_response(data=machine_data)
