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

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_dirty.filters import DirtyMachinePoolFilter
from backend.db_dirty.models import DirtyMachine
from backend.db_dirty.serializers import ListMachinePoolResponseSerializer, TransferDirtyMachineSerializer
from backend.db_dirty.views import DBDirtyMachineViewSet
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet

logger = logging.getLogger("root")


class DBDirtyMachineApiGwViewSet(BaseOpenAPIViewSet, DBDirtyMachineViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("将主机转移至待回收/故障池模块"),
        request_body=TransferDirtyMachineSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=TransferDirtyMachineSerializer)
    def transfer_hosts_to_pool(self, request):
        return super().transfer_hosts_to_pool(request)

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
        return super().query_machine_pool(request)
