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

from backend.db_meta.enums import ClusterType, InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_services.dbbase.dataclass import DBInstance
from backend.db_services.mysql.cluster.handlers import ClusterServiceHandler
from backend.db_services.mysql.dataclass import ClusterFilter

pytestmark = pytest.mark.django_db


class TestMySQLClusterServiceHandler:
    """MySQL ClusterServiceHandler测试类"""

    def test_init(self, bk_biz_id):
        """测试初始化"""
        handler = ClusterServiceHandler(bk_biz_id)
        assert handler.bk_biz_id == bk_biz_id

    def test_find_related_clusters_by_cluster_id(self, bk_biz_id, dbha_cluster):
        """测试根据集群ID查找关联集群"""
        results = ClusterServiceHandler(bk_biz_id).find_related_clusters_by_cluster_ids([dbha_cluster.id])
        assert results
        for result in results:
            assert result["cluster_info"]["bk_biz_id"] == bk_biz_id
            for related_cluster in result["related_clusters"]:
                assert related_cluster["id"] != result["cluster_info"]["id"]

    def test_find_related_clusters_by_instances(self, bk_biz_id, dbha_cluster):
        """测试根据实例查找关联集群"""
        masters = StorageInstance.objects.filter(
            cluster=dbha_cluster, instance_inner_role=InstanceInnerRole.MASTER.value
        )
        master_results = ClusterServiceHandler(bk_biz_id=bk_biz_id).find_related_clusters_by_instances(
            [DBInstance.from_inst_obj(master) for master in masters]
        )
        assert master_results
        for result in master_results:
            assert result["cluster_info"]["bk_biz_id"] == bk_biz_id
            for related_cluster in result["related_clusters"]:
                assert related_cluster["id"] != result["cluster_info"]["id"]

        proxies = ProxyInstance.objects.filter(cluster=dbha_cluster)
        proxy_results = ClusterServiceHandler(bk_biz_id=bk_biz_id).find_related_clusters_by_instances(
            [DBInstance.from_inst_obj(proxy) for proxy in proxies]
        )
        # 此case中master和proxy属于相同集群，因此结果应该是一致的
        assert master_results[0]["cluster_info"] == proxy_results[0]["cluster_info"]
        assert master_results[0]["related_clusters"] == proxy_results[0]["related_clusters"]

    def test_query_clusters_dbha(self, bk_biz_id, dbha_cluster):
        """测试查询DBHA集群"""
        cluster_filters = [ClusterFilter(id=dbha_cluster.id)]
        handler = ClusterServiceHandler(bk_biz_id)

        results = handler.query_clusters(cluster_filters)

        assert len(results) == 1
        cluster_info = results[0]
        assert cluster_info["id"] == dbha_cluster.id
        assert cluster_info["cluster_type"] == ClusterType.TenDBHA
        assert "masters" in cluster_info
        assert "slaves" in cluster_info
        assert "proxies" in cluster_info
        assert "instance_count" in cluster_info

    def test_query_clusters_dbsingle(self, bk_biz_id, dbsingle_cluster):
        """测试查询DBSingle集群"""
        cluster_filters = [ClusterFilter(id=dbsingle_cluster.id)]
        handler = ClusterServiceHandler(bk_biz_id)

        results = handler.query_clusters(cluster_filters)

        assert len(results) == 1
        cluster_info = results[0]
        assert cluster_info["id"] == dbsingle_cluster.id
        assert cluster_info["cluster_type"] == ClusterType.TenDBSingle
        assert "masters" in cluster_info  # DBSingle的实例都归类为masters

    def test_query_clusters_tendbcluster(self, bk_biz_id, tendbcluster_cluster):
        """测试查询TenDBCluster集群"""
        cluster_filters = [ClusterFilter(id=tendbcluster_cluster.id)]
        handler = ClusterServiceHandler(bk_biz_id)

        results = handler.query_clusters(cluster_filters)

        assert len(results) == 1
        cluster_info = results[0]
        assert cluster_info["id"] == tendbcluster_cluster.id
        assert cluster_info["cluster_type"] == ClusterType.TenDBCluster
        assert "remote_db" in cluster_info
        assert "remote_dr" in cluster_info
        assert "spider_master" in cluster_info
        assert "spider_slave" in cluster_info
        assert "spider_ctl" in cluster_info

    def test_query_clusters_empty_filters(self, bk_biz_id):
        """测试空过滤条件查询集群"""
        handler = ClusterServiceHandler(bk_biz_id)
        results = handler.query_clusters([])
        assert results == []

    def test_query_clusters_multiple_filters(self, bk_biz_id, dbha_cluster, dbsingle_cluster):
        """测试多个过滤条件查询集群"""
        cluster_filters = [ClusterFilter(id=dbha_cluster.id), ClusterFilter(id=dbsingle_cluster.id)]
        handler = ClusterServiceHandler(bk_biz_id)

        results = handler.query_clusters(cluster_filters)

        assert len(results) == 2
        cluster_ids = [result["id"] for result in results]
        assert dbha_cluster.id in cluster_ids
        assert dbsingle_cluster.id in cluster_ids

    def test_get_remote_pairs_empty_clusters(self, bk_biz_id):
        """测试获取远程配对 - 空集群列表"""
        handler = ClusterServiceHandler(bk_biz_id)
        results = handler.get_remote_pairs([])
        assert results == []

    def test_get_remote_pairs_no_remote_instances(self, bk_biz_id, dbha_cluster):
        """测试获取远程配对 - 无远程实例"""
        handler = ClusterServiceHandler(bk_biz_id)
        results = handler.get_remote_pairs([dbha_cluster.id])
        assert results == []

    def test_get_remote_pairs_with_remote_instances(self, bk_biz_id, tendbcluster_cluster_with_remote):
        """测试获取远程配对 - 有远程实例"""
        handler = ClusterServiceHandler(bk_biz_id)
        results = handler.get_remote_pairs([tendbcluster_cluster_with_remote.id])

        assert len(results) > 0
        for result in results:
            assert "cluster_id" in result
            assert "remote_pairs" in result
            for pair in result["remote_pairs"]:
                assert "remote_db" in pair
                assert "remote_dr" in pair

    def test_get_instance_objs_dbha(self, bk_biz_id, dbha_cluster):
        """测试获取DBHA实例对象"""
        handler = ClusterServiceHandler(bk_biz_id)
        masters = StorageInstance.objects.filter(cluster=dbha_cluster, instance_inner_role=InstanceInnerRole.MASTER)
        instances = [DBInstance.from_inst_obj(master) for master in masters]

        result = handler._get_instance_objs(instances)

        assert len(result) > 0
        for inst_obj in result:
            assert hasattr(inst_obj, "machine")
            assert hasattr(inst_obj, "port")

    def test_get_instance_objs_tendbcluster(self, bk_biz_id, tendbcluster_cluster):
        """测试获取TenDBCluster实例对象（包含混布的中控节点）"""
        handler = ClusterServiceHandler(bk_biz_id)
        # 获取spider master实例
        spider_masters = ProxyInstance.objects.filter(
            cluster=tendbcluster_cluster, tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )
        instances = [DBInstance.from_inst_obj(spider) for spider in spider_masters]

        result = handler._get_instance_objs(instances)

        # 应该包含原始的spider master实例和对应的中控节点实例
        assert len(result) >= len(instances)

        # 检查是否包含中控节点（admin_port）
        spider_ctl_found = False
        for inst_obj in result:
            if hasattr(inst_obj, "role") and inst_obj.role == "spider_ctl":
                spider_ctl_found = True
                # 中控节点的端口应该是admin_port
                original_spider = spider_masters.first()
                assert inst_obj.port == original_spider.admin_port

        # 如果是TenDBCluster，应该找到中控节点
        if tendbcluster_cluster.cluster_type == ClusterType.TenDBCluster:
            assert spider_ctl_found

    def test_find_related_clusters_by_instances_same_role(self, bk_biz_id, dbha_cluster):
        """测试根据实例查找关联集群（同角色）"""
        handler = ClusterServiceHandler(bk_biz_id)
        masters = StorageInstance.objects.filter(cluster=dbha_cluster, instance_inner_role=InstanceInnerRole.MASTER)
        instances = [DBInstance.from_inst_obj(master) for master in masters]

        # MySQL的实现调用了same_role=True
        with patch.object(handler.__class__.__bases__[0], "find_related_clusters_by_instances") as mock_super:
            mock_super.return_value = []

            handler.find_related_clusters_by_instances(instances)

            # 验证调用了父类方法，并且传入了same_role=True
            mock_super.assert_called_once_with(instances, same_role=True)
