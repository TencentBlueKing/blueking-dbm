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
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.db_services.redis.resources.redis_cluster.views import RedisClusterViewSet
from backend.tests.mock_data import constant
from backend.tests.mock_data.iam_app.permission import PermissionMock

pytestmark = pytest.mark.django_db
client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)
def set_empty_middleware():
    """移除中间件"""
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.fixture(autouse=True)
def setup_permissions():
    """设置权限"""
    patch.object(RedisClusterViewSet, "permission_classes", [AllowAny]).start()
    patch.object(RedisClusterViewSet, "get_permissions", lambda x: []).start()
    patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
    yield


class TestRedisClusterViewSet:
    """测试Redis集群资源视图"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_class(self, django_db_blocker):
        """创建Redis测试集群"""
        with django_db_blocker.unblock():
            from backend.db_meta.models import BKCity

            # 获取或创建城市
            city = BKCity.objects.first()

            # 创建Redis集群
            cluster = Cluster.objects.create(
                id=1001,
                bk_biz_id=constant.BK_BIZ_ID,
                name="test_redis_cluster",
                alias="测试Redis集群",
                cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
                immute_domain="test.redis.db",
                db_module_id=111,
                bk_cloud_id=0,
                major_version="Redis-5.0",
            )

            # 创建机器 - 使用独特的IP避免冲突
            master_machine = Machine.objects.create(
                ip="10.10.10.1001",
                bk_host_id=20001,
                bk_biz_id=constant.BK_BIZ_ID,
                machine_type=MachineType.TENDISCACHE.value,
                bk_city=city,
            )

            proxy_machine = Machine.objects.create(
                ip="10.10.10.1002",
                bk_host_id=20002,
                bk_biz_id=constant.BK_BIZ_ID,
                machine_type=MachineType.TWEMPROXY.value,
                bk_city=city,
            )

            # 创建存储实例
            storage = StorageInstance.objects.create(
                machine=master_machine,
                port=30000,
                instance_role=InstanceRole.REDIS_MASTER.value,
                cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
            )
            storage.cluster.add(cluster)

            # 创建代理实例
            proxy = ProxyInstance.objects.create(
                cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
                machine=proxy_machine,
                port=50000,
            )
            proxy.cluster.add(cluster)

            yield

            # 清理数据
            ProxyInstance.objects.filter(machine__ip__in=["10.10.10.1002"]).delete()
            StorageInstance.objects.filter(machine__ip__in=["10.10.10.1001"]).delete()
            Cluster.objects.filter(id=1001).delete()
            Machine.objects.filter(ip__in=["10.10.10.1001", "10.10.10.1002"]).delete()

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_list_clusters(self, mock_search_cc_cloud):
        """测试获取集群列表"""
        mock_search_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        url = f"/apis/redis/bizs/{constant.BK_BIZ_ID}/redis_resources/?limit=10&offset=0"
        response = client.get(url)

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "count" in result["data"]
        assert "results" in result["data"]

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_retrieve_cluster(self, mock_search_cc_cloud):
        """测试获取集群详情"""
        mock_search_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        url = f"/apis/redis/bizs/{constant.BK_BIZ_ID}/redis_resources/1001/"
        response = client.get(url)

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert result["data"]["id"] == 1001

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_list_instances(self, mock_search_cc_cloud):
        """测试获取实例列表"""
        mock_search_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        url = f"/apis/redis/bizs/{constant.BK_BIZ_ID}/redis_resources/list_instances/?limit=10&offset=0"
        response = client.get(url)

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "count" in result["data"]

    def test_get_table_fields(self):
        """测试获取表字段"""
        url = f"/apis/redis/bizs/{constant.BK_BIZ_ID}/redis_resources/get_table_fields/"
        response = client.get(url)

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert isinstance(result["data"], list)

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_list_machines(self, mock_search_cc_cloud):
        """测试获取机器列表"""
        mock_search_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        url = f"/apis/redis/bizs/{constant.BK_BIZ_ID}/redis_resources/list_machines/?limit=10&offset=0"
        response = client.get(url)

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_list_cluster_entries(self, mock_search_cc_cloud):
        """测试获取集群入口列表"""
        mock_search_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        url = f"/apis/redis/bizs/{constant.BK_BIZ_ID}/redis_resources/list_cluster_entries/?limit=10&offset=0"
        response = client.get(url)

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0

    def test_get_nodes(self):
        """测试获取集群节点"""
        url = f"/apis/redis/bizs/{constant.BK_BIZ_ID}/redis_resources/1001/get_nodes/?role=redis_master"
        response = client.get(url)

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0

    @patch("backend.flow.utils.base.payload_handler.PayloadHandler.redis_get_cluster_password")
    def test_get_password(self, mock_get_password):
        """测试获取集群密码"""
        mock_get_password.return_value = {"redis_proxy_password": "test_password"}

        url = f"/apis/redis/bizs/{constant.BK_BIZ_ID}/redis_resources/1001/get_password/"
        response = client.get(url)

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "password" in result["data"]
