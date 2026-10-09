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

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import AccessLayer, ClusterType
from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator


@pytest.mark.parametrize(
    "relations,resource_module_id,expected",
    [
        ([], 100, True),
        ([{"bk_module_id": 100}], 100, False),
        ([{"bk_module_id": 200}], 100, True),
    ],
)
def test_resolve_replicaset_deploy_is_increment(relations, resource_module_id, expected):
    with patch(
        "backend.flow.utils.mongodb.mongodb_module_operate.CCApi.find_host_biz_relations",
        return_value=relations,
    ):
        assert MongoDBCCTopoOperator.resolve_replicaset_deploy_is_increment(1, resource_module_id) is expected


def _make_operator(cluster_id=1):
    cluster = SimpleNamespace(id=cluster_id, cluster_type=ClusterType.MongoShardedCluster.value, name="c1")
    with patch.object(MongoDBCCTopoOperator, "__init__", lambda self, c, ticket_data=None: None):
        op = MongoDBCCTopoOperator.__new__(MongoDBCCTopoOperator)
        op.clusters = [cluster]
        op._shard_name_cache = {}
        return op, cluster


def test_get_mongo_shard_maps_primary_secondary_and_unknown():
    op, cluster = _make_operator()
    primary = SimpleNamespace(id=11)
    secondary = SimpleNamespace(id=12)
    unknown = SimpleNamespace(id=99)

    detail = SimpleNamespace(id=1, instance_id=11, seg_range="shard-0", instance=primary)
    qs = MagicMock()
    qs.order_by.return_value.all.return_value = [detail]
    cluster.nosqlstoragesetdtl_set = qs

    tpl = SimpleNamespace(id=1, ejector_id=11, receiver_id=12)
    with patch(
        "backend.flow.utils.mongodb.mongodb_module_operate.StorageInstanceTuple.objects.filter",
        return_value=MagicMock(order_by=MagicMock(return_value=[tpl])),
    ) as filter_mock:
        assert op.get_mongo_shard(cluster, primary) == "shard-0"
        assert op.get_mongo_shard(cluster, secondary) == "shard-0"
        assert op.get_mongo_shard(cluster, unknown) == "unknown"
        # Same operator/cluster only builds map once
        assert filter_mock.call_count == 1
        assert qs.order_by.call_count == 1


def test_get_mongo_shard_keeps_first_seen_shard_name():
    op, cluster = _make_operator()
    shared = SimpleNamespace(id=21)
    secondary = SimpleNamespace(id=22)
    detail1 = SimpleNamespace(id=1, instance_id=21, seg_range="shard-a", instance=shared)
    detail2 = SimpleNamespace(id=2, instance_id=21, seg_range="shard-b", instance=shared)
    qs = MagicMock()
    qs.order_by.return_value.all.return_value = [detail1, detail2]
    cluster.nosqlstoragesetdtl_set = qs

    tpl = SimpleNamespace(id=1, ejector_id=21, receiver_id=22)
    with patch(
        "backend.flow.utils.mongodb.mongodb_module_operate.StorageInstanceTuple.objects.filter",
        return_value=MagicMock(order_by=MagicMock(return_value=[tpl])),
    ):
        assert op.get_mongo_shard(cluster, shared) == "shard-a"
        assert op.get_mongo_shard(cluster, secondary) == "shard-a"


def test_generate_custom_labels_replicaset_and_mongos():
    op, _ = _make_operator()
    replicaset = SimpleNamespace(id=2, cluster_type=ClusterType.MongoReplicaSet.value, name="rs-1")
    sharded = SimpleNamespace(id=3, cluster_type=ClusterType.MongoShardedCluster.value, name="sc-1")
    storage = SimpleNamespace(id=1, instance_role="mongo_m1")
    mongos = SimpleNamespace(id=2, instance_role=AccessLayer.PROXY.value)

    assert op.generate_custom_labels(storage, replicaset) == {"shard": "rs-1"}
    assert op.generate_custom_labels(mongos, sharded) == {}


def test_transfer_host_module_skips_hosts_already_in_target():
    op, _ = _make_operator()
    op.bk_biz_id = 100
    with patch(
        "backend.flow.utils.mongodb.mongodb_module_operate.CCApi.find_host_biz_relations",
        return_value=[
            {"bk_host_id": 1, "bk_module_id": 10},
            {"bk_host_id": 2, "bk_module_id": 20},
        ],
    ), patch("backend.flow.utils.mongodb.mongodb_module_operate.CcManage") as cc_manage:
        op._transfer_host_module_if_needed(
            cluster_type=ClusterType.MongoShardedCluster.value,
            bk_host_ids=[1, 2],
            target_module_ids=[10],
            is_increment=False,
        )
        cc_manage.return_value.transfer_host_module.assert_called_once_with([2], [10], False)
