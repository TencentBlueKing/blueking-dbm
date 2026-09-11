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
from backend.db_services.mongodb.autofix.gates import HostCandidate, same_rs_limit, zone_city_circuit_breaker
from backend.db_services.mongodb.autofix.metrics import (
    PeerObservation,
    aggregate_abnormal_peers,
    filter_by_peer_min,
    is_delay_satisfied,
    is_self_report,
    parse_peer_series,
)


def _obs(name, reporter, state, domain="m1.test.db", shard="s0"):
    return PeerObservation(name=name, reporter=reporter, state=state, cluster_domain=domain, shard=shard, set_name="")


def test_parse_peer_series_excludes_self_and_invalid():
    series = [
        {
            "datapoints": [[8, 1]],
            "dimensions": {
                "name": "127.0.0.1:27017",
                "instance": "127.0.0.2:27017",
                "cluster_domain": "m1.test.db",
                "shard": "s0",
                "self": "0",
            },
        },
        # self report
        {
            "datapoints": [[8, 1]],
            "dimensions": {
                "name": "127.0.0.1:27017",
                "instance": "127.0.0.1:27017",
                "cluster_domain": "m1.test.db",
                "shard": "s0",
                "self": "1",
            },
        },
        # healthy secondary from peer
        {
            "datapoints": [[2, 1]],
            "dimensions": {
                "name": "127.0.0.3:27017",
                "instance": "127.0.0.2:27017",
                "cluster_domain": "m1.test.db",
                "shard": "s0",
            },
        },
    ]
    obs = parse_peer_series(series, metric_name="new")
    assert len(obs) == 2
    assert {o.state for o in obs} == {8, 2}
    assert all(o.name != o.reporter for o in obs)


def test_is_self_report():
    assert is_self_report("127.0.0.1:27017", "127.0.0.1:27017", {}) is True
    assert is_self_report("127.0.0.1:27017", "127.0.0.2:27017", {"self": "1"}) is True
    assert is_self_report("127.0.0.1:27017", "127.0.0.2:27017", {"self": "0"}) is False


def test_parse_old_metric_member_idx_and_rs_nm():
    """旧指标：目标在 member_idx，副本集在 rs_nm，instance 为 ip-port。"""
    series = [
        {
            "datapoints": [[8, 1]],
            "dimensions": {
                "member_idx": "127.0.0.3:27000",
                "instance": "127.0.0.1-27000",
                "bk_target_ip": "127.0.0.1",
                "instance_port": "27000",
                "cluster_domain": "m1.example.db",
                "shard": "rs0",
                "rs_nm": "rs0",
                "instance_role": "m1",
                "member_state": "DOWN",
            },
        },
        # backup 旁观者应保留（与 m1 凑齐 peer_min）
        {
            "datapoints": [[8, 1]],
            "dimensions": {
                "member_idx": "127.0.0.3:27000",
                "instance": "127.0.0.2-27000",
                "cluster_domain": "m1.example.db",
                "rs_nm": "rs0",
                "instance_role": "backup",
            },
        },
        # 自报：reporter == member_idx
        {
            "datapoints": [[8, 1]],
            "dimensions": {
                "member_idx": "127.0.0.3:27000",
                "instance": "127.0.0.3-27000",
                "cluster_domain": "m1.example.db",
                "rs_nm": "rs0",
                "instance_role": "m1",
            },
        },
    ]
    obs = parse_peer_series(series, metric_name="old")
    assert len(obs) == 2
    assert {o.reporter for o in obs} == {"127.0.0.1:27000", "127.0.0.2:27000"}
    assert all(o.name == "127.0.0.3:27000" for o in obs)
    assert obs[0].set_name == "rs0"
    assert {o.state for o in obs} == {8}


def test_parse_prefers_name_over_member_idx():
    series = [
        {
            "datapoints": [[6, 1]],
            "dimensions": {
                "name": "127.0.0.10:27018",
                "member_idx": "should-not-win:27018",
                "instance": "127.0.0.11-27018",
                "cluster_domain": "m1.example.db",
                "set": "rs1",
                "shard": "rs1",
                "instance_role": "m1",
            },
        }
    ]
    obs = parse_peer_series(series, metric_name="new")
    assert len(obs) == 1
    assert obs[0].name == "127.0.0.10:27018"
    assert obs[0].set_name == "rs1"


