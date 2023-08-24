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
from backend.db_meta.enums import ClusterType
from backend.db_services.version import serializers
from backend.db_services.version.utils import query_versions_by_key

SWAGGER_TAG = "version"


class VersionViewSet(viewsets.SystemViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("查询所有数据库的版本列表"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=None, pagination_class=None)
    def cluster_type_to_versions(self, requests, *args, **kwargs):
        return Response(
            {cluster_type: query_versions_by_key(cluster_type) for cluster_type in ClusterType.get_values()}
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询数据库版本列表"),
        query_serializer=serializers.ListVersionSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=serializers.ListVersionSerializer)
    def list_versions(self, requests, *args, **kwargs):
        """版本列表"""
        validated_data = self.params_validate(self.get_serializer_class())
        query_key = validated_data["query_key"]
        versions = query_versions_by_key(query_key)
        return Response(versions)
