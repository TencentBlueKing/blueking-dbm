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
import os

import mock
import pytest
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import BKCity, DBModule, LogicalCity
from backend.tests.constants import TEST_ADMIN_USERNAME
from backend.tests.mock_data import constant


def mock_bk_user(username):
    User = get_user_model()  # pylint: disable=invalid-name
    user = User.objects.create(username=username)

    # Set token attribute
    user.token = mock.MagicMock()
    user.token.access_token = get_random_string(12)
    user.token.expires_soon = lambda: False

    return user


@pytest.fixture
def bk_user():
    return mock_bk_user(get_random_string(6))


@pytest.fixture
def bk_admin():
    return mock_bk_user(TEST_ADMIN_USERNAME)


@pytest.fixture
def create_city():
    LogicalCity.objects.get_or_create(id=1, defaults={"name": "南京"})
    LogicalCity.objects.get_or_create(id=2, defaults={"name": "上海"})

    BKCity.objects.create(logical_city_id=1, bk_idc_city_id=21, bk_idc_city_name="南京")
    BKCity.objects.create(logical_city_id=1, bk_idc_city_id=1955, bk_idc_city_name="仪征")
    BKCity.objects.create(logical_city_id=2, bk_idc_city_id=28, bk_idc_city_name="上海")


@pytest.fixture
def init_db_module():
    DBModule.objects.create(
        db_module_id=constant.DB_MODULE_ID,
        bk_biz_id=constant.BK_BIZ_ID,
        cluster_type=ClusterType.TenDBHA.value,
        db_module_name="test",
    )


mark_global_skip = pytest.mark.skipif(os.environ.get("GLOBAL_SKIP") == "true", reason="disable in landun WIP")
