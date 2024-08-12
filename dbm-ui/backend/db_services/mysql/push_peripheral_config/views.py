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
import logging

from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_services.mysql.push_peripheral_config.constants import SWAGGER_TAG
from backend.db_services.mysql.push_peripheral_config.serializers import PushPeripheralConfigSerializer
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


class PushPeripheralConfigViewSet(viewsets.SystemViewSet):
    pagination_class = None

    def _get_custom_permissions(self):
        migrate_users = SystemSettings.get_setting_value(key=SystemSettingsEnum.DBM_MIGRATE_USER, default=[])
        if self.request.user.is_superuser or self.request.user.username in migrate_users:
            return []
        return [RejectPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("下发周边配置"),
        tags=[SWAGGER_TAG],
        request_body=PushPeripheralConfigSerializer(),
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=PushPeripheralConfigSerializer,
    )
    def push_peripheral_config(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        PushPeripheralConfigSerializer(data=data).is_valid(raise_exception=True)
        Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_PUSH_PERIPHERAL_CONFIG,
            creator=request.user.username,
            bk_biz_id=data["bk_biz_id"],
            remark=self.push_peripheral_config.__name__,
            details=data,
        )
        return Response(data)
