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
import copy
from unittest.mock import patch

import pytest

from backend.configuration.models.password_policy import PasswordPolicy
from backend.core.encrypt.constants import RSAConfigType
from backend.core.encrypt.handlers import RSAHandler
from backend.core.encrypt.models import RSAKey
from backend.db_services.mysql.permission.db_account.dataclass import AccountMeta, AccountRuleMeta
from backend.db_services.mysql.permission.db_account.handlers import AccountHandler
from backend.tests.mock_data.components.mysql_priv_manager import MySQLPrivManagerApiMock
from backend.tests.mock_data.db_services.mysql.permission.account import (
    ACCOUNT,
    ACCOUNT_RULE,
    INVALID_PASSWORD_LIST,
    POLICY_DATA,
    VALID_PASSWORD_LIST,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def query_fixture(django_db_blocker):
    with django_db_blocker.unblock():
        RSAHandler.get_or_generate_rsa_in_db(RSAConfigType.MYSQL.value)
        PasswordPolicy.objects.create(account_type=RSAConfigType.MYSQL.value, policy=POLICY_DATA)

        yield
        RSAKey.objects.all().delete()
        PasswordPolicy.objects.all().delete()


class TestAccountHandler:
    """
    AccountHandler的测试类
    """

    @pytest.mark.parametrize("password", VALID_PASSWORD_LIST + INVALID_PASSWORD_LIST)
    def test_check_password_strength__valid(self, password):
        is_pwd_valid, _ = AccountHandler._check_password_strength(password, rule_data=copy.deepcopy(POLICY_DATA))
        assert is_pwd_valid == (password in VALID_PASSWORD_LIST)

    @patch("backend.db_services.mysql.permission.db_account.handlers.MySQLPrivManagerApi", MySQLPrivManagerApiMock)
    def test_create_account(self, query_fixture):
        account = AccountMeta(**ACCOUNT)
        data = AccountHandler(bk_biz_id=1).create_account(account)
        assert data["password"] == ACCOUNT["password"]

    @patch("backend.db_services.mysql.permission.db_account.handlers.MySQLPrivManagerApi", MySQLPrivManagerApiMock)
    def test_update_account(self, query_fixture):
        account = AccountMeta(**ACCOUNT)
        data = AccountHandler(bk_biz_id=1).update_password(account)
        assert data["password"] == ACCOUNT["password"]

    @patch("backend.db_services.mysql.permission.db_account.handlers.MySQLPrivManagerApi", MySQLPrivManagerApiMock)
    def test_delete_account(self, query_fixture):
        account = AccountMeta(**ACCOUNT)
        data = AccountHandler(bk_biz_id=1).delete_account(account)
        assert not data

    @patch("backend.db_services.mysql.permission.db_account.handlers.MySQLPrivManagerApi", MySQLPrivManagerApiMock)
    def test_list_account_rules(self, query_fixture):
        account_rule = AccountRuleMeta(**ACCOUNT_RULE)
        data = AccountHandler(bk_biz_id=1).list_account_rules(account_rule)
        assert data["count"] == 1

    @pytest.mark.parametrize("password", VALID_PASSWORD_LIST + INVALID_PASSWORD_LIST)
    def test_verify_password_strength__valid(self, password):
        rsa = RSAHandler.get_or_generate_rsa_in_db(name=RSAConfigType.MYSQL.value)
        account = AccountMeta(password=RSAHandler.encrypt_password(rsa.rsa_public_key.content, password, None))

        is_strength = AccountHandler(bk_biz_id=1).verify_password_strength(account)["is_strength"]
        assert is_strength == (password in VALID_PASSWORD_LIST)
