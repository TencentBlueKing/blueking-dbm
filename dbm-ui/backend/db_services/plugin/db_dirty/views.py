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
from rest_framework.decorators import action

from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_dirty.filters import DirtyMachinePoolFilter
from backend.db_dirty.models import DirtyMachine
from backend.db_dirty.serializers import ListMachinePoolSerializer
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet

logger = logging.getLogger("root")


class DBDirtyMachineViewSet(BaseOpenAPIViewSet):
    filter_class = None
    pagination_class = AuditedLimitOffsetPagination

    @common_swagger_auto_schema(
        operation_summary=_("主机池查询"),
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
        machine_data = ListMachinePoolSerializer(machine_qs, many=True).data
        return self.paginator.get_paginated_response(data=machine_data)
