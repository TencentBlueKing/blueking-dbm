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
from backend.db_services.dbpermission.db_account.serializers import AddAccountRuleSerializer
from backend.db_services.dbpermission.db_account.views import SWAGGER_TAG, BaseDBAccountViewSet
from backend.db_services.mysql.permission.db_account.handlers import MySQLAccountHandler


class DBAccountViewSet(BaseDBAccountViewSet):
    account_handler = MySQLAccountHandler

    @common_swagger_auto_schema(
        operation_summary=_("添加账号规则前置检查"), request_body=AddAccountRuleSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=AddAccountRuleSerializer)
    def pre_check_add_account_rule(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, self.account_rule_meta, self.account_handler.pre_check_add_account_rule.__name__
        )
