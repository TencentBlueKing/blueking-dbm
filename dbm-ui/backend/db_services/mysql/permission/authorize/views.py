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

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbpermission.db_authorize.views import DBAuthorizeViewSet as BaseDBAuthorizeViewSet
from backend.db_services.mysql.permission.authorize.dataclass import (
    HostInAuthorizeFilterMeta,
    MySQLAuthorizeMeta,
    MySQLExcelAuthorizeMeta,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.db_services.mysql.permission.authorize.handlers import MySQLAuthorizeHandler
from backend.db_services.mysql.permission.authorize.serializers import GetHostInAuthorizeSerializer

SWAGGER_TAG = "db_services/permission/authorize"


class DBAuthorizeViewSet(BaseDBAuthorizeViewSet):

    handler = MySQLAuthorizeHandler
    authorize_meta = MySQLAuthorizeMeta
    excel_authorize_meta = MySQLExcelAuthorizeMeta

    def _get_custom_permissions(self):
        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询授权主机的信息"),
        query_serializer=GetHostInAuthorizeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetHostInAuthorizeSerializer)
    def get_host_in_authorize(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, HostInAuthorizeFilterMeta, self.handler.get_host_in_authorize.__name__
        )
