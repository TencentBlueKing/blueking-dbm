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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.mysql_partition.client import DBPartitionApi
from backend.db_services.partition.serializers import (
    PartitionCreateSerializer,
    PartitionDeleteSerializer,
    PartitionDisableSerializer,
    PartitionDryRunSerializer,
    PartitionEnableSerializer,
    PartitionListSerializer,
    PartitionLogSerializer,
    PartitionUpdateSerializer,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

from .constants import SWAGGER_TAG
from .handlers import PartitionHandler


class DBPartitionViewSet(viewsets.AuditedModelViewSet):

    pagination_class = None

    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("获取分区策略列表"),
        query_serializer=PartitionListSerializer(),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionListSerializer, representation=True)
        return Response(DBPartitionApi.query_conf(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("修改分区策略"),
        request_body=PartitionUpdateSerializer(),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionUpdateSerializer, representation=True)
        return Response(DBPartitionApi.update_conf(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("增加分区策略"),
        request_body=PartitionCreateSerializer(),
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionCreateSerializer, representation=True)
        return Response(PartitionHandler.create_and_execute_partition(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("批量删除分区策略"),
        request_body=PartitionDeleteSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["DELETE"], detail=False, serializer_class=PartitionDeleteSerializer)
    def batch_delete(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionDeleteSerializer, representation=True)
        return Response(DBPartitionApi.del_conf(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("禁用分区策略"),
        request_body=PartitionDisableSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionDisableSerializer)
    def disable(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionDisableSerializer, representation=True)
        return Response(DBPartitionApi.disable_partition(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("启用分区策略"),
        request_body=PartitionEnableSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionEnableSerializer)
    def enable(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionEnableSerializer, representation=True)
        return Response(DBPartitionApi.enable_partition(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询分区策略日志"),
        request_body=PartitionLogSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionLogSerializer)
    def query_log(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionLogSerializer, representation=True)
        return Response(DBPartitionApi.query_log(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("分区策略前置执行"),
        request_body=PartitionDryRunSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionDryRunSerializer)
    def dry_run(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionDryRunSerializer, representation=True)
        return Response(DBPartitionApi.dry_run(params=validated_data))
