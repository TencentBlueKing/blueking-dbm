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
from unittest.mock import patch

import mock
import pytest
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from backend.configuration.constants import DBType
from backend.db_meta.api.cluster.tendbha.handler import TenDBHAClusterHandler
from backend.db_meta.models import AppCache, BKCity, DBModule, LogicalCity, Spec
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.tests.mock_data import constant
from backend.tests.mock_data.components.cc import CCInitMock
from backend.tests.mock_data.constant import INIT_SPEC_DATA, INIT_TENDBHA_CREATE_API_DATA


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


# 全局初始化city信息
@pytest.fixture(scope="session", autouse=True)
def __init_city(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        LogicalCity.objects.get_or_create(id=1, defaults={"name": "南京"})
        LogicalCity.objects.get_or_create(id=2, defaults={"name": "上海"})
        BKCity.objects.create(logical_city_id=1, bk_idc_city_id=1, bk_idc_city_name="南京")
        BKCity.objects.create(logical_city_id=1, bk_idc_city_id=2, bk_idc_city_name="仪征")
        BKCity.objects.create(logical_city_id=2, bk_idc_city_id=3, bk_idc_city_name="上海")
        yield
        BKCity.objects.all().delete()
        LogicalCity.objects.all().delete()


# 全局初始化package信息.
# 目前仅有mysql，后续如果其他集群需要pkg信息则往这里补充
@pytest.fixture(scope="session", autouse=True)
def __init_package(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        fake_pkg_info = {"version": "latest", "path": "", "size": 0, "md5": ""}
        packages = [
            {"name": "pk-1", "pkg_type": PackageType.MySQL, "db_type": DBType.MySQL, **fake_pkg_info},
            {"name": "pk-2", "pkg_type": PackageType.MySQLProxy, "db_type": DBType.MySQL, **fake_pkg_info},
        ]
        Package.objects.bulk_create([Package(**data) for data in packages])
        yield
        Package.objects.all().delete()


# 全局初始化模块信息
@pytest.fixture(scope="session", autouse=True)
def __init_db_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        DBModule.objects.create(
            db_module_id=constant.DB_MODULE_ID,
            bk_biz_id=constant.BK_BIZ_ID,
            db_module_name="test",
        )
        yield
        DBModule.objects.all().delete()


# 全局初始化AppCache信息
@pytest.fixture(scope="session", autouse=True)
def __init_app(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        app = AppCache.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            db_app_abbr="DBA",
            bk_biz_name="dba",
        )
        yield app
        app.delete()


# 全局初始化规格信息
@pytest.fixture(scope="session", autouse=True)
def __init_spec(django_db_setup, django_db_blocker):
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


# 初始化Mysql集群信息
@pytest.fixture
def init_mysql_cluster():
    ip_dict = {
        "new_master_ip": "1.1.1.1",
        "new_slave_ip": "1.1.1.2",
        "new_proxy_1_ip": "1.1.1.3",
        "new_proxy_2_ip": "1.1.1.4",
    }
    clusters = [
        {
            "name": constant.INIT_MYSQL_CLUSTER_NAME,
            "master": f"{constant.INIT_MYSQL_CLUSTER_NAME}.dba.db",
            "slave": f"{constant.INIT_MYSQL_CLUSTER_NAME}.dba.dr",
            "mysql_port": 20000,
            "proxy_port": 10000,
        }
    ]
    with (
        patch("backend.db_meta.api.cluster.tendbha.handler.MysqlCCTopoOperator", CCInitMock),
        patch("backend.db_meta.api.machine.apis.CCApi", CCInitMock),
    ):
        TenDBHAClusterHandler.create(**INIT_TENDBHA_CREATE_API_DATA, clusters=clusters, cluster_ip_dict=ip_dict)


mark_global_skip = pytest.mark.skipif(os.environ.get("GLOBAL_SKIP") == "true", reason="disable in landun WIP")
