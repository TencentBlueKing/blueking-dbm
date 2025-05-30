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
import base64

from backend.components import DBPrivManagerApi
from backend.flow.consts import DEFAULT_INSTANCE, MySQLPrivComponent, UserName


class AccountMixedBase(object):
    @staticmethod
    def _query_user(component: MySQLPrivComponent, *users: UserName):
        user_map = {}
        value_to_name = {member.value: member.name.lower() for member in UserName}

        data = DBPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [{"username": username.value, "component": component.value} for username in users],
            }
        )
        for user in data["items"]:
            user_map[value_to_name[user["username"]] + "_user"] = (
                "MONITOR" if user["username"] == UserName.MONITOR_ACCESS_ALL else user["username"]
            )
            user_map[value_to_name[user["username"]] + "_pwd"] = base64.b64decode(user["password"]).decode("utf-8")

        return user_map
