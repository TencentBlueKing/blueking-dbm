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

from backend.db_services.mysql.resources.tendbsingle import views
from backend.tests.conftest import mark_global_skip
from backend.tests.mock_data.components.cc import CCApiMock
from backend.utils.pytest import AuthorizedAPIRequestFactory

pytestmark = pytest.mark.django_db

factory = AuthorizedAPIRequestFactory()


@mark_global_skip
class TestDBSingleResources:
    def __init__(self):
        patch.object(settings, "MIDDLEWARE", [])

    @patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock())
    @patch.object(views.DBSingleViewSet, "get_permissions", lambda x: [])
    def test_list(self, dbsingle_cluster, dbsingle_module, bk_biz_id, dbsingle_machine_ip_list):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/tendbsingle_resources/",
        )
        view = views.DBSingleViewSet.as_view({"get": "list"})
        response = view(request, bk_biz_id=bk_biz_id)
        data = response.data
        assert data["count"] == 1
        assert set([m["ip"] for m in data["results"][0]["masters"]]) == set(dbsingle_machine_ip_list)
        assert data["results"][0]["db_module_name"] == dbsingle_module.db_module_name

        all_fields = set([field["key"] for field in views.DBSingleViewSet.query_class.fields])
        result_fields = set(data["results"][0])
        assert all_fields.issubset(result_fields)

    @patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock())
    @patch.object(views.DBSingleViewSet, "get_permissions", lambda x: [])
    def test_list_by_ip(self, dbsingle_cluster, bk_biz_id, dbsingle_machine_ip_list):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/tendbsingle_resources/?ip={dbsingle_machine_ip_list[0]}",
        )
        view = views.DBSingleViewSet.as_view({"get": "list"})
        response = view(request, bk_biz_id=bk_biz_id)
        data = response.data
        assert data["count"] == 1

    @patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock())
    @patch.object(views.DBSingleViewSet, "get_permissions", lambda x: [])
    def test_retrieve(self, dbsingle_cluster, dbsingle_module, bk_biz_id, dbsingle_machine_ip_list):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/tendbsingle_resources/{dbsingle_cluster.id}/",
        )
        view = views.DBSingleViewSet.as_view({"get": "retrieve"})
        response = view(request, bk_biz_id=bk_biz_id, cluster_id=dbsingle_cluster.id)
        data = response.data
        assert set([m["ip"] for m in data["masters"]]) == set(dbsingle_machine_ip_list)
        assert data["db_module_name"] == dbsingle_module.db_module_name

    @patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock())
    @patch.object(views.DBSingleViewSet, "get_permissions", lambda x: [])
    def test_get_table_fields(self, bk_biz_id):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/tendbsingle_resources/get_table_fields/",
        )
        view = views.DBSingleViewSet.as_view({"get": "get_table_fields"})
        response = view(request, bk_biz_id=bk_biz_id)
        data = response.data
        assert data == views.DBSingleViewSet.query_class.fields
