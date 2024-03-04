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
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbbase.cluster.views import ClusterViewSet as BaseClusterViewSet
from backend.db_services.sqlserver.cluster.handlers import ClusterServiceHandler
from backend.db_services.sqlserver.cluster.serializers import (
    CheckDBExistResponseSerializer,
    CheckDBExistSerializer,
    GetDBForDrsResponseSerializer,
    GetDBForDrsSerializer,
    ImportDBStructResponseSerializer,
    ImportDBStructSerializer,
    MultiGetDBForDrsResponseSerializer,
    MultiGetDBForDrsSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/sqlserver/cluster"


class ClusterViewSet(BaseClusterViewSet):
    def _get_custom_permissions(self):
        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("通过库表匹配查询db"),
        request_body=GetDBForDrsSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: GetDBForDrsResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=GetDBForDrsSerializer)
    def get_sqlserver_dbs(self, request, bk_biz_id):
        data = self.params_validate(self.get_serializer_class())
        return Response(ClusterServiceHandler(bk_biz_id).get_dbs_for_drs(**data))

    @common_swagger_auto_schema(
        operation_summary=_("通过库表匹配批量查询db"),
        request_body=MultiGetDBForDrsSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: MultiGetDBForDrsResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=MultiGetDBForDrsSerializer)
    def multi_get_sqlserver_dbs(self, request, bk_biz_id):
        data = self.params_validate(self.get_serializer_class())
        return Response(ClusterServiceHandler(bk_biz_id).multi_get_dbs_for_drs(**data))

    @common_swagger_auto_schema(
        operation_summary=_("判断库名是否在集群存在"),
        request_body=CheckDBExistSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: CheckDBExistResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=CheckDBExistSerializer)
    def check_sqlserver_db_exist(self, request, bk_biz_id):
        data = self.params_validate(self.get_serializer_class())
        return Response(ClusterServiceHandler(bk_biz_id).check_cluster_database(**data))

    @common_swagger_auto_schema(
        operation_summary=_("导入构造DB数据"),
        request_body=ImportDBStructSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: ImportDBStructResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=ImportDBStructSerializer)
    def import_db_struct(self, request, bk_biz_id):
        data = self.params_validate(self.get_serializer_class())
        return Response(ClusterServiceHandler(bk_biz_id).import_db_struct(**data))
