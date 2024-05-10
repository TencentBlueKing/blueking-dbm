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
from django_filters import rest_framework
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_dirty.constants import SWAGGER_TAG
from backend.db_dirty.filters import DirtyMachineFilter
from backend.db_dirty.handlers import DBDirtyMachineHandler
from backend.db_dirty.models import DirtyMachine
from backend.db_dirty.serializers import (
    DeleteDirtyMachineSerializer,
    QueryDirtyMachineResponseSerializer,
    QueryDirtyMachineSerializer,
    TransferDirtyMachineSerializer,
)
from backend.iam_app.handlers.drf_perm import GlobalManageIAMPermission


class DBDirtyMachineViewSet(viewsets.SystemViewSet):
    pagination_class = None
    filter_class = None

    def _get_custom_permissions(self):
        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询污点池列表"),
        responses={status.HTTP_200_OK: QueryDirtyMachineResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="query_dirty_machines",
        serializer_class=QueryDirtyMachineSerializer,
        pagination_class=AuditedLimitOffsetPagination,
        filter_class=DirtyMachineFilter,
        filter_backends=(rest_framework.DjangoFilterBackend,),
        queryset=DirtyMachine.objects.all(),
    )
    def query_operation_list(self, request):
        dirty_machines = self.filter_queryset(self.get_queryset())
        page_dirty_machines = self.paginate_queryset(dirty_machines)
        dirty_machine_list = DBDirtyMachineHandler.query_dirty_machine_records(page_dirty_machines)
        return self.paginator.get_paginated_response(data=dirty_machine_list)

    @common_swagger_auto_schema(
        operation_summary=_("将污点池主机转移至待回收模块"),
        request_body=TransferDirtyMachineSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="transfer_dirty_machines",
        serializer_class=TransferDirtyMachineSerializer,
    )
    def transfer_dirty_machines(self, request):
        bk_host_ids = self.params_validate(self.get_serializer_class())["bk_host_ids"]
        DBDirtyMachineHandler.transfer_dirty_machines(bk_host_ids)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("删除污点池记录"),
        request_body=DeleteDirtyMachineSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["DELETE"],
        url_path="delete_dirty_records",
        serializer_class=DeleteDirtyMachineSerializer,
    )
    def delete_dirty_records(self, request):
        bk_host_ids = self.params_validate(self.get_serializer_class())["bk_host_ids"]
        DBDirtyMachineHandler.remove_dirty_machines(bk_host_ids)
        return Response()
