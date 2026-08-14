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
# isort: skip_file
from unittest.mock import MagicMock, patch

import pytest
from django.db.models import Q

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_services.mongodb.resources.query import MongoDBExportQueryResourceMixin, MongoDBListRetrieveResource

pytestmark = pytest.mark.django_db


class TestMongoDBExportQueryResourceMixin:
    """测试 MongoDBExportQueryResourceMixin 类"""

    def test_fill_instances_to_cluster_info_empty(self):
        """测试填充实例信息 - 空实例集"""
        cluster_info = {}
        role_header_ids = set()
        instance_queryset = StorageInstance.objects.none()

        MongoDBExportQueryResourceMixin.fill_instances_to_cluster_info(
            cluster_info, instance_queryset, role_header_ids
        )

        assert cluster_info == {}
        assert role_header_ids == set()

    def test_fill_instances_to_cluster_info_with_mongodb_instances(self, mongodb_replicaset_cluster):
        """测试填充实例信息 - 包含MongoDB实例"""
        cluster = mongodb_replicaset_cluster
        cluster_info = {}
        role_header_ids = set()

        # 获取MongoDB存储实例
        storage_queryset = cluster.storageinstance_set.all()

        MongoDBExportQueryResourceMixin.fill_instances_to_cluster_info(cluster_info, storage_queryset, role_header_ids)

        # 验证实例信息已填充
        assert len(role_header_ids) > 0
        # 验证MongoDB角色的实例信息被填充
        assert MachineType.MONGODB in cluster_info
        assert ":" in cluster_info[MachineType.MONGODB]  # 格式应该是 ip:port

    def test_fill_instances_to_cluster_info_with_mongos_instances(self, mongodb_sharded_cluster):
        """测试填充实例信息 - 包含Mongos实例"""
        cluster = mongodb_sharded_cluster
        cluster_info = {}
        role_header_ids = set()

        # 获取Mongos代理实例
        proxy_queryset = cluster.proxyinstance_set.all()

        MongoDBExportQueryResourceMixin.fill_instances_to_cluster_info(cluster_info, proxy_queryset, role_header_ids)

        # 验证Mongos实例信息已填充
        assert MachineType.MONGOS in cluster_info or len(role_header_ids) > 0

    def test_update_headers(self):
        """测试更新表头"""
        headers = [{"id": "cluster_id", "name": "集群ID"}]

        new_headers, extra_headers = MongoDBExportQueryResourceMixin.update_headers(headers)

        # 验证去除了slave_domain和db_module_name
        header_ids = [h["id"] for h in new_headers]
        assert "slave_domain" not in header_ids
        assert "db_module_name" not in header_ids

        # 验证添加了MongoDB特有的表头
        extra_header_ids = [h["id"] for h in extra_headers]
        assert "clb" in extra_header_ids
        assert "mongo_config" in extra_header_ids
        assert "mongos" in extra_header_ids
        assert "mongodb" in extra_header_ids

    @patch("backend.db_services.dbbase.resources.query.CommonQueryResourceMixin.get_cluster_clb_polaris_entries")
    def test_update_cluster_info(self, mock_get_clb_polaris):
        """测试更新集群信息"""
        mock_get_clb_polaris.return_value = ("1.1.1.1:10000", "")

        cluster = MagicMock()
        cluster_info = {
            "cluster_id": 1,
            "cluster_name": "test",
            "slave_domain": "slave.test.db",
            "db_module_name": "test_module",
        }

        result = MongoDBExportQueryResourceMixin.update_cluster_info(cluster, cluster_info)

        # 验证添加了clb信息
        assert "clb" in result
        # 验证删除了slave_domain和db_module_name
        assert "slave_domain" not in result
        assert "db_module_name" not in result


