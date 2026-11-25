# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import patch

from backend.db_services.mongodb.autofix.discover import _aggregate_by_ip, _collect_sustained_peers
from backend.db_services.mongodb.autofix.metrics import PeerObservation


def _obs(name, reporter, state=8):
    return PeerObservation(name=name, reporter=reporter, state=state, cluster_domain="d.db", shard="s0")


def test_peer_below_min_records_ignore():
    observations = [_obs("127.0.0.1:27017", "127.0.0.2:27017")]
    with patch("backend.db_services.mongodb.autofix.discover.RedisConn"), patch(
        "backend.db_services.mongodb.autofix.discover._record_ignore"
    ) as record:
        sustained = _collect_sustained_peers(observations, peer_min=2, delay_minutes=10, ttl_seconds=3600, now_ts=1000)
    assert sustained == {}
    assert record.call_args.kwargs["ignore_msg"] == "peer_min_count"
    assert record.call_args.kwargs["ip"] == "127.0.0.1"
    assert record.call_args.kwargs["extra"]["peer_count"] == 1
    assert record.call_args.kwargs["extra"]["peer_min"] == 2


def test_delay_window_records_ignore():
    observations = [
        _obs("127.0.0.1:27017", "127.0.0.2:27017"),
        _obs("127.0.0.1:27017", "127.0.0.3:27017"),
    ]
    with patch("backend.db_services.mongodb.autofix.discover.RedisConn") as redis, patch(
        "backend.db_services.mongodb.autofix.discover._record_ignore"
    ) as record:
        redis.set.return_value = True
        sustained = _collect_sustained_peers(observations, peer_min=2, delay_minutes=10, ttl_seconds=3600, now_ts=1000)
    assert sustained == {}
    assert record.call_args.kwargs["ignore_msg"] == "delay_window"
    assert record.call_args.kwargs["extra"]["delay_minutes"] == 10


def test_whitelist_records_ignore():
    machine = SimpleNamespace(ip="127.0.0.1", bk_host_id=11, bk_cloud_id=0, bk_sub_zone_id=1)
    cluster = SimpleNamespace(
        id=1,
        bk_biz_id=3,
        cluster_type="MongoShardedCluster",
        immute_domain="d.db",
    )
    storage = SimpleNamespace(machine=machine, cluster=SimpleNamespace(first=lambda: cluster), port=27017)
    summary = SimpleNamespace(cluster_domain="d.db", shard="s0", set_name="")
    with patch("backend.db_services.mongodb.autofix.discover.ctl.is_whitelist_allowed", return_value=False), patch(
        "backend.db_services.mongodb.autofix.discover._record_ignore"
    ) as record:
        by_ip = _aggregate_by_ip({"127.0.0.1:27017": summary}, {"127.0.0.1:27017": storage})
    assert by_ip == {}
    assert record.call_args.kwargs["ignore_msg"] == "not_in_whitelist"
    assert record.call_args.kwargs["ip"] == "127.0.0.1"
    assert record.call_args.kwargs["immute_domain"] == "d.db"
