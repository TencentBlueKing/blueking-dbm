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

import pytest

from backend.db_services.mysql.permission.authorize.serializers import IntegrationGrantSerializer

BASE_PARAMS = {
    "client_hosts": "%",
    "db_hosts": "test.db#3306",
    "db_name": "test",
    "password": "Zz9!aaaa1",
    "privileges": "SELECT",
}


def validate(user_name):
    slz = IntegrationGrantSerializer(data={**BASE_PARAMS, "user_name": user_name})
    return slz.is_valid(), slz


class TestIntegrationGrantUserName:
    @pytest.mark.parametrize("user_name", ["normal_user", "app-user.01", "a", "A" * 31])
    def test_valid_user_name(self, user_name):
        is_valid, slz = validate(user_name)

        assert is_valid, slz.errors
        assert slz.validated_data["user_name"] == user_name

    @pytest.mark.parametrize(
        "user_name",
        [
            "user_with_quote'",
            "a' or '1'='1",
            "a' union select password from tb_accounts -- ",
            "a%",
            "a\\",
            'a"b',
            "a b",
            "a;drop",
            "_leading_underscore",
            "-leading-dash",
            "A" * 32,
        ],
    )
    def test_invalid_user_name_rejected(self, user_name):
        is_valid, slz = validate(user_name)

        assert not is_valid
        assert "user_name" in slz.errors

    @pytest.mark.parametrize("user_name", ["gcs_admin", "MONITOR", "ADMIN"])
    def test_reserved_user_name_rejected(self, user_name):
        is_valid, slz = validate(user_name)

        assert not is_valid
        assert "user_name" in slz.errors
