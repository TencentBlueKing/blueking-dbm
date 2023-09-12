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

from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_services.mysql.permission.db_account.mock_data import LIST_MYSQL_ACCOUNT_RULE_RESPONSE
from backend.tests.mock_data.constant import Response
from backend.tests.mock_data.db_services.mysql.permission.account import POLICY_DATA
from backend.tests.mock_data.utils import raw_response


class MySQLPrivManagerApiMock(object):
    """dbpriv相关接口的mock"""

    base_data = {"code": 0, "message": "ok", "data": None}

    @classmethod
    @raw_response
    def create_account(cls, *args, **kwargs):
        data = args[0]
        password = data.get("psw", "")
        plain_password = AsymmetricHandler.decrypt(
            name=AsymmetricCipherConfigType.PASSWORD.value, content=password, salted=False
        )
        data.update(password=plain_password)
        return data

    @classmethod
    @raw_response
    def check_password(cls, *args, **kwargs):
        data = {"is_strength": True, "password_verify_info": POLICY_DATA}
        return data

    @classmethod
    @raw_response
    def update_password(cls, *args, **kwargs):
        return cls.create_account(*args, **kwargs)

    @classmethod
    @raw_response
    def fetch_public_key(cls, *agrs, **kwargs):
        cipher = AsymmetricHandler.get_or_generate_cipher_instance(name=AsymmetricCipherConfigType.PASSWORD.value)
        data = cipher.export_public_key()
        return data

    @classmethod
    @raw_response
    def delete_account(cls, *args, **kwargs):
        # TODO 暂时没想到好的mock方法
        return None

    @classmethod
    @raw_response
    def list_account_rules(cls, *args, **kwargs):
        return LIST_MYSQL_ACCOUNT_RULE_RESPONSE

    @classmethod
    @raw_response
    def pre_check_authorize_rules(cls, *args, **kwargs):
        authorize_data = kwargs["params"]
        return authorize_data

    @classmethod
    @raw_response
    def clone_api_field(cls, *args, **kwargs):
        clone_data = kwargs["params"]
        message_list = []
        for index, instance in enumerate(clone_data["source"]):
            message_list.append(f"line {index}:{instance} is not valid")

        return Response(data=None, message="\n".join(message_list), code=10001)

    @classmethod
    @raw_response
    def authorize_rules(cls, *args, **kwargs):
        return True

    @classmethod
    @raw_response
    def clone_instance(cls, *args, **kwargs):
        return True

    @classmethod
    @raw_response
    def clone_client(cls, *args, **kwargs):
        return True

    @classmethod
    @raw_response
    def modify_user_password(cls, *args, **kwargs):
        return True
