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

from backend.db_services.mysql.resources import views
from backend.utils.pytest import AuthorizedAPIRequestFactory

pytestmark = pytest.mark.django_db

factory = AuthorizedAPIRequestFactory()


class TestListResource:
    @patch.object(views.ListResourceViewSet, "get_permissions", lambda x: [])
    def test_list(self, dbsingle_cluster, dbha_cluster, bk_biz_id, dbsingle_module):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/resources/?db_module_id={dbsingle_module.db_module_id}",
        )
        view = views.ListResourceViewSet.as_view({"get": "list"})
        response = view(request, bk_biz_id=bk_biz_id)
        data = response.data
        assert len(data) == 1

    @patch.object(views.ListResourceViewSet, "get_permissions", lambda x: [])
    def test_list_no_data(self, dbha_cluster, bk_biz_id, dbsingle_module):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/resources/?db_module_id={dbsingle_module.db_module_id}",
        )
        view = views.ListResourceViewSet.as_view({"get": "list"})
        response = view(request, bk_biz_id=bk_biz_id)
        data = response.data
        assert len(data) == 0


class TestResourceTree:
    @patch.object(views.ResourceTreeViewSet, "get_permissions", lambda x: [])
    def test_get_tree(self, bk_biz_id, dbsingle_cluster):
        request = factory.get(
            f"/apis/mysql/bizs/{bk_biz_id}/resource_tree/?cluster_type={dbsingle_cluster.cluster_type}"
        )
        view = views.ResourceTreeViewSet.as_view({"get": "get_resource_tree"})
        response = view(request, bk_biz_id=bk_biz_id)
        data = response.data
        assert data[0]["children"][0]["extra"]["domain"] == dbsingle_cluster.immute_domain
