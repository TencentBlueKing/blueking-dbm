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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.mysql.apply.serializers import MysqlHaApplyQuickMinorPassSerializer
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.ticket.constants import TicketType
from backend.ticket.contexts import TicketContext
from backend.ticket.models import Ticket
from backend.ticket.serializers import TicketSerializer


class ApplyPluginViewSet(viewsets.SystemViewSet):
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("第三方权限申请mysql集群小额绿通部署"),
        request_body=MysqlHaApplyQuickMinorPassSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=MysqlHaApplyQuickMinorPassSerializer)
    def mysql_ha_apply_quick_minor_pass(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        # 自动创建ticket
        ticket = Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_HA_APPLY_QUICK_MINOR_PASS,
            creator=request.user.username,
            bk_biz_id=request.data["bk_biz_id"],
            remark=request.data["remark"],
            details=data,
        )
        serializer_data = TicketSerializer(
            instance=ticket,
            context={
                "request": request,
                "ticket_type": TicketType.MYSQL_HA_APPLY_QUICK_MINOR_PASS,
                "bk_biz_id": request.data["bk_biz_id"],
                "ticket_ctx": TicketContext(),
            },
        ).data
        return Response(serializer_data)
