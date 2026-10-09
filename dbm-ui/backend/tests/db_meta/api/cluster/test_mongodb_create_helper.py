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

from backend.db_meta.api.cluster.nosqlcomm.mongodb_create_helper import (
    StageTimer,
    emit_progress,
    find_reusable_cluster,
    partition_proxy_inputs,
    partition_storage_inputs,
)
from backend.db_meta.enums import ClusterPhase, ClusterType


def test_emit_progress_and_stage_timer():
    logs = []
    emit_progress(None, "ignored")
    emit_progress(logs.append, "hello")
    assert logs == ["hello"]

    timer = StageTimer(logs.append, "stage-a", count=3)
    timer.done(skipped=1, created=2)
    assert logs[1].startswith("[start] stage-a, count=3")
    assert "[done] stage-a" in logs[2]
    assert "skipped=1" in logs[2]
    assert "created=2" in logs[2]


def test_partition_storage_inputs_missing_reusable_conflict():
    missing_node = {"ip": "127.0.0.1", "port": 27001, "role": "mongo_m1"}
    reusable_node = {"ip": "127.0.0.2", "port": 27001, "role": "mongo_m2"}
    conflict_node = {"ip": "127.0.0.3", "port": 27001, "role": "mongo_m3"}
    same_cluster_node = {"ip": "127.0.0.4", "port": 27001, "role": "mongo_backup"}
    foreign_unbound_node = {"ip": "127.0.0.5", "port": 27001, "role": "mongo_backup"}

    reusable_obj = MagicMock()
    reusable_obj.name = "c1"
    reusable_obj.cluster.values_list.return_value = []
    foreign_unbound = MagicMock()
    foreign_unbound.name = "other"
    foreign_unbound.cluster.values_list.return_value = []
    conflict_obj = MagicMock()
    conflict_obj.cluster.values_list.return_value = [99]
    same_cluster_obj = MagicMock()
    same_cluster_obj.cluster.values_list.return_value = [7]

    def filter_side_effect(**kwargs):
        ip = kwargs["machine__ip"]
        qs = MagicMock()
        if ip == "127.0.0.1":
            qs.first.return_value = None
        elif ip == "127.0.0.2":
            qs.first.return_value = reusable_obj
        elif ip == "127.0.0.4":
            qs.first.return_value = same_cluster_obj
        elif ip == "127.0.0.5":
            qs.first.return_value = foreign_unbound
        else:
            qs.first.return_value = conflict_obj
        return qs

    with patch(
        "backend.db_meta.api.cluster.nosqlcomm.mongodb_create_helper.StorageInstance.objects.filter",
        side_effect=filter_side_effect,
    ):
        missing, reusable, conflicts = partition_storage_inputs(
            [missing_node, reusable_node, conflict_node, same_cluster_node, foreign_unbound_node],
            bk_cloud_id=0,
            allowed_cluster_id=7,
            cluster_name="c1",
        )
    assert missing == [missing_node]
    assert reusable == [reusable_obj, same_cluster_obj]
    assert len(conflicts) == 2
    assert "127.0.0.3:27001" in conflicts[0]
    assert "127.0.0.5:27001" in conflicts[1]


def test_partition_proxy_inputs_similar():
    with patch(
        "backend.db_meta.api.cluster.nosqlcomm.mongodb_create_helper.ProxyInstance.objects.filter",
    ) as filter_mock:
        filter_mock.return_value.first.return_value = None
        missing, reusable, conflicts = partition_proxy_inputs([{"ip": "127.0.0.1", "port": 27017}], 0)
    assert len(missing) == 1
    assert reusable == []
    assert conflicts == []


def test_find_reusable_cluster_none_and_conflict_domain():
    with patch("backend.db_meta.api.cluster.nosqlcomm.mongodb_create_helper.Cluster.objects.filter") as filter_mock:
        name_qs = MagicMock()
        name_qs.first.return_value = None
        domain_qs = MagicMock()
        domain_qs.first.return_value = SimpleNamespace(name="other")

        def side_effect(**kwargs):
            if "name" in kwargs:
                return name_qs
            return domain_qs

        filter_mock.side_effect = side_effect
        with pytest.raises(Exception, match="already exists"):
            find_reusable_cluster(1, "c1", "c1.db", ClusterType.MongoShardedCluster.value)


def _cluster(phase, storages=None, proxies=None):
    storage_qs = MagicMock()
    storage_qs.all.return_value = storages or []
    proxy_qs = MagicMock()
    proxy_qs.all.return_value = proxies or []
    return SimpleNamespace(
        id=9,
        immute_domain="c1.db",
        phase=phase,
        storageinstance_set=storage_qs,
        proxyinstance_set=proxy_qs,
    )


def _inst(ip, port, bk_cloud_id=0):
    return SimpleNamespace(port=port, machine=SimpleNamespace(ip=ip, bk_cloud_id=bk_cloud_id))


def test_find_reusable_cluster_offline_exact_match():
    inst = _inst("127.0.0.1", 27001)
    cluster = _cluster(ClusterPhase.OFFLINE.value, storages=[inst])
    with patch("backend.db_meta.api.cluster.nosqlcomm.mongodb_create_helper.Cluster.objects.filter") as filter_mock:
        filter_mock.return_value.first.return_value = cluster
        found = find_reusable_cluster(
            1,
            "c1",
            "c1.db",
            ClusterType.MongoShardedCluster.value,
            expected_storage_keys={("127.0.0.1", 27001, 0)},
        )
    assert found is cluster


def test_find_reusable_cluster_rejects_online_empty_and_subset():
    online = _cluster(ClusterPhase.ONLINE.value, storages=[_inst("127.0.0.1", 27001), _inst("127.0.0.2", 27001)])
    empty = _cluster(ClusterPhase.OFFLINE.value)
    subset = _cluster(ClusterPhase.OFFLINE.value, storages=[_inst("127.0.0.1", 27001)])
    expected = {("127.0.0.1", 27001, 0), ("127.0.0.2", 27001, 0)}
    with patch("backend.db_meta.api.cluster.nosqlcomm.mongodb_create_helper.Cluster.objects.filter") as filter_mock:
        filter_mock.return_value.first.return_value = online
        with pytest.raises(Exception, match="only an offline cluster"):
            find_reusable_cluster(
                1, "c1", "c1.db", ClusterType.MongoShardedCluster.value, expected_storage_keys=expected
            )
        filter_mock.return_value.first.return_value = empty
        with pytest.raises(Exception, match="storage instances do not match"):
            find_reusable_cluster(
                1, "c1", "c1.db", ClusterType.MongoShardedCluster.value, expected_storage_keys=expected
            )
        filter_mock.return_value.first.return_value = subset
        with pytest.raises(Exception, match="storage instances do not match"):
            find_reusable_cluster(
                1, "c1", "c1.db", ClusterType.MongoShardedCluster.value, expected_storage_keys=expected
            )
