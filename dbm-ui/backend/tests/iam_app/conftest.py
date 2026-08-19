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
import random

import pytest
from django.utils.crypto import get_random_string
from rest_framework.test import APIRequestFactory

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache
from backend.tests.mock_data import constant


@pytest.fixture
def test_username():
    """提供测试用户名"""
    return "test_user"


@pytest.fixture
def mock_request_factory():
    """提供Django Request Factory"""
    return APIRequestFactory()


@pytest.fixture
def mock_request(mock_request_factory, test_username):
    """创建Mock请求对象"""
    request = mock_request_factory.get("/")
    request.user = type("User", (), {"username": test_username, "is_superuser": False})()
    return request


@pytest.fixture
def test_app_cache():
    """创建测试业务缓存"""
    app_cache, created = AppCache.objects.get_or_create(
        bk_biz_id=constant.BK_BIZ_ID,
        defaults={
            "bk_biz_name": "DBA",
            "db_app_abbr": "DBA",
        },
    )
    yield app_cache
    # 只删除新创建的
    if created:
        app_cache.delete()


@pytest.fixture
def test_bk_biz_id():
    """提供测试业务ID"""
    return constant.BK_BIZ_ID


@pytest.fixture
def test_cluster_module(test_bk_biz_id):
    """创建测试集群模块"""
    from backend.db_meta.models import DBModule

    module, created = DBModule.objects.get_or_create(
        db_module_id=constant.DB_MODULE_ID,
        defaults={
            "bk_biz_id": test_bk_biz_id,
            "db_module_name": "test_module",
            "cluster_type": ClusterType.TenDBHA,
        },
    )
    yield module
    if created:
        module.delete()


@pytest.fixture
def test_city():
    """创建测试城市"""
    from backend.db_meta.models import city_map

    logic_city = city_map.LogicalCity.objects.create(name="测试城市")
    bk_city = city_map.BKCity.objects.create(
        bk_idc_city_id=random.randint(1000000, 9999999),
        bk_idc_city_name="测试城市",
        logical_city=logic_city,
    )
    yield bk_city
    bk_city.delete()
    logic_city.delete()


@pytest.fixture
def test_cluster_for_iam(test_bk_biz_id, test_cluster_module, test_city):
    """创建用于IAM测试的集群"""
    from backend.db_meta.models import Cluster

    cluster_name = get_random_string(6)
    cluster = Cluster.objects.create(
        id=1,  # 使用固定ID以便测试
        name=cluster_name,
        cluster_type=ClusterType.TenDBHA,
        immute_domain=f"test.{cluster_name}.db",
        bk_biz_id=test_bk_biz_id,
        db_module_id=test_cluster_module.db_module_id,
    )
    yield cluster
    cluster.delete()


@pytest.fixture
def mock_iam_backend():
    """
    提供Mock的鉴权后端。
    Permission 的鉴权调用都经由 backend，直接替换 Permission._iam 已不生效
    """
    from unittest.mock import MagicMock

    from backend.iam_app.handlers.backends.base import IAMBackend

    backend = MagicMock(spec=IAMBackend)
    backend.is_allowed.return_value = True
    backend.policy_query.side_effect = lambda username, action, obj_list: list(obj_list)
    backend.grant_creator_actions.return_value = (True, "success")
    return backend


@pytest.fixture
def mock_iam_client():
    """提供Mock的IAM客户端，用于尚未下沉到后端的能力（申请链接、系统信息等）"""
    from unittest.mock import MagicMock

    from iam import DummyIAM

    from backend import env

    mock_client = MagicMock(spec=DummyIAM)
    mock_client.is_allowed.return_value = True
    mock_client.batch_is_allowed.return_value = {}
    mock_client.resource_multi_actions_allowed.return_value = {}
    mock_client._do_policy_query.return_value = MagicMock(to_dict=lambda: {"condition": []})
    mock_client.get_apply_url.return_value = (True, "", "http://apply.url")
    mock_client.grant_resource_creator_actions.return_value = (True, "success")
    mock_client.grant_resource_creator_action_attributes.return_value = (True, "success")
    mock_client._client = MagicMock()
    mock_client._client.query.return_value = (True, "", {"id": env.BK_IAM_SYSTEM_ID, "name": "DB管理"})
    return mock_client
