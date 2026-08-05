# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from rest_framework.exceptions import ValidationError

from backend.db_meta.enums import ClusterType
from backend.db_services.mongodb.toolbox.handlers import ToolboxHandler
from backend.db_services.mongodb.toolbox.serializers import ListClusterShardsSerializer


def test_list_cluster_shards_serializer_require_cluster_ids():
    serializer = ListClusterShardsSerializer(data={})
    assert not serializer.is_valid()
    assert "cluster_ids" in serializer.errors


def test_list_cluster_shards_serializer_accepts_cluster_ids():
    serializer = ListClusterShardsSerializer(data={"cluster_ids": [1, 2]})
    assert serializer.is_valid()
    assert serializer.validated_data == {"cluster_ids": [1, 2]}


def _fake_cluster(cluster_id, domain, shard_names, cluster_type=ClusterType.MongoShardedCluster.value):
    return SimpleNamespace(
        id=cluster_id,
        immute_domain=domain,
        cluster_type=cluster_type,
        mongodb_shard_dtls=[SimpleNamespace(seg_range=name) for name in shard_names],
    )


def test_list_cluster_shards_sorted_and_filters_by_biz(monkeypatch):
    called = {}
    qs = MagicMock()
    qs.prefetch_related.return_value = [
        _fake_cluster(1001, "demo.mongodb.db", ["demo-s3", "demo-s1", "demo-s2"]),
    ]

    def _filter(**kwargs):
        called.update(kwargs)
        return qs

    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        _filter,
    )

    data = ToolboxHandler(bk_biz_id=3).list_cluster_shards(bk_biz_id=3, cluster_ids=[1001])
    assert called.get("bk_biz_id") == 3
    assert called.get("id__in") == [1001]
    assert data == [
        {
            "cluster_id": 1001,
            "immute_domain": "demo.mongodb.db",
            "shard_list": ["demo-s1", "demo-s2", "demo-s3"],
        }
    ]


def test_list_cluster_shards_raise_for_missing_cluster(monkeypatch):
    qs = MagicMock()
    qs.prefetch_related.return_value = [
        _fake_cluster(100, "a.db", ["a-s1"]),
    ]
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        lambda **kwargs: qs,
    )
    with pytest.raises(ValidationError, match="集群不存在"):
        ToolboxHandler(bk_biz_id=3).list_cluster_shards(bk_biz_id=3, cluster_ids=[100, 101])


def test_list_cluster_shards_raise_for_replica_set(monkeypatch):
    qs = MagicMock()
    qs.prefetch_related.return_value = [
        _fake_cluster(100, "rs.mongodb.db", [], cluster_type=ClusterType.MongoReplicaSet.value),
    ]
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        lambda **kwargs: qs,
    )
    with pytest.raises(ValidationError, match="不是分片集群"):
        ToolboxHandler(bk_biz_id=3).list_cluster_shards(bk_biz_id=3, cluster_ids=[100])


def test_list_cluster_shards_preserves_cluster_ids_order(monkeypatch):
    qs = MagicMock()
    qs.prefetch_related.return_value = [
        _fake_cluster(200, "b.mongodb.db", ["b-s1"]),
        _fake_cluster(100, "a.mongodb.db", ["a-s1"]),
    ]
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        lambda **kwargs: qs,
    )

    data = ToolboxHandler(bk_biz_id=3).list_cluster_shards(bk_biz_id=3, cluster_ids=[200, 100])
    assert [row["cluster_id"] for row in data] == [200, 100]
    assert data[0]["shard_list"] == ["b-s1"]
    assert data[1]["shard_list"] == ["a-s1"]
