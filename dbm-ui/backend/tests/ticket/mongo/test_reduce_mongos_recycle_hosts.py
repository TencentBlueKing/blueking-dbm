# -*- coding: utf-8 -*-
"""缩容 mongos 的下架主机：混部了 mongod 或还留着 mongos 的机器不进下架单."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.ticket.builders.common.base import BaseTicketFlowBuilderPatchMixin
from backend.ticket.builders.mongodb.base import assign_recycle_hosts
from backend.ticket.builders.mongodb.mongo_reduce_mongos import (
    MongoDBReduceMongosFlowBuilder,
    collect_reduce_mongos_recycle_hosts,
)
from backend.ticket.builders.mongodb.mongo_reduce_shard import MongoDBReduceShardFlowBuilder


def _node(ip, host_id, port=None, bk_cloud_id=0):
    node = {"ip": ip, "bk_cloud_id": bk_cloud_id, "bk_host_id": host_id}
    if port is not None:
        node["port"] = port
    return node


def _patch_instances(monkeypatch, proxy_rows, storage_rows=None, cluster_ports=None):
    """cluster_ports: cluster_id -> [port, ...]。未给出时，按 cluster__id 查询会失败，用来卡住误用全量端口。"""

    def proxy_filter(**kwargs):
        query = MagicMock()
        if "cluster__id" in kwargs:
            if cluster_ports is None:
                raise AssertionError("should not load all cluster mongos ports")
            query.values_list.return_value = cluster_ports.get(kwargs["cluster__id"], [])
            return query
        query.values_list.return_value = proxy_rows
        return query

    storage_query = MagicMock()
    storage_query.values_list.return_value = storage_rows or []
    monkeypatch.setattr(
        "backend.ticket.builders.mongodb.mongo_reduce_mongos.ProxyInstance.objects.filter",
        proxy_filter,
    )
    monkeypatch.setattr(
        "backend.ticket.builders.mongodb.mongo_reduce_mongos.StorageInstance.objects.filter",
        lambda **kwargs: storage_query,
    )


def test_skip_host_with_storage_or_remaining_mongos(monkeypatch):
    _patch_instances(
        monkeypatch,
        proxy_rows=[
            ("127.0.0.1", 0, 27021),
            ("127.0.0.2", 0, 27021),
            ("127.0.0.3", 0, 27021),
            ("127.0.0.3", 0, 27022),
        ],
        storage_rows=[("127.0.0.2", 0)],
        cluster_ports={1001: [27021]},
    )
    infos = [
        {
            "cluster_id": 1001,
            "old_nodes": {
                "mongos": [
                    _node("127.0.0.1", 101),
                    _node("127.0.0.2", 102),
                    _node("127.0.0.3", 103),
                ]
            },
        }
    ]

    hosts = collect_reduce_mongos_recycle_hosts(3, infos)

    assert hosts == [{"ip": "127.0.0.1", "bk_host_id": 101, "bk_cloud_id": 0}]


def test_recycle_when_every_listed_mongos_port_is_removed(monkeypatch):
    _patch_instances(
        monkeypatch,
        proxy_rows=[("127.0.0.1", 0, 27021), ("127.0.0.1", 0, 27022)],
    )
    infos = [
        {
            "cluster_id": 1001,
            "old_nodes": {
                "mongos": [
                    _node("127.0.0.1", 101, port=27021),
                    _node("127.0.0.1", 101, port=27022),
                ]
            },
        }
    ]

    hosts = collect_reduce_mongos_recycle_hosts(3, infos)

    assert hosts == [{"ip": "127.0.0.1", "bk_host_id": 101, "bk_cloud_id": 0}]


def test_keep_host_when_only_one_mongos_port_is_reduced(monkeypatch):
    _patch_instances(
        monkeypatch,
        proxy_rows=[("127.0.0.1", 0, 27021), ("127.0.0.1", 0, 27022)],
        cluster_ports={1001: [27021, 27022]},
    )
    infos = [
        {
            "cluster_id": 1001,
            "old_nodes": {"mongos": [_node("127.0.0.1", 101, port=27021)]},
        }
    ]

    assert collect_reduce_mongos_recycle_hosts(3, infos) == []


def test_empty_old_nodes_returns_empty():
    assert collect_reduce_mongos_recycle_hosts(3, []) == []
    assert collect_reduce_mongos_recycle_hosts(3, None) == []
    assert collect_reduce_mongos_recycle_hosts(3, [{"cluster_id": 1001, "old_nodes": {}}]) == []
    assert collect_reduce_mongos_recycle_hosts(3, [{"cluster_id": 1001, "old_nodes": {"mongos": []}}]) == []


def test_same_host_across_clusters_keeps_remaining_mongos(monkeypatch):
    _patch_instances(
        monkeypatch,
        proxy_rows=[
            ("127.0.0.1", 0, 27021),
            ("127.0.0.1", 0, 27031),
            ("127.0.0.1", 0, 27032),
        ],
    )
    infos = [
        {"cluster_id": 1001, "old_nodes": {"mongos": [_node("127.0.0.1", 101, port=27021)]}},
        {"cluster_id": 1002, "old_nodes": {"mongos": [_node("127.0.0.1", 101, port=27031)]}},
    ]

    assert collect_reduce_mongos_recycle_hosts(3, infos) == []


def test_same_host_across_clusters_recycles_when_all_ports_removed(monkeypatch):
    _patch_instances(
        monkeypatch,
        proxy_rows=[("127.0.0.1", 0, 27021), ("127.0.0.1", 0, 27031)],
    )
    infos = [
        {"cluster_id": 1001, "old_nodes": {"mongos": [_node("127.0.0.1", 101, port=27021)]}},
        {"cluster_id": 1002, "old_nodes": {"mongos": [_node("127.0.0.1", 101, port=27031)]}},
    ]

    hosts = collect_reduce_mongos_recycle_hosts(3, infos)

    assert hosts == [{"ip": "127.0.0.1", "bk_host_id": 101, "bk_cloud_id": 0}]


def test_assign_recycle_hosts_raises_when_cmdb_fails(monkeypatch):
    monkeypatch.setattr(
        "backend.ticket.builders.mongodb.base.ResourceHandler.standardized_resource_host",
        MagicMock(side_effect=Exception("cmdb down")),
    )
    details = {}

    with pytest.raises(Exception, match="cmdb down"):
        assign_recycle_hosts(details, [{"ip": "127.0.0.1", "bk_host_id": 101, "bk_cloud_id": 0}])

    assert "recycle_hosts" not in details


def test_reduce_mongos_patch_writes_recycle_hosts_once(monkeypatch):
    hosts = [{"ip": "127.0.0.1", "bk_host_id": 101, "bk_cloud_id": 0}]
    standardized = [{"bk_host_id": 101, "ip": "127.0.0.1"}]
    monkeypatch.setattr(
        "backend.ticket.builders.mongodb.mongo_reduce_mongos.collect_reduce_mongos_recycle_hosts",
        lambda bk_biz_id, infos: hosts,
    )
    standardize = MagicMock(return_value=standardized)
    monkeypatch.setattr(
        "backend.ticket.builders.mongodb.base.ResourceHandler.standardized_resource_host",
        standardize,
    )
    ticket = SimpleNamespace(bk_biz_id=3, details={"infos": []}, save=MagicMock())
    builder = MongoDBReduceMongosFlowBuilder(ticket)

    def super_patch(self):
        assert self.ticket.details["recycle_hosts"] == standardized
        self.ticket.save(update_fields=["details"])

    monkeypatch.setattr(BaseTicketFlowBuilderPatchMixin, "patch_ticket_detail", super_patch)
    builder.patch_ticket_detail()

    standardize.assert_called_once_with(hosts)
    ticket.save.assert_called_once_with(update_fields=["details"])


def test_reduce_shard_patch_raises_when_cmdb_fails(monkeypatch):
    hosts = [{"ip": "127.0.0.1", "bk_host_id": 101, "bk_cloud_id": 0}]
    monkeypatch.setattr(
        "backend.ticket.builders.mongodb.mongo_reduce_shard.collect_reduce_shard_recycle_hosts",
        lambda bk_biz_id, infos: hosts,
    )
    monkeypatch.setattr(
        "backend.ticket.builders.mongodb.base.ResourceHandler.standardized_resource_host",
        MagicMock(side_effect=Exception("cmdb down")),
    )
    ticket = SimpleNamespace(bk_biz_id=3, details={"infos": []}, save=MagicMock())

    def super_patch(self):
        raise AssertionError("CMDB 失败时不应保存单据")

    monkeypatch.setattr(BaseTicketFlowBuilderPatchMixin, "patch_ticket_detail", super_patch)

    with pytest.raises(Exception, match="cmdb down"):
        MongoDBReduceShardFlowBuilder(ticket).patch_ticket_detail()

    ticket.save.assert_not_called()