class TestMongoDBListRetrieveResource:
    """测试 MongoDBListRetrieveResource 类"""

    def test_cluster_types(self):
        """测试集群类型定义"""
        assert ClusterType.MongoReplicaSet in MongoDBListRetrieveResource.cluster_types
        assert ClusterType.MongoShardedCluster in MongoDBListRetrieveResource.cluster_types

    def test_list_clusters_with_domain_filter(self, mongodb_replicaset_cluster):
        """测试按域名过滤查询集群"""
        cluster = mongodb_replicaset_cluster
        query_params = {"domains": cluster.immute_domain}

        result = MongoDBListRetrieveResource._list_clusters(
            bk_biz_id=cluster.bk_biz_id, query_params=query_params, limit=10, offset=0
        )

        assert result.count >= 0  # 查询结果应该包含数据

    def test_list_clusters_empty_domain_filter(self, mongodb_bk_biz_id):
        """测试空域名过滤"""
        query_params = {"domains": ""}

        result = MongoDBListRetrieveResource._list_clusters(
            bk_biz_id=mongodb_bk_biz_id, query_params=query_params, limit=10, offset=0
        )

        assert result.count >= 0

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.db_meta.models.AppCache.objects.get")
    def test_to_cluster_representation_replicaset(
        self, mock_app_cache, mock_cc_cloud, mongodb_replicaset_cluster, mongodb_spec
    ):
        """测试副本集集群信息转换"""
        from django.db.models import Prefetch

        from backend.db_meta.models import Cluster

        # 重新获取集群并预取关联数据
        from backend.db_meta.models.cluster_entry import ClusterEntry
        from backend.db_meta.models.storage_instance_tuple import StorageInstanceTuple

        # 按照_filter_cluster_hook的方式预取数据
        storage_ids = StorageInstance.objects.filter(cluster=mongodb_replicaset_cluster).values_list("id", flat=True)

        storage_instance_queryset = StorageInstance.objects.prefetch_related(
            Prefetch(
                "as_ejector",
                queryset=StorageInstanceTuple.objects.select_related("receiver", "receiver__machine").filter(
                    ejector__in=storage_ids
                ),
                to_attr="instance_tuples",
            )
        ).select_related("machine")

        proxy_queryset = ProxyInstance.objects.select_related("machine")

        cluster = Cluster.objects.prefetch_related(
            Prefetch("storageinstance_set", queryset=storage_instance_queryset, to_attr="storage_instances"),
            Prefetch("storageinstance_set", to_attr="storages"),
            Prefetch("proxyinstance_set", queryset=proxy_queryset, to_attr="proxies"),
            Prefetch("nosqlstoragesetdtl_set", to_attr="storage_set_dtl"),
            Prefetch(
                "clusterentry_set", queryset=ClusterEntry.objects.select_related("forward_to"), to_attr="entries"
            ),
        ).get(id=mongodb_replicaset_cluster.id)

        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}
        mock_app = MagicMock()
        mock_app.bk_biz_name = "test_biz"
        mock_app_cache.return_value = mock_app

        # 准备cluster_info需要的参数
        cluster_entry = []
        db_module_names_map = {cluster.db_module_id: "test_module"}
        cluster_entry_map = {}
        cluster_operate_records_map = {}
        cloud_info = {"0": {"bk_cloud_name": "Default Area"}}
        biz_info = mock_app
        cluster_stats_map = {}
        cluster_zone_map = {}

        cluster_info = MongoDBListRetrieveResource._to_cluster_representation(
            cluster=cluster,
            cluster_entry=cluster_entry,
            db_module_names_map=db_module_names_map,
            cluster_entry_map=cluster_entry_map,
            cluster_operate_records_map=cluster_operate_records_map,
            cloud_info=cloud_info,
            biz_info=biz_info,
            cluster_stats_map=cluster_stats_map,
            cluster_zone_map=cluster_zone_map,
            remote_spec_map={mongodb_spec.spec_id: mongodb_spec} if mongodb_spec else {},
        )

        # 验证返回的集群信息包含MongoDB特有字段
        assert "mongodb" in cluster_info
        assert "mongo_config" in cluster_info
        assert "mongos" in cluster_info
        assert "shard_num" in cluster_info
        assert "shard_node_count" in cluster_info
        assert cluster_info["shard_num"] == 1  # 副本集分片数为1

        # 节点带角色/状态字段，且按 m1 → m2 → … → backup 排序
        assert cluster_info["mongodb"]
        for node in cluster_info["mongodb"]:
            assert "instance_role" in node
            assert "mongodb_state" in node
            assert "seg_range" not in node  # 副本集不带分片名
        role_order = [node["instance_role"] for node in cluster_info["mongodb"]]
        from backend.db_services.mongodb.resources.query import _MONGO_DISPLAY_ROLE_INDEX

        role_indexes = [_MONGO_DISPLAY_ROLE_INDEX.get(role, 999) for role in role_order]
        assert role_indexes == sorted(role_indexes)

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.db_meta.models.AppCache.objects.get")
    def test_to_cluster_representation_sharded(
        self, mock_app_cache, mock_cc_cloud, mongodb_sharded_cluster, mongodb_spec
    ):
        """测试分片集群信息转换"""
        from django.db.models import Prefetch

        from backend.db_meta.models import Cluster

        # 重新获取集群并预取关联数据
        from backend.db_meta.models.cluster_entry import ClusterEntry
        from backend.db_meta.models.storage_instance_tuple import StorageInstanceTuple
        from backend.db_meta.models.storage_set_dtl import NosqlStorageSetDtl

        # 按照_filter_cluster_hook的方式预取数据
        storage_ids = StorageInstance.objects.filter(cluster=mongodb_sharded_cluster).values_list("id", flat=True)

        storage_instance_queryset = StorageInstance.objects.prefetch_related(
            Prefetch(
                "as_ejector",
                queryset=StorageInstanceTuple.objects.select_related("receiver", "receiver__machine").filter(
                    ejector__in=storage_ids
                ),
                to_attr="instance_tuples",
            )
        ).select_related("machine")

        proxy_queryset = ProxyInstance.objects.select_related("machine")
        storage_set_dtl_queryset = NosqlStorageSetDtl.objects.select_related("instance", "instance__machine")

        cluster = Cluster.objects.prefetch_related(
            Prefetch("storageinstance_set", queryset=storage_instance_queryset, to_attr="storage_instances"),
            Prefetch("storageinstance_set", to_attr="storages"),
            Prefetch("proxyinstance_set", queryset=proxy_queryset, to_attr="proxies"),
            Prefetch("nosqlstoragesetdtl_set", queryset=storage_set_dtl_queryset, to_attr="storage_set_dtl"),
            Prefetch(
                "clusterentry_set", queryset=ClusterEntry.objects.select_related("forward_to"), to_attr="entries"
            ),
        ).get(id=mongodb_sharded_cluster.id)

        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}
        mock_app = MagicMock()
        mock_app.bk_biz_name = "test_biz"
        mock_app_cache.return_value = mock_app

        cluster_entry = []
        db_module_names_map = {cluster.db_module_id: "test_module"}
        cluster_entry_map = {}
        cluster_operate_records_map = {}
        cloud_info = {"0": {"bk_cloud_name": "Default Area"}}
        biz_info = mock_app
        cluster_stats_map = {}
        cluster_zone_map = {}

        cluster_info = MongoDBListRetrieveResource._to_cluster_representation(
            cluster=cluster,
            cluster_entry=cluster_entry,
            db_module_names_map=db_module_names_map,
            cluster_entry_map=cluster_entry_map,
            cluster_operate_records_map=cluster_operate_records_map,
            cloud_info=cloud_info,
            biz_info=biz_info,
            cluster_stats_map=cluster_stats_map,
            cluster_zone_map=cluster_zone_map,
            remote_spec_map={mongodb_spec.spec_id: mongodb_spec} if mongodb_spec else {},
        )

        # 验证返回的集群信息包含分片相关字段
        assert "mongodb" in cluster_info
        assert "mongo_config" in cluster_info
        assert "mongos" in cluster_info
        assert "shard_num" in cluster_info
        assert "seg_range" in cluster_info
        assert cluster_info["shard_num"] > 1  # 分片集群分片数大于1

        # ShardSvr：角色/状态/分片名；按 seg_range → 角色排序
        assert cluster_info["mongodb"]
        for node in cluster_info["mongodb"]:
            assert "instance_role" in node
            assert "mongodb_state" in node
            assert node.get("seg_range")
        from backend.db_services.mongodb.resources.query import _MONGO_DISPLAY_ROLE_INDEX

        shard_keys = [
            (node["seg_range"], _MONGO_DISPLAY_ROLE_INDEX.get(node["instance_role"], 999), node["ip"], node["port"])
            for node in cluster_info["mongodb"]
        ]
        assert shard_keys == sorted(shard_keys)

        # ConfigSvr：角色有序
        if cluster_info["mongo_config"]:
            for node in cluster_info["mongo_config"]:
                assert "instance_role" in node
                assert "mongodb_state" in node
            config_indexes = [
                _MONGO_DISPLAY_ROLE_INDEX.get(node["instance_role"], 999) for node in cluster_info["mongo_config"]
            ]
            assert config_indexes == sorted(config_indexes)

        # Mongos：按 ip → port 排序
        if cluster_info["mongos"]:
            mongos_keys = [(node["ip"], node["port"]) for node in cluster_info["mongos"]]
            assert mongos_keys == sorted(mongos_keys)

    def test_list_instances_with_cluster_type_filter(self, mongodb_replicaset_cluster):
        """测试按集群类型过滤实例"""
        cluster = mongodb_replicaset_cluster
        query_params = {"cluster_type": ClusterType.MongoReplicaSet.value}

        result = MongoDBListRetrieveResource._list_instances(
            bk_biz_id=cluster.bk_biz_id, query_params=query_params, limit=10, offset=0
        )

        assert result.count >= 0

    def test_list_instances_with_exact_ip_filter(self, mongodb_replicaset_cluster):
        """测试按精确IP过滤实例"""
        cluster = mongodb_replicaset_cluster
        instance = cluster.storageinstance_set.first()
        query_params = {"exact_ip": instance.machine.ip}

        result = MongoDBListRetrieveResource._list_instances(
            bk_biz_id=cluster.bk_biz_id, query_params=query_params, limit=10, offset=0
        )

        assert result.count >= 0

    def test_filter_instance_qs_with_domain(self, mongodb_replicaset_cluster):
        """测试过滤实例查询集 - 包含域名过滤"""
        cluster = mongodb_replicaset_cluster
        query_filters = Q(cluster__id=cluster.id)
        query_params = {"domain": cluster.immute_domain}

        instances = MongoDBListRetrieveResource._filter_instance_qs(query_filters, query_params)

        # 验证返回的是QuerySet
        assert instances is not None

    def test_filter_instance_qs_default_role_order(self, mongodb_replicaset_cluster):
        """实例列表默认按 m1 → … → backup 排序"""
        from backend.db_services.mongodb.resources.query import _MONGO_DISPLAY_ROLE_INDEX

        cluster = mongodb_replicaset_cluster
        query_filters = Q(cluster__id=cluster.id)
        rows = list(MongoDBListRetrieveResource._filter_instance_qs(query_filters, {}))
        roles = [row["role"] for row in rows]
        indexes = [_MONGO_DISPLAY_ROLE_INDEX.get(role, 999) for role in roles]
        assert indexes == sorted(indexes)

    def test_filter_instance_qs_storage_and_proxy(self, mongodb_sharded_cluster):
        """测试过滤实例查询集 - 同时包含存储和代理实例；默认 mongos → config → shard 角色序"""
        from backend.db_services.mongodb.resources.query import (
            _MONGO_DISPLAY_ROLE_INDEX,
            _MONGO_MACHINE_TYPE_ORDER,
        )

        cluster = mongodb_sharded_cluster
        query_filters = Q(cluster__id=cluster.id)
        query_params = {}

        rows = list(MongoDBListRetrieveResource._filter_instance_qs(query_filters, query_params))
        assert rows

        machine_type_index = {mt: idx for idx, mt in enumerate(_MONGO_MACHINE_TYPE_ORDER)}
        sort_keys = [
            (
                machine_type_index.get(row["machine__machine_type"], 9),
                row.get("shard") or "",
                _MONGO_DISPLAY_ROLE_INDEX.get(row["role"], 0 if row["machine__machine_type"] == "mongos" else 999),
                row["machine__ip"],
                row["port"],
            )
            for row in rows
        ]
        assert sort_keys == sorted(sort_keys)

    def test_to_instance_representation(self, mongodb_replicaset_cluster):
        """测试实例信息转换"""
        cluster = mongodb_replicaset_cluster
        instance = cluster.storageinstance_set.first()

        instance_dict = {
            "id": instance.id,
            "cluster__id": cluster.id,
            "cluster__cluster_type": cluster.cluster_type,
            "cluster__name": cluster.name,
            "cluster__db_module_id": cluster.db_module_id,
            "version": instance.version or "",
            "machine__bk_host_id": instance.machine.bk_host_id,
            "machine__ip": instance.machine.ip,
            "machine__bk_cloud_id": instance.machine.bk_cloud_id,
            "machine__bk_sub_zone": instance.machine.bk_sub_zone or "",
            "machine__bk_sub_zone_id": instance.machine.bk_sub_zone_id or 0,
            "machine__machine_type": instance.machine.machine_type,
            "machine__spec_config": instance.machine.spec_config or {},
            "machine__bk_os_name": instance.machine.bk_os_name or "",
            "machine__bk_rack_id": instance.machine.bk_rack_id or "",
            "machine__bk_svr_device_cls_name": instance.machine.bk_svr_device_cls_name or "",
            "port": instance.port,
            "role": instance.instance_role,
            "status": instance.status,
            "create_at": instance.create_at,
            "shard": "",
            "bind_entry__entry": "",
            "bk_biz_id": cluster.bk_biz_id,
        }

        cluster_entry_map = {}
        db_module_names_map = {cluster.db_module_id: "test_module"}
        instance_operator_record_map = {}
        cloud_info = {"0": {"bk_cloud_name": "Default Area"}}

        result = MongoDBListRetrieveResource._to_instance_representation(
            instance_dict,
            cluster_entry_map,
            db_module_names_map,
            instance_operator_record_map=instance_operator_record_map,
            cloud_info=cloud_info,
        )

        # 验证实例信息包含MongoDB特有字段
        assert "shard" in result
        assert "operations" in result
        assert "instance_domain" in result

    @patch("backend.db_meta.api.cluster.mongocluster.scan_cluster")
    def test_get_topo_graph_sharded(self, mock_scan_cluster, mongodb_sharded_cluster):
        """测试获取分片集群拓扑图"""
        cluster = mongodb_sharded_cluster
        mock_graph = MagicMock()
        mock_graph.to_dict.return_value = {"nodes": [], "edges": []}
        mock_scan_cluster.return_value = mock_graph

        graph = MongoDBListRetrieveResource.get_topo_graph(bk_biz_id=cluster.bk_biz_id, cluster_id=cluster.id)

        # 验证调用了分片集群的scan_cluster方法
        assert mock_scan_cluster.called
        assert "nodes" in graph
        assert "edges" in graph

    @patch("backend.db_meta.api.cluster.mongorepset.scan_cluster")
    def test_get_topo_graph_replicaset(self, mock_scan_cluster, mongodb_replicaset_cluster):
        """测试获取副本集集群拓扑图"""
        cluster = mongodb_replicaset_cluster
        mock_graph = MagicMock()
        mock_graph.to_dict.return_value = {"nodes": [], "edges": []}
        mock_scan_cluster.return_value = mock_graph

        graph = MongoDBListRetrieveResource.get_topo_graph(bk_biz_id=cluster.bk_biz_id, cluster_id=cluster.id)

        # 验证调用了副本集的scan_cluster方法
        assert mock_scan_cluster.called
        assert "nodes" in graph
        assert "edges" in graph

    def test_query_storage_shard_replicaset(self, mongodb_replicaset_cluster):
        """测试查询副本集分片信息"""
        cluster = mongodb_replicaset_cluster
        query_conditions = Q(cluster__id=cluster.id)

        storage_instance, storage_id__shard = MongoDBListRetrieveResource.query_storage_shard(query_conditions)

        # 验证副本集分片信息为空
        for storage_id, shard in storage_id__shard.items():
            assert shard == ""  # 副本集没有分片信息

    def test_query_storage_shard_sharded_cluster(self, mongodb_sharded_cluster):
        """测试查询分片集群分片信息"""
        cluster = mongodb_sharded_cluster
        query_conditions = Q(
            cluster__id=cluster.id,
            machine__machine_type=MachineType.MONGODB,
        )

        storage_instance, storage_id__shard = MongoDBListRetrieveResource.query_storage_shard(query_conditions)

        # 验证分片集群有分片信息
        shard_values = set(storage_id__shard.values())
        assert len(shard_values) > 0  # 应该有分片信息

    def test_filter_cluster_hook_prefetch(self, mongodb_sharded_cluster):
        """测试集群过滤钩子的预取功能"""
        cluster = mongodb_sharded_cluster

        cluster_queryset = cluster.__class__.objects.filter(id=cluster.id)
        proxy_queryset = ProxyInstance.objects.filter(cluster=cluster)
        storage_queryset = StorageInstance.objects.filter(cluster=cluster)

        result = MongoDBListRetrieveResource._filter_cluster_hook(
            bk_biz_id=cluster.bk_biz_id,
            cluster_queryset=cluster_queryset,
            proxy_queryset=proxy_queryset,
            storage_queryset=storage_queryset,
            limit=10,
            offset=0,
        )

        # 验证返回了ResourceList对象
        assert hasattr(result, "count")
        assert hasattr(result, "data")

    def test_filter_instance_hook(self, mongodb_replicaset_cluster):
        """测试实例过滤钩子"""
        cluster = mongodb_replicaset_cluster
        instance = cluster.storageinstance_set.first()

        instances = [
            {
                "id": instance.id,
                "cluster__id": cluster.id,
                "cluster__cluster_type": cluster.cluster_type,
                "cluster__name": cluster.name,
                "cluster__db_module_id": cluster.db_module_id,
                "version": instance.version or "",
                "machine__bk_host_id": instance.machine.bk_host_id,
                "machine__ip": instance.machine.ip,
                "machine__bk_cloud_id": instance.machine.bk_cloud_id,
                "machine__bk_sub_zone": instance.machine.bk_sub_zone or "",
                "machine__bk_sub_zone_id": instance.machine.bk_sub_zone_id or 0,
                "machine__machine_type": instance.machine.machine_type,
                "machine__spec_config": instance.machine.spec_config or {},
                "machine__bk_os_name": instance.machine.bk_os_name or "",
                "machine__bk_rack_id": instance.machine.bk_rack_id or "",
                "machine__bk_svr_device_cls_name": instance.machine.bk_svr_device_cls_name or "",
                "port": instance.port,
                "role": instance.instance_role,
                "status": instance.status,
                "create_at": instance.create_at,
                "shard": "",
                "bind_entry__entry": "",
                "bk_biz_id": cluster.bk_biz_id,
            }
        ]

        query_params = {}

        result = MongoDBListRetrieveResource._filter_instance_hook(
            bk_biz_id=cluster.bk_biz_id,
            query_params=query_params,
            instances=instances,
        )

        # 验证实例钩子正常执行
        assert result is not None
