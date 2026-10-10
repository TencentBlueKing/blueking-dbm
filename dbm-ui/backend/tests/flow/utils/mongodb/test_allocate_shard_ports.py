# -*- coding: utf-8 -*-
"""shardsvr 端口分配：可复用 mongos 端口，同机时避开"""

from backend.flow.utils.mongodb.calculate_cluster import allocate_shard_ports


def _groups(*ips):
    return [[{"ip": ip, "bk_cloud_id": 0}] for ip in ips]


def test_shard_can_use_mongos_port_when_hosts_differ():
    ports = allocate_shard_ports(
        shard_num=3,
        start_port=27020,
        machine_groups=_groups("127.0.0.1", "127.0.0.2", "127.0.0.3"),
        shards_per_group=1,
        mongos_hosts={("127.0.0.10", 0)},
        mongos_port=27021,
        always_skip={28021},
    )
    assert ports == [27020, 27021, 27022]


def test_shard_skips_mongos_port_when_same_host():
    ports = allocate_shard_ports(
        shard_num=3,
        start_port=27020,
        machine_groups=_groups("127.0.0.10", "127.0.0.10", "127.0.0.10"),
        shards_per_group=1,
        mongos_hosts={("127.0.0.10", 0)},
        mongos_port=27021,
        always_skip={28021},
    )
    assert ports == [27020, 27022, 27023]


def test_only_colocated_group_skips_mongos_port():
    machine_groups = [
        [{"ip": "127.0.0.10", "bk_cloud_id": 0}, {"ip": "127.0.0.11", "bk_cloud_id": 0}],
        [{"ip": "127.0.0.1", "bk_cloud_id": 0}],
    ]
    ports = allocate_shard_ports(
        shard_num=2,
        start_port=27021,
        machine_groups=machine_groups,
        shards_per_group=1,
        mongos_hosts={("127.0.0.10", 0)},
        mongos_port=27021,
        always_skip=set(),
    )
    assert ports == [27022, 27023]


def test_config_port_always_skipped():
    ports = allocate_shard_ports(
        shard_num=2,
        start_port=28021,
        machine_groups=_groups("127.0.0.1", "127.0.0.2"),
        shards_per_group=1,
        mongos_hosts={("127.0.0.10", 0)},
        mongos_port=27021,
        always_skip={28021},
    )
    assert ports == [28022, 28023]


def test_same_ip_different_cloud_is_not_same_host():
    ports = allocate_shard_ports(
        shard_num=1,
        start_port=27021,
        machine_groups=[[{"ip": "127.0.0.10", "bk_cloud_id": 0}]],
        shards_per_group=1,
        mongos_hosts={("127.0.0.10", 1)},
        mongos_port=27021,
        always_skip=set(),
    )
    assert ports == [27021]
