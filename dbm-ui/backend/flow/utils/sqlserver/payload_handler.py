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
import logging

from backend.components import MySQLPrivManagerApi
from backend.flow.consts import DEFAULT_INSTANCE, SqlserverComponent, SqlserverUserName

logger = logging.getLogger("flow")


class PayloadHandler(object):
    def __init__(self, global_data: dict):
        """
        @param global_data 流程/子流程全局信息
        """
        self.global_data = global_data

    @staticmethod
    def get_sqlserver_account():
        """
        获取sqlserver实例内置帐户密码
        """
        user_map = {}
        value_to_name = {member.value: member.name.lower() for member in SqlserverUserName}
        data = MySQLPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [
                    {"username": SqlserverUserName.MSSQL.value, "component": SqlserverComponent.SQLSERVER.value},
                    {"username": SqlserverUserName.SQLSERVER.value, "component": SqlserverComponent.SQLSERVER.value},
                    {"username": SqlserverUserName.SA.value, "component": SqlserverComponent.SQLSERVER.value},
                    {"username": SqlserverUserName.EXPORTER.value, "component": SqlserverComponent.SQLSERVER.value},
                ],
            }
        )
        for user in data["items"]:
            user_map[value_to_name[user["username"]] + "_user"] = user["username"]
            user_map[value_to_name[user["username"]] + "_pwd"] = base64.b64decode(user["password"]).decode("utf-8")

        return user_map

    @staticmethod
    def get_version_key(version):
        """
        获取版本的key
        """
        data = MySQLPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [
                    {"username": version, "component": SqlserverComponent.SQLSERVER.value},
                ],
            }
        )
        if data["count"] == 0:
            return None

        return base64.b64decode(data["items"][0]["password"]).decode("utf-8")
