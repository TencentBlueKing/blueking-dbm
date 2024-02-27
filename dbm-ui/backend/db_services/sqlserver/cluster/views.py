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

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.sqlserver.cluster.handlers import ClusterServiceHandler
from backend.db_services.sqlserver.cluster.serializers import GetDBForDrsResponseSerializer, GetDBForDrsSerializer
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/sqlserver/cluster"


class ClusterViewSet(viewsets.SystemViewSet):
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
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(ClusterServiceHandler(bk_biz_id).get_dbs_for_drs(**validated_data))