def test_aggregate_requires_two_peers():
    observations = [
        _obs("127.0.0.1:27017", "127.0.0.2:27017", 8),
        _obs("127.0.0.1:27017", "127.0.0.3:27017", 6),
        # single peer for another target
        _obs("127.0.0.4:27017", "127.0.0.2:27017", 8),
        # healthy should not count
        _obs("127.0.0.5:27017", "127.0.0.2:27017", 2),
    ]
    aggregated = aggregate_abnormal_peers(observations)
    assert "127.0.0.1:27017" in aggregated
    assert aggregated["127.0.0.1:27017"].peer_count == 2
    assert "127.0.0.4:27017" in aggregated
    assert aggregated["127.0.0.4:27017"].peer_count == 1
    assert "127.0.0.5:27017" not in aggregated

    filtered = filter_by_peer_min(aggregated, peer_min_count=2)
    assert list(filtered.keys()) == ["127.0.0.1:27017"]


def test_old_and_new_metric_names_union_via_aggregate():
    # same reporters from two metric names should de-dup by reporter set
    observations = [
        _obs("127.0.0.1:27017", "127.0.0.2:27017", 8),
        PeerObservation(
            name="127.0.0.1:27017",
            reporter="127.0.0.2:27017",
            state=8,
            cluster_domain="m1.test.db",
            shard="s0",
            metric_name="old",
        ),
        _obs("127.0.0.1:27017", "127.0.0.3:27017", 8),
    ]
    aggregated = aggregate_abnormal_peers(observations)
    assert aggregated["127.0.0.1:27017"].peer_count == 2


def test_is_delay_satisfied():
    assert is_delay_satisfied(1000, 1000 + 10 * 60, 10) is True
    assert is_delay_satisfied(1000, 1000 + 9 * 60, 10) is False
    assert is_delay_satisfied(None, 2000, 10) is False


def test_zone_breaker_by_count():
    candidates = [
        HostCandidate(ip="127.0.0.1", bk_sub_zone_id=10, bk_city="sz"),
        HostCandidate(ip="127.0.0.2", bk_sub_zone_id=10, bk_city="sz"),
        HostCandidate(ip="127.0.0.3", bk_sub_zone_id=10, bk_city="sz"),
        HostCandidate(ip="127.0.0.4", bk_sub_zone_id=20, bk_city="sz"),
    ]
    result = zone_city_circuit_breaker(candidates, zone_host_threshold=3, city_host_threshold=5)
    assert {c.ip for c in result.suppressed} == {"127.0.0.1", "127.0.0.2", "127.0.0.3"}
    assert {c.ip for c in result.passed} == {"127.0.0.4"}


def test_zone_breaker_by_percent():
    candidates = [
        HostCandidate(ip="127.0.0.1", bk_sub_zone_id=10, bk_city="gz"),
        HostCandidate(ip="127.0.0.2", bk_sub_zone_id=10, bk_city="gz"),
    ]
    # 2/5 = 0.4 >= 0.3
    result = zone_city_circuit_breaker(
        candidates,
        zone_total_hosts={10: 5},
        zone_host_threshold=3,
        zone_percent=0.3,
        city_host_threshold=5,
    )
    assert len(result.suppressed) == 2


def test_city_breaker():
    candidates = [HostCandidate(ip=f"127.0.0.{i}", bk_sub_zone_id=i, bk_city="sh") for i in range(1, 6)]
    result = zone_city_circuit_breaker(candidates, zone_host_threshold=10, city_host_threshold=5)
    assert len(result.suppressed) == 5


def test_same_rs_limit_blocks_when_ge_two():
    c1 = HostCandidate(ip="127.0.0.1", rs_keys={"d|s0"}, names={"127.0.0.1:27017"})
    c2 = HostCandidate(ip="127.0.0.2", rs_keys={"d|s0"}, names={"127.0.0.2:27017"})
    passed, reasons = same_rs_limit([c1, c2], max_abnormal=2)
    assert passed == []
    assert "127.0.0.1" in reasons
    assert "127.0.0.2" in reasons


def test_same_rs_limit_allows_single():
    c1 = HostCandidate(ip="127.0.0.1", rs_keys={"d|s0"}, names={"127.0.0.1:27017"})
    passed, reasons = same_rs_limit([c1], max_abnormal=2)
    assert len(passed) == 1
    assert reasons == {}
