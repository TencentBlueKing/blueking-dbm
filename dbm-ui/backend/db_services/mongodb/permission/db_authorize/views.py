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

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.dbpermission.db_authorize.views import DBAuthorizeViewSet as BaseDBAuthorizeViewSet
from backend.db_services.mongodb.permission.db_authorize.dataclass import (
    MongoDBAuthorizeMeta,
    MongoDBExcelAuthorizeMeta,
)
from backend.db_services.mongodb.permission.db_authorize.handlers import MongoDBAuthorizeHandler
from backend.db_services.mongodb.permission.db_authorize.serializers import (
    MongoDBPreCheckAuthorizeRulesResponseSerializer,
    MongoDBPreCheckAuthorizeRulesSerializer,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

SWAGGER_TAG = "db_services/permission/authorize"


class DBAuthorizeViewSet(BaseDBAuthorizeViewSet):

    handler = MongoDBAuthorizeHandler
    authorize_meta = MongoDBAuthorizeMeta
    excel_authorize_meta = MongoDBExcelAuthorizeMeta

    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("规则前置检查"),
        request_body=MongoDBPreCheckAuthorizeRulesSerializer(),
        responses={status.HTTP_200_OK: MongoDBPreCheckAuthorizeRulesResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=MongoDBPreCheckAuthorizeRulesSerializer)
    def pre_check_rules(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, self.authorize_meta, self.handler.multi_user_pre_check_rules.__name__
        )
