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
import pytest
from mock.mock import patch

from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.tests.mock_data.components.db_remote_service import DbRemoteServiceApiMock

pytestmark = pytest.mark.django_db


class TestRemoteServiceHandler:
    @patch("backend.db_services.mysql.remote_service.handlers.DRSApi", DbRemoteServiceApiMock())
    def test_dbsingle_show_databases(self, bk_biz_id, dbsingle_cluster, dbha_cluster):
        results = RemoteServiceHandler(bk_biz_id=bk_biz_id).show_databases(
            cluster_ids=[dbsingle_cluster.id, dbha_cluster.id]
        )
        for result in results:
            if result["cluster_id"] == dbsingle_cluster.id:
                assert len(result["databases"]) > 0
            if result["cluster_id"] == dbha_cluster.id:
                assert len(result["databases"]) == 0
