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

from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.tests.mock_data.components import cc
from backend.tests.mock_data.components.dbconfig import DBConfigApiMock
from backend.tests.mock_data.components.dbpriv_manager import DBPrivManagerApiMock
from backend.tests.mock_data.constant import BK_BIZ_ID

pytestmark = pytest.mark.django_db


class TestHandler:
    @patch("backend.db_meta.api.cluster.base.handler.DBConfigApi", DBConfigApiMock)
    @patch("backend.db_meta.api.cluster.base.handler.DBPrivManagerApi", DBPrivManagerApiMock)
    def test_import_meta_mysql_on_k8s(self):
        immute_domain = "localhost"
        ClusterHandler.import_meta(
            {
                "cluster_info": {
                    "name": "cluster-name",
                    "alias": "",
                    "bk_biz_id": BK_BIZ_ID,
                    "cluster_type": ClusterType.MySQLOnK8S,
                    "immute_domain": immute_domain,
                    "major_version": "MySQL-5.7",
                },
                "cluster_entries": [
                    {
                        "entry": immute_domain,
                        "cluster_entry_type": ClusterEntryType.K8SService.value,
                        "access_port": 3306,
                    }
                ],
                "storage_instances": [],
                "proxy_instances": [],
                "db_configs": [
                    {
                        "conf_file": "",
                        "conf_type": "",
                        "namespace": "",
                        "config_map": {"conf_name": "", "conf_value": ""},
                    }
                ],
                "account": {
                    "instances": [{"domain": immute_domain}, {"ip": cc.NORMAL_IP2}],
                    "username": settings.DATABASES["default"]["USER"],
                    "password": settings.DATABASES["default"]["PASSWORD"],
                    "component": "mysql",
                },
            }
        )
        assert Cluster.objects.filter(cluster_type=ClusterType.MySQLOnK8S, immute_domain=immute_domain).exists()
        assert ClusterEntry.objects.filter(entry=immute_domain).exists()
