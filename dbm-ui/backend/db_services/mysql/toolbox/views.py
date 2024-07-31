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
from backend.db_services.mysql.toolbox.handlers import ToolboxHandler
from backend.db_services.mysql.toolbox.serializers import QueryPkgListByCompareVersionSerializer
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/mysql/toolbox"


class ToolboxViewSet(viewsets.SystemViewSet):
    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询 MySQL 可以用的升级包"),
        request_body=QueryPkgListByCompareVersionSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryPkgListByCompareVersionSerializer)
    def query_higher_version_pkg_list(self, request, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id, higher_major_version = data["cluster_id"], data["higher_major_version"]
        return Response(ToolboxHandler().query_higher_version_pkg_list(cluster_id, higher_major_version))
