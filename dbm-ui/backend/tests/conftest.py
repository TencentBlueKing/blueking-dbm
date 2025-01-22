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
import os

import mock
import pytest
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, ClusterType
from backend.db_meta.models import AppCache, BKCity, Cluster, ClusterEntry, DBModule, LogicalCity, Machine, Spec
from backend.tests.mock_data import constant
from backend.tests.mock_data.constant import INIT_MACHINE_DATA, INIT_SPEC_DATA


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
    return mock_bk_user("admin")


@pytest.fixture(scope="session", autouse=True)
def create_city(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        LogicalCity.objects.get_or_create(id=1, defaults={"name": "南京"})
        LogicalCity.objects.get_or_create(id=2, defaults={"name": "上海"})
        BKCity.objects.create(logical_city_id=1, bk_idc_city_id=21, bk_idc_city_name="南京")
        BKCity.objects.create(logical_city_id=1, bk_idc_city_id=1955, bk_idc_city_name="仪征")
        BKCity.objects.create(logical_city_id=2, bk_idc_city_id=28, bk_idc_city_name="上海")
        yield
        BKCity.objects.all().delete()
        LogicalCity.objects.all().delete()


# TODO: 初始化各个集群的模块信息
@pytest.fixture
def init_db_module():
    DBModule.objects.create(
        db_module_id=constant.DB_MODULE_ID,
        bk_biz_id=constant.BK_BIZ_ID,
        cluster_type=ClusterType.TenDBHA.value,
        db_module_name="test",
    )


# TODO: 初始化mysql集群信息
@pytest.fixture()
def init_cluster():
    cluster = Cluster.objects.create(
        bk_biz_id=constant.BK_BIZ_ID,
        name=constant.CLUSTER_NAME,
        db_module_id=constant.DB_MODULE_ID,
        immute_domain=constant.CLUSTER_IMMUTE_DOMAIN,
        cluster_type=ClusterType.TenDBHA.value,
    )
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS.value,
        entry=constant.CLUSTER_IMMUTE_DOMAIN,
        role=ClusterEntryRole.MASTER_ENTRY,
    )
    yield cluster


# 全局初始化AppCache信息 -- 自动创建
@pytest.fixture(scope="session", autouse=True)
def init_app(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        app = AppCache.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            db_app_abbr="DBA",
            bk_biz_name="dba",
        )
        yield app
        app.delete()


# 全局初始化规格信息 -- 自动创建
@pytest.fixture(scope="session", autouse=True)
def init_spec(django_db_setup, django_db_blocker):
    n = 10
    specs = [
        Spec(**copy.deepcopy(INIT_SPEC_DATA), spec_id=spec_id, spec_name=f"test_spec_{spec_id}")
        for spec_id in range(1, n + 1)
    ]
    with django_db_blocker.unblock():
        Spec.objects.all().delete()
        Spec.objects.bulk_create(specs)
        yield
        Spec.objects.all().delete()


# 全局初始化机器信息 -- 自动创建
@pytest.fixture(scope="session", autouse=True)
def init_machine(django_db_setup, django_db_blocker):
    n = 10
    machines = [
        Machine(**copy.deepcopy(INIT_MACHINE_DATA), bk_host_id=host_id, ip=f"1.1.1.{host_id}")
        for host_id in range(1, n + 1)
    ]
    with django_db_blocker.unblock():
        Machine.objects.bulk_create(machines)
        yield
        Machine.objects.all().delete()


mark_global_skip = pytest.mark.skipif(os.environ.get("GLOBAL_SKIP") == "true", reason="disable in landun WIP")
