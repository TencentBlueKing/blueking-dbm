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
from backend.db_services.dbpermission.constants import AccountType
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission, ResourceActionPermission
from backend.db_services.dbpermission.db_account.views import BaseDBAccountViewSet


class DBAccountViewSet(BaseDBAccountViewSet):
    def _get_custom_permissions(self):
        if self.action not in ["create_account", "delete_account", "add_account_rule"]:
            return [DBManagePermission()]

        account_type = self.request.data.get("account_type", AccountType.MYSQL)
        account_action = getattr(ActionEnum, f"{account_type}_{self.action}".upper())
        return [ResourceActionPermission([account_action], ResourceEnum.BUSINESS)]
