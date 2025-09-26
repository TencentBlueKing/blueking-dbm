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
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_monitor.constants import AlertLevelEnum
from backend.db_monitor.views.subscribe import MonitorSubscribeViewSet
from backend.tests.mock_data.db_monitor.bkmonitorv3 import BKMonitorV3MockApi

pytestmark = pytest.mark.django_db

client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)
def set_empty_middleware():
    """设置空的中间件，避免权限检查干扰测试"""
    with patch.object(settings, "MIDDLEWARE", []):
        yield


# 测试集群数据
TEST_CLUSTER_DATA = {
    "id": 1,
    "name": "test-cluster",
    "immute_domain": "test.cluster.db",
    "cluster_type": ClusterType.TenDBHA.value,
    "bk_biz_id": 2,
    "region": "default",
    "creator": "admin",
    "updater": "admin",
}

SPIDER_CLUSTER_DATA = {
    "id": 2,
    "name": "spider-cluster",
    "immute_domain": "spider.xiaogtest.xxxx.db",
    "cluster_type": ClusterType.TenDBHA.value,
    "bk_biz_id": 2,
    "region": "default",
    "creator": "admin",
    "updater": "admin",
}


@pytest.fixture(scope="class", autouse=True)
def setup_test_clusters(django_db_setup, django_db_blocker):
    """初始化测试集群数据"""
    with django_db_blocker.unblock():
        # 创建测试集群
        Cluster.objects.create(**TEST_CLUSTER_DATA)
        Cluster.objects.create(**SPIDER_CLUSTER_DATA)
        yield
        # 清理测试数据
        Cluster.objects.filter(immute_domain__in=["test.cluster.db", "spider.xiaogtest.xxxx.db"]).delete()


@pytest.fixture
def mock_system_settings():
    """模拟系统设置中的订阅指标配置"""
    metric_config = {
        ClusterType.TenDBHA.value: [
            "bk_monitor.dbm_system.cpu.pct_used",
            "bk_monitor.dbm_system.mem.pct_used",
            "bk_monitor.dbm_system.disk.pct_used",
        ]
    }
    with patch.object(SystemSettings, "get_setting_value") as mock_get_setting:
        mock_get_setting.return_value = metric_config
        yield mock_get_setting


class TestMonitorSubscribeViewSet:
    """监控订阅视图集测试类"""

    @patch.object(MonitorSubscribeViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorSubscribeViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.views.subscribe.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_save_subscribe_success(self, mock_system_settings):
        """测试保存告警订阅成功"""
        url = "/apis/monitor/subscribe/save_subscribe/"
        data = {
            "clusters": [
                {"cluster_type": ClusterType.TenDBHA.value, "cluster_domain": "cluster-0.test.db"},
                {"cluster_type": ClusterType.TenDBHA.value, "cluster_domain": "cluster-xxx.test.db"},
            ],
            "bk_biz_id": 2,
            "alert_level": AlertLevelEnum.HIGH.value,
            "notice_ways": ["weixin", "mail"],
        }

        response = client.post(url, data=data, format="json")
        assert response.status_code == status.HTTP_200_OK

    @patch.object(MonitorSubscribeViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorSubscribeViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.views.subscribe.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_delete_subscribe_success(self):
        """测试删除告警订阅成功"""
        url = "/apis/monitor/subscribe/delete_subscribe/"
        data = {"ids": [1, 2, 3]}

        response = client.post(url, data=data, format="json")
        assert response.status_code == status.HTTP_200_OK

    @patch.object(MonitorSubscribeViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorSubscribeViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.views.subscribe.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_list_subscribe(self, mock_system_settings):
        url = "/apis/monitor/subscribe/list_subscribe/"
        data = {"page": 1, "page_size": 10}

        response = client.get(url, data=data, format="json")
        assert response.status_code == status.HTTP_200_OK
