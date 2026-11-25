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
import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache.backends.locmem import LocMemCache
from django.urls import resolve
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.plugin.constants import SubscribeAggregateType
from backend.db_services.plugin.monitor import handlers
from backend.db_services.plugin.monitor.handlers import SubscribeRelationHandler
from backend.db_services.plugin.monitor.serializers import ListSubscribeRelationsSerializer
from backend.db_services.plugin.monitor.views import MonitorSubscribeOpenViewSet
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission

pytestmark = pytest.mark.django_db

User = get_user_model()

MYSQL_DOMAIN = "mysql.subscribe.test.db"
REDIS_DOMAIN = "redis.subscribe.test.db"
DELETED_DOMAIN = "deleted.subscribe.test.db"

BIZ_MAP = {"2": {"bk_biz_name": "biz-a"}, "3": {"bk_biz_name": "biz-b"}}


def _subscribe(username, domain=None):
    conditions = [{"field": "alert.severity", "value": [1], "method": "eq", "condition": "and"}]
    if domain:
        conditions.append({"field": "tags.cluster_domain", "value": [domain], "method": "eq", "condition": "and"})
    return {"id": 1, "username": username, "conditions": conditions, "user_type": "follower"}


MOCK_SUBSCRIBES = [
    _subscribe("alice", MYSQL_DOMAIN),
    _subscribe("bob", MYSQL_DOMAIN),
    _subscribe("alice", REDIS_DOMAIN),
    # 同一账号对同一集群的重复订阅，只保留一条
    _subscribe("alice", MYSQL_DOMAIN),
    # 集群已下架，不应出现在结果中
    _subscribe("carol", DELETED_DOMAIN),
    # 缺少集群条件的脏数据，直接忽略
    _subscribe("dave"),
]


@pytest.fixture
def clusters():
    common = {"region": "default", "creator": "admin", "updater": "admin"}
    Cluster.objects.create(
        name="mysql", immute_domain=MYSQL_DOMAIN, cluster_type=ClusterType.TenDBHA.value, bk_biz_id=2, **common
    )
    Cluster.objects.create(
        name="redis",
        immute_domain=REDIS_DOMAIN,
        cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
        bk_biz_id=3,
        **common,
    )


@pytest.fixture
def local_cache():
    local = LocMemCache("subscribe-relations-test", {})
    local.clear()
    with patch.object(handlers, "cache", local):
        yield local


@pytest.fixture
def mock_subscribes():
    with patch.object(handlers.BKMonitorV3Api, "list_full_subscribe", return_value=MOCK_SUBSCRIBES) as mocked, patch(
        "backend.db_meta.models.AppCache.get_appcache", return_value=BIZ_MAP
    ):
        yield mocked


@pytest.mark.usefixtures("clusters", "local_cache")
class TestSubscribeRelationHandler:
    def test_build_relations(self, mock_subscribes):
        relations = SubscribeRelationHandler.list_relations()

        assert sorted(relations, key=lambda r: (r["username"], r["cluster_domain"])) == [
            {"cluster_domain": MYSQL_DOMAIN, "bk_biz_name": "biz-a", "db_type": "mysql", "username": "alice"},
            {"cluster_domain": REDIS_DOMAIN, "bk_biz_name": "biz-b", "db_type": "redis", "username": "alice"},
            {"cluster_domain": MYSQL_DOMAIN, "bk_biz_name": "biz-a", "db_type": "mysql", "username": "bob"},
        ]

    @pytest.mark.parametrize(
        "filters, expected",
        [
            ({"bk_biz_name": "biz-b"}, {("alice", REDIS_DOMAIN)}),
            ({"db_types": ["mysql"]}, {("alice", MYSQL_DOMAIN), ("bob", MYSQL_DOMAIN)}),
            (
                {"db_types": ["mysql", "redis"]},
                {("alice", MYSQL_DOMAIN), ("bob", MYSQL_DOMAIN), ("alice", REDIS_DOMAIN)},
            ),
            ({"cluster_domain": "redis.subscribe"}, {("alice", REDIS_DOMAIN)}),
            ({"username": "bo"}, {("bob", MYSQL_DOMAIN)}),
            ({"username": "alice", "db_types": ["redis"]}, {("alice", REDIS_DOMAIN)}),
            ({"bk_biz_name": "", "cluster_domain": "", "username": ""}, None),
        ],
    )
    def test_filters(self, mock_subscribes, filters, expected):
        relations = SubscribeRelationHandler.list_relations(**filters)

        if expected is None:
            assert len(relations) == 3
        else:
            assert {(r["username"], r["cluster_domain"]) for r in relations} == expected

    def test_biz_name_with_int_keys(self, mock_subscribes):
        # appcache_dict 未命中缓存、直接从 DB 构建时 key 为 int
        int_key_biz_map = {int(bk_biz_id): biz for bk_biz_id, biz in BIZ_MAP.items()}
        with patch("backend.db_meta.models.AppCache.get_appcache", return_value=int_key_biz_map):
            relations = SubscribeRelationHandler.list_relations()

        assert {r["bk_biz_name"] for r in relations} == {"biz-a", "biz-b"}

    def test_aggregate_by_cluster(self, mock_subscribes):
        relations = SubscribeRelationHandler.list_relations(aggregate=SubscribeAggregateType.CLUSTER)

        assert relations == [
            {
                "cluster_domain": MYSQL_DOMAIN,
                "bk_biz_name": "biz-a",
                "db_type": "mysql",
                "subscribers": "alice,bob",
                "subscriber_count": 2,
            },
            {
                "cluster_domain": REDIS_DOMAIN,
                "bk_biz_name": "biz-b",
                "db_type": "redis",
                "subscribers": "alice",
                "subscriber_count": 1,
            },
        ]

    def test_aggregate_by_account(self, mock_subscribes):
        relations = SubscribeRelationHandler.list_relations(aggregate=SubscribeAggregateType.ACCOUNT)

        assert relations == [
            {"username": "alice", "cluster_count": 2, "clusters": f"{MYSQL_DOMAIN},{REDIS_DOMAIN}"},
            {"username": "bob", "cluster_count": 1, "clusters": MYSQL_DOMAIN},
        ]

    def test_filter_before_aggregate(self, mock_subscribes):
        by_cluster = SubscribeRelationHandler.list_relations(
            username="alice", aggregate=SubscribeAggregateType.CLUSTER
        )
        by_account = SubscribeRelationHandler.list_relations(
            db_types=["mysql"], aggregate=SubscribeAggregateType.ACCOUNT
        )

        assert [(r["cluster_domain"], r["subscribers"]) for r in by_cluster] == [
            (MYSQL_DOMAIN, "alice"),
            (REDIS_DOMAIN, "alice"),
        ]
        assert by_account == [
            {"username": "alice", "cluster_count": 1, "clusters": MYSQL_DOMAIN},
            {"username": "bob", "cluster_count": 1, "clusters": MYSQL_DOMAIN},
        ]

    def test_relations_cached(self, mock_subscribes):
        SubscribeRelationHandler.list_relations()
        SubscribeRelationHandler.list_relations(username="alice")

        assert mock_subscribes.call_count == 1

    def test_empty_result_cached(self, local_cache):
        with patch.object(handlers.BKMonitorV3Api, "list_full_subscribe", return_value=[]) as mocked:
            assert SubscribeRelationHandler.list_relations() == []
            assert SubscribeRelationHandler.list_relations() == []

        assert mocked.call_count == 1


