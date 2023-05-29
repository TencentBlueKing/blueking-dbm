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

from backend.db_services.mysql.resources.tendbha import views
from backend.tests.conftest import mark_global_skip
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.gse import GseApiMock
from backend.utils.pytest import AuthorizedAPIRequestFactory

pytestmark = pytest.mark.django_db

factory = AuthorizedAPIRequestFactory()


@mark_global_skip
class TestDBHAResources:
    def __init__(self):
        patch.object(settings, "MIDDLEWARE", [])

    @patch("backend.db_services.ipchooser.handlers.host_handler.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.handlers.base.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.query.resource.GseApi", GseApiMock())
    @patch.object(views.DBHAViewSet, "get_permissions", lambda x: [])
    def test_list(self, dbha_cluster, bk_biz_id, dbha_master_ip, dbha_slave_ip, dbha_proxy_ip_list):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/tendbha_resources/",
        )
        view = views.DBHAViewSet.as_view({"get": "list"})
        response = view(request, bk_biz_id=bk_biz_id)
        data = response.data
        assert data["count"] == 1

        first_item = data["results"][0]
        assert {m["ip"] for m in first_item["masters"]} == {dbha_master_ip}
        assert {s["ip"] for s in first_item["slaves"]} == {dbha_slave_ip}
        assert {p["ip"] for p in first_item["proxies"]} == set(dbha_proxy_ip_list)
        assert first_item["slave_domain"] == f"slave-{dbha_cluster.immute_domain}"

        all_fields = set([field["key"] for field in views.DBHAViewSet.query_class.fields])
        result_fields = set(data["results"][0])
        assert all_fields.issubset(result_fields)

    @patch("backend.db_services.ipchooser.handlers.host_handler.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.handlers.base.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.query.resource.GseApi", GseApiMock())
    @patch.object(views.DBHAViewSet, "get_permissions", lambda x: [])
    def test_list_by_ip(self, dbha_cluster, bk_biz_id, dbha_master_ip, dbha_slave_ip, dbha_proxy_ip_list):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/tendbha_resources/?ip={dbha_master_ip}",
        )
        view = views.DBHAViewSet.as_view({"get": "list"})
        response = view(request, bk_biz_id=bk_biz_id)
        data = response.data
        assert data["count"] == 1

    @patch("backend.db_services.ipchooser.handlers.host_handler.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.handlers.base.CCApi", CCApiMock())
    @patch("backend.db_services.ipchooser.query.resource.GseApi", GseApiMock())
    @patch.object(views.DBHAViewSet, "get_permissions", lambda x: [])
    def test_retrieve(self, dbha_cluster, bk_biz_id, dbha_master_ip, dbha_proxy_ip_list):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/tendbha_resources/{dbha_cluster.id}/",
        )
        view = views.DBHAViewSet.as_view({"get": "retrieve"})
        response = view(request, bk_biz_id=bk_biz_id, cluster_id=dbha_cluster.id)
        data = response.data
        assert {m["ip"] for m in data["masters"]} == {dbha_master_ip}
        assert {p["ip"] for p in data["proxies"]} == set(dbha_proxy_ip_list)
        assert data["slave_domain"] == f"slave-{dbha_cluster.immute_domain}"

    @patch.object(views.DBHAViewSet, "get_permissions", lambda x: [])
    def test_get_table_fields(self, bk_biz_id):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/tendbha_resources/get_table_fields/",
        )
        view = views.DBHAViewSet.as_view({"get": "get_table_fields"})
        response = view(request, bk_biz_id=bk_biz_id)
        data = response.data
        assert data == views.DBHAViewSet.query_class.fields
