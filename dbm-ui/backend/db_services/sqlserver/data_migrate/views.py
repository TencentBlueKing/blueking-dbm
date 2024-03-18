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
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.sqlserver.data_migrate.handlers import SQLServerDataMigrateHandler
from backend.db_services.sqlserver.data_migrate.serializers import (
    ForceFailedMigrateSerializer,
    ManualTerminateSyncResponseSerializer,
    ManualTerminateSyncSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/sqlserver/migrate"


class SQLServerDataMigrateViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("手动断开同步"),
        request_body=ManualTerminateSyncSerializer(),
        responses={status.HTTP_200_OK: ManualTerminateSyncResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ManualTerminateSyncSerializer)
    def manual_terminate_sync(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        ticket = SQLServerDataMigrateHandler.manual_terminate_sync(ticket_id=data["ticket_id"])
        return Response({"ticket_id": ticket.id})

    @common_swagger_auto_schema(
        operation_summary=_("强制终止"),
        request_body=ForceFailedMigrateSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ForceFailedMigrateSerializer)
    def force_failed_migrate(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        SQLServerDataMigrateHandler.force_failed_migrate(dts_id=data["dts_id"])
        return Response()
