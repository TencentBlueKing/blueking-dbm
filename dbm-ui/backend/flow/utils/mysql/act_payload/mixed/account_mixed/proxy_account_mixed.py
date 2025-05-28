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

from backend.flow.consts import MySQLPrivComponent, UserName
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.account_mixed_base import AccountMixedBase


class ProxyAccountMixed(AccountMixedBase):
    @staticmethod
    def proxy_admin_account():
        user_map = AccountMixedBase._query_user(MySQLPrivComponent.PROXY, UserName.PROXY)

        return {"proxy_admin_pwd": user_map["proxy_pwd"], "proxy_admin_user": user_map["proxy_user"]}
