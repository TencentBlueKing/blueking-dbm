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
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.cluster_state.handlers import ClusterStateHandler
from backend.db_services.cluster_state.serializers import (
    StateDetailQuerySerializer,
    StateDetailResponseSerializer,
    StateSchemaQuerySerializer,
    StateSchemaResponseSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/cluster_state"


class ClusterStateViewSet(viewsets.SystemViewSet):
    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询集群状态字段定义"),
        query_serializer=StateSchemaQuerySerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: StateSchemaResponseSerializer()},
    )
    @action(methods=["GET"], detail=False, url_path="schema")
    def get_state_schema(self, request, bk_biz_id):
        data = self.params_validate(StateSchemaQuerySerializer)
        return Response(ClusterStateHandler(bk_biz_id).get_schema(data["cluster_type"]))

    @common_swagger_auto_schema(
        operation_summary=_("查询集群状态详情"),
        query_serializer=StateDetailQuerySerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: StateDetailResponseSerializer()},
    )
    @action(methods=["GET"], detail=False, url_path="detail")
    def get_state_detail(self, request, bk_biz_id):
        data = self.params_validate(StateDetailQuerySerializer)
        return Response(ClusterStateHandler(bk_biz_id).get_detail(data["cluster_id"], data["key"]))
