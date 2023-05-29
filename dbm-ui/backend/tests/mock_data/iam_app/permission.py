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

from typing import List, Union

from django.utils.crypto import get_random_string
from iam import DummyIAM

from backend import env
from backend.iam_app.dataclass.actions import ActionMeta
from backend.iam_app.dataclass.resources import Resource
from backend.iam_app.handlers.permission import Permission
from backend.tests.conftest import mock_bk_user


class PermissionMock(Permission):
    """
    权限中心的mock类
    """

    def __init__(self, username: str = "", request=None):
        username = username or mock_bk_user(get_random_string(10))
        request = request or {}

        super().__init__(username, request)

    @classmethod
    def get_iam_client(cls):
        return DummyIAM(env.APP_CODE, env.SECRET_KEY, env.BK_IAM_INNER_HOST, env.BK_COMPONENT_API_URL)

    @classmethod
    def policy_query(cls, action: Union[ActionMeta, str], obj_list: List = None) -> List:
        return obj_list

    @classmethod
    def is_allowed(
        cls, action: Union[ActionMeta, str], resources: List[Resource], is_raise_exception: bool = False
    ) -> bool:
        return True