class TestListSubscribeRelationsSerializer:
    def test_db_types_split(self):
        slz = ListSubscribeRelationsSerializer(data={"db_types": "mysql, redis,,"})
        assert slz.is_valid(), slz.errors
        assert slz.validated_data["db_types"] == ["mysql", "redis"]

    def test_blank_params(self):
        slz = ListSubscribeRelationsSerializer(
            data={"bk_biz_name": "", "db_types": "", "username": "", "aggregate": ""}
        )
        assert slz.is_valid(), slz.errors
        assert slz.validated_data["db_types"] == []

    def test_invalid_aggregate(self):
        slz = ListSubscribeRelationsSerializer(data={"aggregate": "biz"})
        assert not slz.is_valid()
        assert "aggregate" in slz.errors


@pytest.mark.usefixtures("clusters", "local_cache", "mock_subscribes")
class TestMonitorSubscribeOpenViewSet:
    url = "/apis/plugin/monitor/subscribe/relations/"

    def _request(self, is_jwt, has_platform_manage, params=None):
        request = APIRequestFactory().get(self.url, params or {})
        request.is_bk_jwt = lambda: is_jwt
        force_authenticate(request, user=User(username="normal_user"))
        with patch.object(ResourceActionPermission, "has_permission", return_value=has_platform_manage):
            return resolve(self.url).func(request)

    @staticmethod
    def _assert_forbidden(response):
        # drf_exception_handler 将权限异常包装为 HTTP 200，错误码放在响应体中
        body = json.loads(response.content)
        assert body["result"] is False
        assert str(body["code"]).endswith(str(status.HTTP_403_FORBIDDEN))

    def test_route_and_permissions(self):
        view = resolve(self.url).func
        assert view.cls is MonitorSubscribeOpenViewSet
        assert not getattr(view, "login_exempt", False)

        perm = MonitorSubscribeOpenViewSet.default_permission_class[0]
        assert isinstance(perm, ResourceActionPermission)
        assert [action.id for action in perm.actions] == [ActionEnum.PLATFORM_MANAGE.id]

    def test_platform_manager_via_jwt(self):
        response = self._request(is_jwt=True, has_platform_manage=True, params={"db_types": "redis"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [
            {"cluster_domain": REDIS_DOMAIN, "bk_biz_name": "biz-b", "db_type": "redis", "username": "alice"}
        ]

    def test_aggregate_param(self):
        response = self._request(is_jwt=True, has_platform_manage=True, params={"aggregate": "account"})

        assert response.status_code == status.HTTP_200_OK
        assert [r["username"] for r in response.data] == ["alice", "bob"]

    def test_reject_without_platform_manage(self):
        self._assert_forbidden(self._request(is_jwt=True, has_platform_manage=False))

    def test_reject_non_jwt_request(self):
        self._assert_forbidden(self._request(is_jwt=False, has_platform_manage=True))
