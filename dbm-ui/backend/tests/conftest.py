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
import ipaddress
import os

import mock
import pytest
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from backend.db_meta import models
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.models import BKCity, Cluster, DBModule, LogicalCity, Machine
from backend.tests.constants import TEST_ADMIN_USERNAME
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc


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
def machine_fixture(create_city):
    bk_city = BKCity.objects.first()
    Machine.objects.create(
        ip=cc.NORMAL_IP2,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        bk_cloud_id=1,
        bk_host_id=2,
    )


@pytest.fixture
def init_proxy_machine(create_city):
    bk_city = models.BKCity.objects.first()
    machine = models.Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.PROXY,
    )
    return machine


@pytest.fixture
def init_storage_machine(create_city):
    bk_city = models.BKCity.objects.first()
    machine = models.Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.STORAGE,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP)),
    )
    return machine


@pytest.fixture
def init_db_module():
    DBModule.objects.create(
        db_module_id=constant.DB_MODULE_ID,
        bk_biz_id=constant.BK_BIZ_ID,
        cluster_type=ClusterType.TenDBHA.value,
        db_module_name="test",
    )


@pytest.fixture
def init_cluster():
    Cluster.objects.create(
        bk_biz_id=constant.BK_BIZ_ID,
        name=constant.CLUSTER_NAME,
        db_module_id=constant.DB_MODULE_ID,
        immute_domain=constant.CLUSTER_IMMUTE_DOMAIN,
        cluster_type=ClusterType.TenDBHA.value,
    )


mark_global_skip = pytest.mark.skipif(os.environ.get("GLOBAL_SKIP") == "true", reason="disable in landun WIP")
