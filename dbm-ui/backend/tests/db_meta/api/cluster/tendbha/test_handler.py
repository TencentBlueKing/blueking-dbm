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

from backend.constants import DEFAULT_TIME_ZONE
from backend.db_meta.api.cluster.tendbha.handler import TenDBHAClusterHandler
from backend.db_meta.models import Cluster, ClusterEntry
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc
from backend.tests.mock_data.components.cc import CCApiMock

pytestmark = pytest.mark.django_db


class TestHandler:
    @patch("backend.db_meta.api.db_module.apis.CCApi", CCApiMock())
    @patch("backend.db_meta.api.machine.apis.CCApi", CCApiMock())
    @patch("backend.db_meta.api.cluster.tendbha.create_cluster.CCApi", CCApiMock())
    @patch("backend.db_meta.api.common.common.CCApi", CCApiMock())
    @patch("backend.db_meta.api.cluster.tendbha.handler.create_bk_module_for_cluster_id", lambda **kwargs: None)
    @patch("backend.db_meta.api.cluster.tendbha.handler.transfer_host_in_cluster_module", lambda **kwargs: None)
    def test_create_success(self, init_db_module, create_city):
        cluster_name = "test"
        clusters = [
            {
                "name": cluster_name,
                "master": "db-module-name-db.cluster-name.bk-app-abbr.db",
                "slave": "db-module-name-dr.cluster-name.bk-app-abbr.db",
                "mysql_port": 20000,
                "proxy_port": 10000,
            }
        ]
        cluster_ip_dict = {
            "new_master_ip": cc.NORMAL_IP3,
            "new_slave_ip": cc.NORMAL_IP4,
            "new_proxy_1_ip": cc.NORMAL_IP,
            "new_proxy_2_ip": cc.NORMAL_IP2,
        }
        TenDBHAClusterHandler.create(
            **{
                "bk_biz_id": constant.BK_BIZ_ID,
                "db_module_id": constant.DB_MODULE_ID,
                "cluster_ip_dict": cluster_ip_dict,
                "clusters": clusters,
                "creator": "",
                "major_version": "MySQL-5.7",
                "time_zone": DEFAULT_TIME_ZONE,
                "bk_cloud_id": 0,
            }
        )
        assert Cluster.objects.filter(name=cluster_name).exists()
        cluster = Cluster.objects.get(name=cluster_name)
        assert cluster.storageinstance_set.count() == 2
        assert cluster.proxyinstance_set.count() == 2

        assert ClusterEntry.objects.filter(entry=clusters[0]["master"], cluster=cluster).exists()
        assert ClusterEntry.objects.filter(entry=clusters[0]["slave"], cluster=cluster).exists()

        master_entry = ClusterEntry.objects.get(entry=clusters[0]["master"], cluster=cluster)
        assert master_entry.proxyinstance_set.count() == 2

        slave_entry = ClusterEntry.objects.get(entry=clusters[0]["slave"], cluster=cluster)
        assert slave_entry.storageinstance_set.count() == 1
