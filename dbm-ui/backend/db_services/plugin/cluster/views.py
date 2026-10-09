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

from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import ResponseSwaggerAutoSchema, common_swagger_auto_schema
from backend.db_proxy.models import ClusterExtension
from backend.db_services.dbbase.serializers import ClusterFilterSerializer
from backend.db_services.dbbase.views import DBBaseViewSet
from backend.db_services.plugin.cluster.serializers import (
    DeleteClusterExtensionSerializer,
    OpenAPIQueryClusterCapSerializer,
)
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.view import BaseOpenAPIViewSet


class OpenClusterViewSet(BaseOpenAPIViewSet, DBBaseViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("查询集群负载"),
        query_serializer=OpenAPIQueryClusterCapSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=OpenAPIQueryClusterCapSerializer, pagination_class=None)
    def query_cluster_load(self, request, *args, **kwargs):
        return super().query_cluster_load(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("删除集群额外服务组件"),
        request_body=DeleteClusterExtensionSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=DeleteClusterExtensionSerializer, pagination_class=None)
    def delete_cluster_extension(self, request, *args, **kwargs):
        # TODO: 这里还需要做后台任务删除对应 nginx 的配置
        params = self.params_validate(self.get_serializer_class())
        ClusterExtension.objects.filter(
            bk_biz_id=params["bk_biz_id"], cluster_name=params["cluster_name"], is_deleted=True
        ).delete()
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("根据过滤条件查询业务下集群详细信息"),
        auto_schema=ResponseSwaggerAutoSchema,
        query_serializer=ClusterFilterSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ClusterFilterSerializer, pagination_class=None)
    def filter_clusters(self, request, *args, **kwargs):
        return super().filter_clusters(request, *args, **kwargs)
