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

from django.utils.translation import ugettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.ticket.serializers import OpenAPIBatchTicketOperateSerializer
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.ticket.handler import TicketHandler
from backend.ticket.serializers import TodoSerializer

logger = logging.getLogger("root")


class TicketViewSet(BaseOpenAPIViewSet):
    @swagger_auto_schema(
        operation_summary=_("批量单据待办处理"),
        request_body=OpenAPIBatchTicketOperateSerializer(),
        responses={status.HTTP_200_OK: TodoSerializer(many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=OpenAPIBatchTicketOperateSerializer)
    def batch_process_ticket(self, request, *args, **kwargs):
        params = self.params_validate(self.get_serializer_class())
        return Response(TicketHandler.batch_process_ticket(**params))
