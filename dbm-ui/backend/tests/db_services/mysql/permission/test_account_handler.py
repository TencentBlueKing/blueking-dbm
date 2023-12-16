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
import logging
from unittest.mock import patch

import pytest

from backend.configuration.handlers.password import DBPasswordHandler
from backend.configuration.models.password_policy import PasswordPolicy
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.core.encrypt.models import AsymmetricCipherKey
from backend.db_services.dbpermission.constants import AccountType
from backend.db_services.dbpermission.db_account.dataclass import AccountMeta, AccountRuleMeta
from backend.db_services.mysql.permission.db_account.handlers import MySQLAccountHandler
from backend.tests.mock_data.components.mysql_priv_manager import DBPrivManagerApiMock
from backend.tests.mock_data.db_services.mysql.permission.account import (
    ACCOUNT,
    ACCOUNT_RULE,
    POLICY_DATA,
    VALID_PASSWORD_LIST,
)

pytestmark = pytest.mark.django_db
logger = logging.getLogger("root")


@pytest.fixture(scope="module")
def query_fixture(django_db_blocker):
    with django_db_blocker.unblock():
        AsymmetricHandler.get_or_generate_cipher_instance(AsymmetricCipherConfigType.PASSWORD.value)
        PasswordPolicy.objects.create(account_type=AsymmetricCipherConfigType.PASSWORD.value, policy=POLICY_DATA)
        yield
        AsymmetricCipherKey.objects.all().delete()
        PasswordPolicy.objects.all().delete()


class TestAccountHandler:
    """
    AccountHandler的测试类
    """

    @patch("backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi", DBPrivManagerApiMock)
    def test_create_account(self, query_fixture):
        account = AccountMeta(**ACCOUNT)
        data = MySQLAccountHandler(bk_biz_id=1, account_type=AccountType.MYSQL).create_account(account)
        assert data["password"] == ACCOUNT["password"]

    @patch("backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi", DBPrivManagerApiMock)
    def test_update_account(self, query_fixture):
        account = AccountMeta(**ACCOUNT)
        data = MySQLAccountHandler(bk_biz_id=1, account_type=AccountType.MYSQL).update_password(account)
        assert data["password"] == ACCOUNT["password"]

    @patch("backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi", DBPrivManagerApiMock)
    def test_delete_account(self, query_fixture):
        account = AccountMeta(**ACCOUNT)
        data = MySQLAccountHandler(bk_biz_id=1, account_type=AccountType.MYSQL).delete_account(account)
        assert not data

    @patch("backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi", DBPrivManagerApiMock)
    def test_list_account_rules(self, query_fixture):
        account_rule = AccountRuleMeta(**ACCOUNT_RULE)
        data = MySQLAccountHandler(bk_biz_id=1, account_type=AccountType.MYSQL).list_account_rules(account_rule)
        assert data["count"] == 1

    @pytest.mark.parametrize("password", VALID_PASSWORD_LIST)
    @patch("backend.configuration.handlers.password.DBPrivManagerApi", DBPrivManagerApiMock)
    def test_verify_password_strength__valid(self, password):
        password = AsymmetricHandler.encrypt(
            name=AsymmetricCipherConfigType.PASSWORD.value, content=password, need_salt=False
        )
        check_result = DBPasswordHandler.verify_password_strength(password)
        is_strength = check_result["is_strength"]
        assert is_strength
