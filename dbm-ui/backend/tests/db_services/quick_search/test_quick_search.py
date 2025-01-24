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

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.enums import ClusterEntryRole, ClusterType
from backend.db_meta.models import Cluster, Machine
from backend.db_services.quick_search.views import QuickSearchViewSet
from backend.utils.pytest import AuthorizedAPIRequestFactory

pytestmark = pytest.mark.django_db

factory = AuthorizedAPIRequestFactory()

QUICK_SEARCH_CONTAINS_PARAMS = {
    "bk_biz_ids": [],
    "db_types": [],
    "resource_types": [],
    "filter_type": "CONTAINS",
    "keyword": None,
}

QUICK_SEARCH_EXACT_PARAMS = {
    "bk_biz_ids": [],
    "db_types": [],
    "resource_types": [],
    "filter_type": "EXACT",
    "keyword": None,
}


class TestQuickSearchViewSet:
    def _get_keyword(self, query, target_value):
        keyword = target_value
        if query.get("filter_type") == "CONTAINS":
            keyword = target_value[: len(target_value) - 1]
        return keyword

    def _request_quick_search(self, resource_list_mock, query):
        resource_list_mock.return_value = {"count": 0, "details": []}

        request = factory.post("/apis/quick_search/search/", data=query, format="json")
        quick_search_viewset = QuickSearchViewSet.as_view({"post": "search"})
        response = quick_search_viewset(request)
        return response

    # @pytest.mark.parametrize("query", [QUICK_SEARCH_CONTAINS_PARAMS, QUICK_SEARCH_EXACT_PARAMS])
    # @patch.object(DBResourceApi, "resource_list")
    # def test_quick_search_for_cluster_name(self, resource_list_mock, query, init_cluster):
    #     """
    #     测试搜索集群名称
    #     """
    #     target_value = init_cluster.name
    #     query["keyword"] = self._get_keyword(query, target_value)
    #     response = self._request_quick_search(resource_list_mock, query)
    #     assert response.status_code == 200
    #     result = [cluster.get("id") for cluster in response.data.get("cluster_name")]
    #     assert init_cluster.id in result

    @pytest.mark.parametrize("query", [QUICK_SEARCH_CONTAINS_PARAMS, QUICK_SEARCH_EXACT_PARAMS])
    @patch.object(DBResourceApi, "resource_list")
    def test_quick_search_for_entry(self, resource_list_mock, query, init_mysql_cluster):
        """
        测试搜索访问入口
        """
        cluster = Cluster.objects.filter(cluster_type=ClusterType.TenDBHA).first()
        target_value = cluster.immute_domain
        query["keyword"] = self._get_keyword(query, target_value)
        response = self._request_quick_search(resource_list_mock, query)
        assert response.status_code == 200
        result = [
            entry.get("entry")
            for entry in response.data.get("entry")
            if entry["role"] == ClusterEntryRole.MASTER_ENTRY
        ]
        assert cluster.immute_domain in result

    @pytest.mark.parametrize("query", [QUICK_SEARCH_CONTAINS_PARAMS, QUICK_SEARCH_EXACT_PARAMS])
    @patch.object(DBResourceApi, "resource_list")
    def test_quick_search_for_proxy_instance(self, resource_list_mock, query, init_proxy_instance):
        """
        测试搜索实例
        """
        target_value = init_proxy_instance.machine.ip
        query["keyword"] = self._get_keyword(query, target_value)
        response = self._request_quick_search(resource_list_mock, query)
        assert response.status_code == 200
        result = [cluster.get("ip") for cluster in response.data.get("instance")]
        assert init_proxy_instance.machine.ip in result

    @pytest.mark.parametrize("query", [QUICK_SEARCH_CONTAINS_PARAMS, QUICK_SEARCH_EXACT_PARAMS])
    @patch.object(DBResourceApi, "resource_list")
    def test_quick_search_for_storage_instance(self, resource_list_mock, query, init_storage_instance):
        """
        测试搜索存储实例
        """
        target_value = init_storage_instance.machine.ip
        query["keyword"] = self._get_keyword(query, target_value)
        response = self._request_quick_search(resource_list_mock, query)
        assert response.status_code == 200
        result = [cluster.get("ip") for cluster in response.data.get("instance")]
        assert init_storage_instance.machine.ip in result

    @pytest.mark.parametrize("query", [QUICK_SEARCH_EXACT_PARAMS])
    @patch.object(DBResourceApi, "resource_list")
    def test_quick_search_for_task(self, resource_list_mock, query, init_flow_tree):
        """
        测试搜索任务ID
        """
        target_value = init_flow_tree.root_id
        query["keyword"] = self._get_keyword(query, target_value)
        response = self._request_quick_search(resource_list_mock, query)
        assert response.status_code == 200
        result = [cluster.get("root_id") for cluster in response.data.get("task")]
        assert init_flow_tree.root_id in result

    @pytest.mark.parametrize("query", [QUICK_SEARCH_CONTAINS_PARAMS, QUICK_SEARCH_EXACT_PARAMS])
    @patch.object(DBResourceApi, "resource_list")
    def test_quick_search_for_machine(self, resource_list_mock, query, init_mysql_cluster):
        """
        测试搜索主机
        """
        target_value = Machine.objects.first().ip
        query["keyword"] = self._get_keyword(query, target_value)
        response = self._request_quick_search(resource_list_mock, query)
        assert response.status_code == 200
        # result = [cluster.get("ip") for cluster in response.data.get("machine")]
        # assert machine_fixture.ip in result

    @pytest.mark.parametrize("query", [QUICK_SEARCH_EXACT_PARAMS])
    @patch.object(DBResourceApi, "resource_list")
    def test_quick_search_for_ticket(self, resource_list_mock, query, init_ticket):
        """
        测试搜索单据
        """
        target_value = init_ticket.id
        query["keyword"] = self._get_keyword(query, target_value)
        response = self._request_quick_search(resource_list_mock, query)
        assert response.status_code == 200
        result = [cluster.get("id") for cluster in response.data.get("ticket")]
        assert init_ticket.id in result
