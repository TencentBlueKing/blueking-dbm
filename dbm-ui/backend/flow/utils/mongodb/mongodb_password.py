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
from backend.flow.consts import MediumEnum, MongoDBPasswordRule, RequestResultCode


class MongoDBPassword(object):
    """
    mongodb用户密码
    """

    def __init__(self):
        self.security_rule_name = MongoDBPasswordRule.RULE.value
        self.component = MediumEnum.MongoDB.value

    @staticmethod
    def base64_encode(password: str) -> str:
        """进行base64编码"""

        return str(base64.b64encode(password.encode("utf-8")), "utf-8")

    @staticmethod
    def base64_decode(password: str) -> str:
        """进行base64解码"""

        return str(base64.b64decode(password), "utf-8")

    def create_user_password(self) -> dict:
        """创建密码"""

        result = DBPrivManagerApi.get_random_string(
            {"security_rule_name": self.security_rule_name},
            raw=True,
        )
        if result["code"] != RequestResultCode.Success.value:
            return {"password": None, "info": result["message"]}
        if self.base64_decode(result["data"])[0] == "-" or self.base64_decode(result["data"])[0:2] == "--":
            return {"password": self.base64_decode(result["data"]).replace("-", "!"), "info": None}
        return {"password": self.base64_decode(result["data"]), "info": None}

    def save_password_to_db(self, instances: list, username: str, password: str, operator: str) -> str:
        """把密码保存到db中"""

        result = DBPrivManagerApi.modify_password(
            {
                "instances": instances,
                "username": username,
                "component": self.component,
                "password": self.base64_encode(password),
                "operator": operator,
                "security_rule_name": self.security_rule_name,
            },
            raw=True,
        )
        if result["code"] != RequestResultCode.Success.value:
            return result["message"] + " " + result["data"]

    def delete_password_from_db(self, instances: list, usernames: list) -> str:
        """
        从db中删除密码
        instances [{"ip":"x.x.x.x","port":1234,"bk_cloud_id":0}]
        usernames ["user1", "user2"]
        """

        users = []
        for user in usernames:
            users.append({"username": user, "component": self.component})
        result = DBPrivManagerApi.delete_password(
            {
                "instances": instances,
                "users": users,
            },
            raw=True,
        )
        if result["code"] != RequestResultCode.Success.value:
            return result["message"]

    def get_password_from_db(self, ip: str, port: int, bk_cloud_id: int, username: str) -> dict:
        """从db获取密码"""

        result = DBPrivManagerApi.get_password(
            {
                "instances": [{"ip": ip, "port": port, "bk_cloud_id": bk_cloud_id}],
                "users": [{"username": username, "component": self.component}],
            },
            raw=True,
        )
        if result["code"] != RequestResultCode.Success.value:
            return {"password": None, "info": result["message"]}
        return {"password": self.base64_decode(result["data"]["items"][0]["password"]), "info": None}
