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
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from backend.db_services.redis.toolbox import handlers as handlers_mod
from backend.db_services.redis.toolbox.handlers import ToolboxHandler
from backend.db_services.redis.toolbox.views import ToolboxViewSet

BIZ_ID = 3
TOOLBOX_ROOT = "/apis/redis/bizs/{}/toolbox/".format(BIZ_ID)

STORAGE_ITEMS = [
    {
        "db_version_id": 15,
        "version_name": "redis-7.2.5",
        "full_version": "7.2.5.0.0.0",
        "phase": "alpha",
        "series_name": "Redis-7",
        "recommend": False,
        "is_current": False,
    },
    {
        "db_version_id": 9,
        "version_name": "redis-6.2.14",
        "full_version": "6.2.14.0.0.0",
        "phase": "release",
        "series_name": "Redis-6",
        "recommend": True,
        "is_current": True,
    },
]
PROXY_ITEMS = [
    {
        "db_version_id": 21,
        "version_name": "predixy-1.4.3",
        "full_version": "1.4.3.0.0.0",
        "phase": "rc",
        "series_name": "Predixy-latest",
        "recommend": False,
        "is_current": False,
    }
]


@pytest.fixture
def api_client(db):
    user, _ = get_user_model().objects.get_or_create(username="admin")
    client = APIClient()
    client.force_authenticate(user=user)
    with patch.object(settings, "MIDDLEWARE", []), patch.object(ToolboxViewSet, "get_permissions", lambda self: []):
        yield client


@pytest.fixture
def stub_versions(monkeypatch):
    calls = []

    def storage(cluster_id, ip=None):
        calls.append(("storage", cluster_id, ip))
        return STORAGE_ITEMS

    def proxy(cluster_id, ip=None):
        calls.append(("proxy", cluster_id, ip))
        return PROXY_ITEMS

    monkeypatch.setattr(handlers_mod, "get_cluster_storage_versions_for_upgrade", storage)
    monkeypatch.setattr(handlers_mod, "get_cluster_proxy_version_for_upgrade", proxy)
    monkeypatch.setattr(handlers_mod, "get_cluster_redis_version", lambda cluster_id: "redis-6.2.7")
    monkeypatch.setattr(handlers_mod, "get_cluster_proxy_version", lambda cluster_id: ["predixy-1.4.0"])
    monkeypatch.setattr(handlers_mod, "get_redis_version_by_ip", lambda cluster_id, ip: "redis-6.2.7")
    monkeypatch.setattr(handlers_mod, "get_proxy_version_by_ip", lambda cluster_id, ip: "predixy-1.4.0")
    return calls


class TestHandler:
    def test_update_dispatches_by_node_type(self, stub_versions):
        assert ToolboxHandler.get_update_cluster_versions(1, "Backend") == STORAGE_ITEMS
        assert ToolboxHandler.get_update_cluster_versions(1, "Proxy") == PROXY_ITEMS
        assert ToolboxHandler.get_update_cluster_version_by_ip(1, "Backend", "1.1.1.1") == STORAGE_ITEMS
        assert ToolboxHandler.get_update_cluster_version_by_ip(1, "Proxy", "1.1.1.1") == PROXY_ITEMS
        assert stub_versions == [
            ("storage", 1, None),
            ("proxy", 1, None),
            ("storage", 1, "1.1.1.1"),
            ("proxy", 1, "1.1.1.1"),
        ]


@pytest.mark.usefixtures("stub_versions")
class TestGetClusterVersionsApi:
    @pytest.mark.parametrize("node_type, expected", [("Backend", STORAGE_ITEMS), ("Proxy", PROXY_ITEMS)])
    def test_update_returns_structured_items(self, api_client, node_type, expected):
        resp = api_client.get(
            TOOLBOX_ROOT + "get_cluster_versions/", {"cluster_id": 1, "node_type": node_type, "type": "update"}
        )

        assert resp.status_code == 200
        assert resp.json()["data"] == expected

    @pytest.mark.parametrize("node_type, expected", [("Backend", ["redis-6.2.7"]), ("Proxy", ["predixy-1.4.0"])])
    def test_online_returns_string_list(self, api_client, node_type, expected):
        resp = api_client.get(
            TOOLBOX_ROOT + "get_cluster_versions/", {"cluster_id": 1, "node_type": node_type, "type": "online"}
        )

        assert resp.status_code == 200
        assert resp.json()["data"] == expected


@pytest.mark.usefixtures("stub_versions")
class TestGetClusterVersionByIpApi:
    @pytest.mark.parametrize("node_type, expected", [("Backend", STORAGE_ITEMS), ("Proxy", PROXY_ITEMS)])
    def test_update_returns_structured_items(self, api_client, node_type, expected):
        resp = api_client.get(
            TOOLBOX_ROOT + "get_cluster_version_by_ip/",
            {"cluster_id": 1, "node_type": node_type, "type": "update", "ip": "1.1.1.1"},
        )

        assert resp.status_code == 200
        assert resp.json()["data"] == expected

    @pytest.mark.parametrize("node_type, expected", [("Backend", ["redis-6.2.7"]), ("Proxy", ["predixy-1.4.0"])])
    def test_online_returns_string_list(self, api_client, node_type, expected):
        resp = api_client.get(
            TOOLBOX_ROOT + "get_cluster_version_by_ip/",
            {"cluster_id": 1, "node_type": node_type, "type": "online", "ip": "1.1.1.1"},
        )

        assert resp.status_code == 200
        assert resp.json()["data"] == expected
