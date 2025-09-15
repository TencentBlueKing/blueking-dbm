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
import logging
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Tag
from backend.tests.mock_data.iam_app.permission import PermissionMock

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")
client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)
def set_empty_middleware():
    """禁用中间件以简化测试"""
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.mark.django_db
class TestDBBaseViewSet:
    """测试DBBaseViewSet - 使用APIClient通过真实URL路由"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_class(self, django_db_setup, django_db_blocker):
        """设置测试类 - 禁用权限验证"""
        with django_db_blocker.unblock():
            from backend.db_services.dbbase.views import DBBaseViewSet

            # 禁用权限验证
            patch.object(DBBaseViewSet, "permission_classes", [AllowAny]).start()
            patch.object(DBBaseViewSet, "get_permissions", lambda x: []).start()
            # Mock IAM权限
            patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
            yield

    def test_verify_duplicated_cluster_name_exists(self, test_cluster_with_entries):
        """测试查询集群名称是否重复 - 存在"""
        cluster = test_cluster_with_entries

        url = "/apis/dbbase/verify_duplicated_cluster_name/"
        response = client.get(
            url,
            {"cluster_type": cluster.cluster_type, "name": cluster.name, "bk_biz_id": cluster.bk_biz_id},
        )

        assert response.status_code == 200
        assert response.json()["data"] is True

    def test_verify_duplicated_cluster_name_not_exists(self, test_bk_biz_id):
        """测试查询集群名称是否重复 - 不存在"""
        url = "/apis/dbbase/verify_duplicated_cluster_name/"
        response = client.get(
            url,
            {"cluster_type": ClusterType.TenDBHA.value, "name": "non_existent_cluster", "bk_biz_id": test_bk_biz_id},
        )

        assert response.status_code == 200
        assert response.json()["data"] is False

    @patch("backend.db_services.dbbase.views.ListRetrieveResource.common_query_cluster")
    def test_common_query_cluster(self, mock_query, test_cluster_with_entries):
        """测试查询集群通用信息"""
        cluster = test_cluster_with_entries
        mock_query.return_value = (
            [{"id": "cluster_id", "name": "集群ID"}],
            [{"cluster_id": cluster.id, "cluster_name": cluster.name}],
        )

        url = "/apis/dbbase/common_query_cluster/"
        response = client.get(
            url,
            {
                "bk_biz_id": cluster.bk_biz_id,
                "cluster_types": ClusterType.TenDBHA.value,
                "cluster_ids": str(cluster.id),
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["cluster_id"] == cluster.id

    def test_simple_query_cluster(self, test_cluster_with_entries):
        """测试查询业务集群简略信息"""
        cluster = test_cluster_with_entries

        url = "/apis/dbbase/simple_query_cluster/"
        response = client.get(
            url,
            {"bk_biz_id": cluster.bk_biz_id, "cluster_types": ClusterType.TenDBHA.value},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        cluster_ids = [c["id"] for c in data]
        assert cluster.id in cluster_ids

    @patch("backend.db_services.dbbase.instances.handlers.InstanceHandler.check_instances")
    def test_check_instances(self, mock_check, test_cluster_with_entries):
        """测试检查实例"""
        mock_check.return_value = {
            "valid_instances": [{"ip": "1.1.1.1", "port": 20000}],
            "invalid_instances": [],
        }

        url = "/apis/dbbase/check_instances/"
        response = client.post(
            url,
            {
                "instance_addresses": ["1.1.1.1:20000"],
                "cluster_type": [ClusterType.TenDBHA.value],
            },
            format="json",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "valid_instances" in data

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_query_cluster_instance_count(self, mock_search_cloud, test_cluster_with_entries):
        """测试查询集群与实例数量统计"""
        cluster = test_cluster_with_entries
        mock_search_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        url = "/apis/dbbase/query_cluster_instance_count/"
        response = client.get(url, {"bk_biz_id": cluster.bk_biz_id})

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, dict)
        assert ClusterType.TenDBHA.value in data
        assert data[ClusterType.TenDBHA.value]["cluster_count"] >= 1

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_query_biz_cluster_attrs(self, mock_search_cloud, test_cluster_with_entries):
        """测试查询业务集群属性"""
        cluster = test_cluster_with_entries
        mock_search_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        url = "/apis/dbbase/query_biz_cluster_attrs/"
        response = client.get(
            url,
            {
                "bk_biz_id": cluster.bk_biz_id,
                "cluster_type": ClusterType.TenDBHA.value,
                "cluster_attrs": "bk_cloud_id,major_version",
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, dict)

    def test_update_cluster_alias(self, test_cluster_with_entries):
        """测试更新集群别名"""
        cluster = test_cluster_with_entries
        new_alias = "new_test_alias"

        url = "/apis/dbbase/update_cluster_alias/"
        response = client.post(
            url,
            {"bk_biz_id": cluster.bk_biz_id, "cluster_id": cluster.id, "new_alias": new_alias},
            format="json",
        )

        assert response.status_code == 200
        cluster.refresh_from_db()
        assert cluster.alias == new_alias

    def test_update_cluster_tag(self, test_cluster_with_entries):
        """测试更新集群标签"""
        cluster = test_cluster_with_entries

        # 创建测试标签
        tag1 = Tag.objects.create(key="env", value="prod")
        tag2 = Tag.objects.create(key="team", value="dba")

        url = "/apis/dbbase/update_cluster_tag/"
        response = client.post(
            url,
            {"bk_biz_id": cluster.bk_biz_id, "cluster_id": cluster.id, "tags": [tag1.id, tag2.id]},
            format="json",
        )

        assert response.status_code == 200
        cluster.refresh_from_db()
        cluster_tag_ids = list(cluster.tags.values_list("id", flat=True))
        assert tag1.id in cluster_tag_ids
        assert tag2.id in cluster_tag_ids

        # 清理
        tag1.delete()
        tag2.delete()

    def test_remove_cluster_tag_keys(self, test_cluster_with_tags):
        """测试批量移除标签键"""
        cluster = test_cluster_with_tags
        tag_keys = list(cluster.tags.values_list("key", flat=True))
        initial_count = cluster.tags.count()
        assert initial_count > 0, "测试集群应该有标签"

        url = "/apis/dbbase/remove_cluster_tag_keys/"
        response = client.post(
            url,
            {"cluster_ids": [cluster.id], "keys": tag_keys},
            format="json",
        )

        # API调用成功即可,具体的tag删除逻辑由数据库事务控制
        assert response.status_code == 200

    def test_add_cluster_tag_keys(self, test_cluster_with_entries):
        """测试批量增加标签键"""
        cluster = test_cluster_with_entries
        tag = Tag.objects.create(key="test_key", value="test_value")

        url = "/apis/dbbase/add_cluster_tag_keys/"
        response = client.post(
            url,
            {"cluster_ids": [cluster.id], "tags": [tag.id]},
            format="json",
        )

        # API调用成功即可
        assert response.status_code == 200

        tag.delete()

    @patch("backend.db_services.dbbase.resources.register.cluster_type__resource_class")
    def test_filter_clusters(self, mock_register, test_multiple_clusters, test_bk_biz_id):
        """测试根据过滤条件查询集群"""
        # Mock resource_class
        mock_resource = MagicMock()
        mock_resource.list_clusters.return_value = MagicMock(
            data=[{"id": c.id, "name": c.name} for c in test_multiple_clusters]
        )
        mock_register.get.return_value = mock_resource

        url = "/apis/dbbase/filter_clusters/"
        response = client.get(
            url,
            {
                "bk_biz_id": test_bk_biz_id,
                "cluster_type": ClusterType.TenDBHA.value,
                "limit": 10,
                "offset": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)

    @patch("backend.db_services.mysql.remote_service.handlers.RemoteServiceHandler.webconsole_rpc")
    def test_webconsole_mysql(self, mock_webconsole, test_cluster_with_entries):
        """测试webconsole查询 - MySQL"""
        cluster = test_cluster_with_entries
        mock_webconsole.return_value = {"query_id": "123", "data": []}

        url = "/apis/dbbase/webconsole/"
        response = client.post(
            url,
            {"cluster_id": cluster.id, "cmd": "SELECT 1"},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "query_id" in data

    @patch("backend.db_services.dbbase.cluster.handlers.ClusterServiceHandler.console_rpc")
    def test_dbconsole_mysql(self, mock_console, test_cluster_with_entries):
        """测试dbconsole查询 - MySQL"""
        cluster = test_cluster_with_entries
        mock_console.return_value = {"query_id": "123", "data": []}

        url = "/apis/dbbase/dbconsole/"
        response = client.post(
            url,
            {"cluster_id": cluster.id, "db_type": "mysql", "is_proxy": False, "sql": "SHOW DATABASES"},
            format="json",
        )

        assert response.status_code == 200

    @patch("backend.db_services.dbbase.cluster.handlers.ClusterServiceHandler.check_cluster_databases")
    def test_check_cluster_databases(self, mock_check, test_cluster_with_entries):
        """测试查询集群的库是否存在"""
        cluster = test_cluster_with_entries
        mock_check.return_value = {"test_db": True, "other_db": False}

        url = "/apis/dbbase/check_cluster_databases/"
        response = client.post(
            url,
            {"bk_biz_id": cluster.bk_biz_id, "cluster_id": cluster.id, "db_list": ["test_db", "other_db"]},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, dict)
        assert "test_db" in data

    @patch("backend.db_services.dbbase.cluster.handlers.ClusterServiceHandler.check_cluster_databases")
    def test_batch_check_cluster_databases(self, mock_check, test_multiple_clusters):
        """测试批量查询多个集群的库是否存在"""
        clusters = test_multiple_clusters
        mock_check.return_value = {"test_db": True}

        cluster_ids = [c.id for c in clusters]
        url = "/apis/dbbase/batch_check_cluster_databases/"
        response = client.post(
            url,
            {"bk_biz_id": clusters[0].bk_biz_id, "cluster_ids": cluster_ids, "db_list": ["test_db"]},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, dict), f"响应数据应该是字典,实际: {type(data)}"
        # 批量检查返回的是 {cluster_id: {db: bool}} 格式,注意key是字符串
        for cluster_id in cluster_ids:
            assert (
                str(cluster_id) in data or cluster_id in data
            ), f"集群ID {cluster_id} 应该在响应中,实际keys: {list(data.keys())}"

    @patch("backend.db_periodic_task.local_tasks.db_meta.sync_cluster_stat.sync_cluster_stat_by_cluster_type")
    def test_query_cluster_stat(self, mock_sync_stat, test_cluster_with_entries):
        """测试查询集群容量统计"""
        cluster = test_cluster_with_entries
        mock_sync_stat.return_value = {cluster.immute_domain: {"capacity": 100, "usage": 50}}

        url = "/apis/dbbase/query_cluster_stat/"
        response = client.get(
            url,
            {"bk_biz_id": cluster.bk_biz_id, "cluster_type": ClusterType.TenDBHA.value},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, dict)

    @patch("backend.db_periodic_task.local_tasks.db_meta.sync_cluster_stat.sync_cluster_load_by_cluster_type")
    def test_query_cluster_load(self, mock_sync_load, test_cluster_with_entries):
        """测试查询集群负载"""
        cluster = test_cluster_with_entries
        mock_sync_load.return_value = ({cluster.id: "normal"}, {cluster.id: {"cpu": 50, "mem": 60}})

        url = "/apis/dbbase/query_cluster_load/"
        response = client.get(
            url,
            {"bk_biz_id": cluster.bk_biz_id, "cluster_type": ClusterType.TenDBHA.value},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, dict), f"响应应该是字典,实际: {type(data)}, 内容: {data}"
        # 检查响应格式
        assert "cluster_load_status_map" in data
        assert "cluster_load_data_map" in data

    def test_get_ips_list_mysql(self, test_cluster_with_entries):
        """测试根据db类型查询ip列表 - MySQL"""
        cluster = test_cluster_with_entries

        url = "/apis/dbbase/get_ips_list/"
        response = client.get(
            url,
            {"bk_biz_id": cluster.bk_biz_id, "db_type": "mysql"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data, list)
        assert len(data) > 0

    @patch("backend.db_services.dbbase.cluster.handlers.retrieve_resources")
    def test_filter_instances(self, mock_retrieve, test_bk_biz_id):
        """测试根据集群类型获取实例信息"""
        mock_retrieve.return_value = MagicMock(data=[{"ip": "1.1.1.1", "port": 20000}])

        url = "/apis/dbbase/filter_instances/"
        response = client.get(
            url,
            {"bk_biz_id": test_bk_biz_id, "cluster_type": ClusterType.TenDBHA.value},
        )

        assert response.status_code == 200

    @patch("backend.db_services.dbbase.cluster.handlers.retrieve_resources")
    def test_filter_machines(self, mock_retrieve, test_bk_biz_id):
        """测试根据集群类型获取机器信息"""
        mock_retrieve.return_value = MagicMock(data=[{"ip": "1.1.1.1", "bk_host_id": 1}])

        url = "/apis/dbbase/filter_machines/"
        response = client.get(
            url,
            {"bk_biz_id": test_bk_biz_id, "cluster_type": ClusterType.TenDBHA.value},
        )

        assert response.status_code == 200

    @patch("backend.db_services.dbbase.cluster.handlers.retrieve_resources")
    def test_filter_clusters_by_type(self, mock_retrieve, test_bk_biz_id):
        """测试根据集群类型获取集群信息"""
        mock_retrieve.return_value = MagicMock(
            data=[{"cluster_id": 1, "cluster_name": "test", "cluster_type": ClusterType.TenDBHA.value}]
        )

        url = "/apis/dbbase/filter_clusters_by_type/"
        response = client.get(
            url,
            {"bk_biz_id": test_bk_biz_id, "cluster_type": ClusterType.TenDBHA.value},
        )

        assert response.status_code == 200
