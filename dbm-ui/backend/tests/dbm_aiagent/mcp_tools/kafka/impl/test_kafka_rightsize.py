# -*- coding: utf-8 -*-
"""Kafka 集群下线/缩容评估：判定规则、PromQL、取数与汇总"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.db.models.query import QuerySet
from rest_framework.exceptions import PermissionDenied

from backend.constants import INT_MAX
from backend.db_meta.models import Cluster, Spec, StorageInstance
from backend.dbm_aiagent.mcp_tools import decorators as decorators_mod
from backend.dbm_aiagent.mcp_tools.kafka.impl import kafka_rightsize as mod
from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_rightsize import (
    KafkaClusterRightsizeInputSerializer,
    KafkaClusterRightsizeOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.kafka.views import kafka_metrics_mcp as view_mod
from backend.iam_app.handlers.drf_perm.mcp import McpDBManagePermission

GB = mod.BYTES_PER_GB


def ips(count, third=0):
    """虚构的 broker IP，只用 127.x，保证能过 CI 的硬编码 IP 检查"""
    return [f"127.0.{third}.{i + 1}" for i in range(count)]


# 默认"所有 broker 都在上报"：比测试里任何集群都多的 IP 集合，多出来的不属于集群，应当被忽略
ALL_IPS = [ip for third in range(4) for ip in ips(250, third)]
PARAMS = mod.RightsizeParams()


def make_inv(**overrides):
    values = dict(
        cluster_id=1,
        bk_biz_id=10,
        immute_domain="a.test.db",
        alias="",
        region="sh",
        nodes=60,
        cpu_cores_per_node=96,
        mem_gb_per_node=128,
        disk_gb_per_node=14000,
        bandwidth_mbps_per_node=10000,
    )
    values.update(overrides)
    values.setdefault("broker_ips", ips(values["nodes"]))
    return mod.ClusterInventory(**values)


def make_peaks(**overrides):
    values = dict(
        producer_bps=1.45e8,
        consumer_bps=1.45e8,
        cpu_peak_pct=3.0,
        host_net_bps=4.64e9,
        log_size_bytes=1 * GB,
        disk_used_bytes=23040 * GB,
        producer_ips=ALL_IPS,
        cpu_ips=ALL_IPS,
        net_ips=ALL_IPS,
        disk_ips=ALL_IPS,
    )
    values.update(overrides)
    return mod.ClusterPeaks(**values)


class TestDecideDecommission:
    def test_zero_producer_traffic_is_decommission(self):
        decision = mod.decide_cluster(make_inv(), make_peaks(producer_bps=0, consumer_bps=0), PARAMS)
        assert decision.verdict == mod.VERDICT_DECOMMISSION
        assert decision.reclaim_nodes == 60
        assert decision.flags == []

    def test_zero_producer_with_consumer_marks_flag_but_still_decommission(self):
        decision = mod.decide_cluster(make_inv(), make_peaks(producer_bps=0, consumer_bps=10), PARAMS)
        assert decision.verdict == mod.VERDICT_DECOMMISSION
        assert decision.flags == [mod.FLAG_CONSUMER_ACTIVE]

    def test_tiny_nonzero_producer_traffic_is_not_decommission(self):
        # 容差是严格的0，哪怕只有 1 B/s 也不能判下线
        decision = mod.decide_cluster(make_inv(), make_peaks(producer_bps=1.0), PARAMS)
        assert decision.verdict != mod.VERDICT_DECOMMISSION

    def test_decommission_ignores_cpu_and_other_missing_metrics(self):
        peaks = mod.ClusterPeaks(producer_bps=0, consumer_bps=0, cpu_peak_pct=95, producer_ips=ALL_IPS)
        assert mod.decide_cluster(make_inv(), peaks, PARAMS).verdict == mod.VERDICT_DECOMMISSION

    @pytest.mark.parametrize("reporting", [None, [], ips(3), ips(59)])
    def test_partial_producer_coverage_is_never_decommission(self, reporting):
        # 60台里只有部分在上报，且上报的都是空闲的：聚合出来的0不能代表整个集群没流量
        decision = mod.decide_cluster(
            make_inv(nodes=60), make_peaks(producer_bps=0, consumer_bps=0, producer_ips=reporting), PARAMS
        )
        assert (decision.verdict, decision.reasons) == (mod.VERDICT_UNCLEAR, [mod.REASON_METRICS_INCOMPLETE])
        assert decision.reclaim_nodes == 0

    def test_full_producer_coverage_allows_decommission(self):
        decision = mod.decide_cluster(make_inv(nodes=60), make_peaks(producer_bps=0, producer_ips=ips(60)), PARAMS)
        assert decision.verdict == mod.VERDICT_DECOMMISSION


class TestDecideRightsize:
    def test_disk_bound_shrink(self):
        # 60台 -> 磁盘 23040GB / (14000*60%) = 2.74 -> 3台；网络 4.64Gbps / (10Gbps*50%) = 0.93 -> 1台
        decision = mod.decide_cluster(make_inv(), make_peaks(), PARAMS)
        assert decision.verdict == mod.VERDICT_RIGHTSIZE
        assert decision.target_nodes == 3
        assert decision.binding_constraint == mod.CONSTRAINT_DISK
        assert decision.nodes_by_disk == 3
        assert decision.nodes_by_network == 1
        assert decision.reclaim_nodes == 57
        assert decision.projected_disk_pct == pytest.approx(23040 / (3 * 14000) * 100, abs=0.01)
        assert decision.projected_net_pct == pytest.approx(4.64e9 / (3 * 10000 * mod.BITS_PER_MBPS) * 100, abs=0.01)

    def test_network_bound_shrink(self):
        # 网络 6e10 / (10e9*50%) = 12台 > 磁盘 1台 > 下限3台
        decision = mod.decide_cluster(
            make_inv(nodes=20), make_peaks(host_net_bps=6e10, log_size_bytes=100 * GB), PARAMS
        )
        assert decision.verdict == mod.VERDICT_RIGHTSIZE
        assert decision.target_nodes == 12
        assert decision.binding_constraint == mod.CONSTRAINT_NETWORK
        assert decision.reclaim_nodes == 8

    def test_bandwidth_unit_is_the_rebalance_one_not_decimal_mbps(self):
        # 跟 rebalance 自动调速一致：1 Mbps = 1024*1024 bit/s。10000Mbps、水位50%时单机可承载 5242880000 bit/s，
        # 52428800000 bit/s 刚好需要10台；如果按 1e6 换算会算成11台
        decision = mod.decide_cluster(
            make_inv(nodes=20),
            make_peaks(host_net_bps=52428800000, log_size_bytes=GB),
            PARAMS,
        )
        assert decision.nodes_by_network == 10
        assert decision.target_nodes == 10

    def test_min_nodes_floor_binds_when_load_is_tiny(self):
        decision = mod.decide_cluster(make_inv(nodes=10), make_peaks(disk_used_bytes=GB, host_net_bps=1e6), PARAMS)
        assert decision.target_nodes == 3
        assert decision.binding_constraint == mod.CONSTRAINT_MIN_NODES

    def test_min_nodes_param_is_respected(self):
        params = mod.RightsizeParams(min_nodes=5)
        decision = mod.decide_cluster(make_inv(nodes=10), make_peaks(disk_used_bytes=GB, host_net_bps=1e6), params)
        assert decision.target_nodes == 5

    def test_exact_division_does_not_round_up(self):
        # 单机 1GB、目标 70% -> 单机可用 0.7GB；2.1GB / 0.7GB 在浮点下是 3.0000000000000004，恰好需要3台，不能多算成4台
        inv = make_inv(nodes=10, disk_gb_per_node=1)
        peaks = make_peaks(disk_used_bytes=2.1 * GB, host_net_bps=1e6)
        decision = mod.decide_cluster(inv, peaks, mod.RightsizeParams(disk_target_pct=70))
        assert decision.nodes_by_disk == 3

    @pytest.mark.parametrize("value, expected", [(3.0000000000000004, 3), (6.000000000000001, 6), (2.0, 2), (2.01, 3)])
    def test_ceil_ignores_float_noise_but_not_real_remainder(self, value, expected):
        assert mod._ceil(value) == expected

    def test_disk_is_sized_by_used_bytes_not_by_average_usage(self):
        # 评审给的反例：每台两个盘，100GB 用 0%、900GB 用 100%，10台实际占用 9000GB。
        # 平均使用率只有 50%，按它估算会得到 5000GB、9台；按已用字节算是 9000GB、15台
        inv = make_inv(nodes=10, disk_gb_per_node=1000)
        decision = mod.decide_cluster(inv, make_peaks(disk_used_bytes=9000 * GB, host_net_bps=1e6), PARAMS)
        assert decision.nodes_by_disk == 15  # ceil(9000 / 600)
        assert decision.verdict == mod.VERDICT_KEEP
        assert decision.reasons == [mod.REASON_ALREADY_RIGHT_SIZED]

    def test_log_size_does_not_affect_capacity(self):
        # 日志只有 10GB，但数据盘已用 5000GB（有残留数据）：必须按 5000GB 算
        inv = make_inv(nodes=10, disk_gb_per_node=1000)
        decision = mod.decide_cluster(
            inv, make_peaks(log_size_bytes=10 * GB, disk_used_bytes=5000 * GB, host_net_bps=1e6), PARAMS
        )
        assert decision.nodes_by_disk == 9  # ceil(5000 / 600)
        assert decision.target_nodes == 9
        assert decision.verdict == mod.VERDICT_RIGHTSIZE

    def test_log_size_alone_is_not_enough(self):
        # 磁盘已用字节缺失时不能退回用日志大小：日志大小不含残留数据，会低估
        decision = mod.decide_cluster(make_inv(), make_peaks(disk_used_bytes=None), PARAMS)
        assert (decision.verdict, decision.reasons) == (mod.VERDICT_UNCLEAR, [mod.REASON_METRICS_MISSING])

    def test_decision_does_not_project_cpu(self):
        assert not any("cpu" in name for name in vars(mod.decide_cluster(make_inv(), make_peaks(), PARAMS)))


class TestDecideKeepAndUnclear:
    def test_cpu_above_guard_keeps(self):
        decision = mod.decide_cluster(make_inv(), make_peaks(cpu_peak_pct=40.1), PARAMS)
        assert decision.verdict == mod.VERDICT_KEEP
        assert decision.reasons == [mod.REASON_CPU_GUARD]
        assert decision.reclaim_nodes == 0

    def test_cpu_equal_to_guard_is_not_blocked(self):
        decision = mod.decide_cluster(make_inv(), make_peaks(cpu_peak_pct=40.0), PARAMS)
        assert decision.verdict == mod.VERDICT_RIGHTSIZE

    def test_cpu_guard_param(self):
        decision = mod.decide_cluster(make_inv(), make_peaks(cpu_peak_pct=30), mod.RightsizeParams(cpu_guard_pct=25))
        assert decision.reasons == [mod.REASON_CPU_GUARD]

    def test_high_cpu_does_not_depend_on_node_count(self):
        # CPU 门槛看当前峰值，不做台数换算：3% 与 39% 都能缩，41% 都不能缩
        for cpu, verdict in [(3, mod.VERDICT_RIGHTSIZE), (39, mod.VERDICT_RIGHTSIZE), (41, mod.VERDICT_KEEP)]:
            assert mod.decide_cluster(make_inv(), make_peaks(cpu_peak_pct=cpu), PARAMS).verdict == verdict

    def test_already_right_sized(self):
        inv = make_inv(nodes=3, disk_gb_per_node=100)
        decision = mod.decide_cluster(inv, make_peaks(log_size_bytes=GB, host_net_bps=1e6), PARAMS)
        assert decision.verdict == mod.VERDICT_KEEP
        assert decision.reasons == [mod.REASON_ALREADY_RIGHT_SIZED]
        assert decision.reclaim_nodes == 0

    def test_cluster_below_min_nodes_is_kept_not_grown(self):
        inv = make_inv(nodes=2)
        decision = mod.decide_cluster(inv, make_peaks(log_size_bytes=GB, host_net_bps=1e6), PARAMS)
        assert decision.verdict == mod.VERDICT_KEEP
        assert decision.reclaim_nodes == 0

    def test_no_broker_is_unclear(self):
        decision = mod.decide_cluster(make_inv(nodes=0), make_peaks(), PARAMS)
        assert (decision.verdict, decision.reasons) == (mod.VERDICT_UNCLEAR, [mod.REASON_NO_BROKER])

    def test_missing_producer_metric_is_unclear_not_decommission(self):
        decision = mod.decide_cluster(make_inv(), make_peaks(producer_bps=None), PARAMS)
        assert (decision.verdict, decision.reasons) == (mod.VERDICT_UNCLEAR, [mod.REASON_METRICS_MISSING])

    @pytest.mark.parametrize(
        "overrides",
        [
            {"cpu_peak_pct": None},
            {"host_net_bps": None},
            {"disk_used_bytes": None},
        ],
    )
    def test_missing_required_metrics_are_unclear(self, overrides):
        decision = mod.decide_cluster(make_inv(), make_peaks(**overrides), PARAMS)
        assert (decision.verdict, decision.reasons) == (mod.VERDICT_UNCLEAR, [mod.REASON_METRICS_MISSING])

    @pytest.mark.parametrize("field", ["cpu_ips", "net_ips", "disk_ips"])
    @pytest.mark.parametrize("reporting", [None, [], ips(59)])
    def test_partial_coverage_of_decision_metrics_is_unclear(self, field, reporting):
        # CPU 取 max、网络和磁盘取 sum，少一台都会低估，不能据此建议缩容
        decision = mod.decide_cluster(make_inv(nodes=60), make_peaks(**{field: reporting}), PARAMS)
        assert (decision.verdict, decision.reasons) == (mod.VERDICT_UNCLEAR, [mod.REASON_METRICS_INCOMPLETE])
        assert decision.reclaim_nodes == 0

    def test_coverage_equal_to_node_count_is_complete(self):
        decision = mod.decide_cluster(
            make_inv(nodes=60), make_peaks(cpu_ips=ips(60), net_ips=ips(60), disk_ips=ips(60)), PARAMS
        )
        assert decision.verdict == mod.VERDICT_RIGHTSIZE

    def test_incomplete_coverage_is_reported_before_cpu_guard(self):
        # 少一台的 CPU 峰值可能漏掉最忙的那台，此时不能直接用它做 cpu_guard 的结论
        decision = mod.decide_cluster(make_inv(nodes=60), make_peaks(cpu_peak_pct=90, cpu_ips=ips(59)), PARAMS)
        assert decision.reasons == [mod.REASON_METRICS_INCOMPLETE]

    @pytest.mark.parametrize("field", ["producer_ips", "cpu_ips", "net_ips", "disk_ips"])
    def test_duplicate_or_foreign_reporters_cannot_hide_a_missing_broker(self, field):
        # 3台 broker 里 .3 没有在上报，但有两个外来的、重复的 IP 在报：按台数数是 4，按身份比对 .3 仍然缺失
        inv = make_inv(nodes=3)
        reported = ips(2) + ["127.9.9.9", "127.9.9.9", "127.9.9.8"]
        assert len(reported) >= inv.nodes
        decision = mod.decide_cluster(inv, make_peaks(**{field: reported}), PARAMS)
        assert (decision.verdict, decision.reasons) == (mod.VERDICT_UNCLEAR, [mod.REASON_METRICS_INCOMPLETE])
        assert mod.missing_brokers(inv, make_peaks(**{field: reported})) == {mod.COVERAGE_LABELS[field]: [ips(3)[2]]}

    def test_extra_reporters_outside_the_cluster_are_ignored_when_all_brokers_report(self):
        decision = mod.decide_cluster(
            make_inv(nodes=3),
            make_peaks(producer_ips=ips(3) + ["127.9.9.9"], cpu_ips=ips(3), net_ips=ips(3), disk_ips=ips(3)),
            PARAMS,
        )
        assert decision.verdict == mod.VERDICT_RIGHTSIZE or decision.reasons == [mod.REASON_ALREADY_RIGHT_SIZED]
        assert decision.reasons != [mod.REASON_METRICS_INCOMPLETE]

    def test_missing_brokers_reports_each_metric_and_treats_failed_query_as_all_missing(self):
        inv = make_inv(nodes=3)
        peaks = make_peaks(producer_ips=ips(3), cpu_ips=ips(2), net_ips=None, disk_ips=[])
        assert mod.missing_brokers(inv, peaks) == {"cpu": [ips(3)[2]], "host_net": ips(3), "disk": ips(3)}
        assert mod.reporting_broker_counts(inv, peaks) == {"producer": 3, "cpu": 2, "host_net": 0, "disk": 0}
        assert mod.missing_brokers(inv, make_peaks()) == {}

    def test_coverage_of_consumer_metric_is_not_required(self):
        # 消费流量只用来给 consumer_active 提示，不参与决策，没有覆盖校验
        decision = mod.decide_cluster(make_inv(), make_peaks(consumer_bps=None), PARAMS)
        assert decision.verdict == mod.VERDICT_RIGHTSIZE

    def test_unknown_bandwidth_is_unclear(self):
        decision = mod.decide_cluster(make_inv(bandwidth_mbps_per_node=None), make_peaks(), PARAMS)
        assert (decision.verdict, decision.reasons) == (mod.VERDICT_UNCLEAR, [mod.REASON_BANDWIDTH_UNKNOWN])

    def test_unknown_disk_capacity_is_unclear(self):
        decision = mod.decide_cluster(make_inv(disk_gb_per_node=0), make_peaks(), PARAMS)
        assert (decision.verdict, decision.reasons) == (mod.VERDICT_UNCLEAR, [mod.REASON_DISK_CAPACITY_UNKNOWN])


class TestPromql:
    def test_domain_selector_escapes_dots_for_promql_string(self):
        assert mod._domain_selector(["a.b-c.db", "x.y.db"]) == 'cluster_domain=~"a\\\\.b-c\\\\.db|x\\\\.y\\\\.db"'

    @pytest.mark.parametrize("metric", sorted(mod.PEAK_PROMQL))
    def test_peak_promql_wraps_subquery_and_fills_selector(self, metric):
        promql = mod._peak_promql(metric, ["a.test.db"], 30)
        assert promql.startswith("max_over_time(")
        assert promql.endswith("[30d:5m])")
        assert "__SEL__" not in promql
        assert 'cluster_domain=~"a\\\\.test\\\\.db"' in promql

    def test_host_net_uses_bit_gauges_without_rate(self):
        promql = mod._peak_promql("host_net_bps", ["a.test.db"], 7)
        assert "net:speed_sent_bit" in promql and "net:speed_recv_bit" in promql
        assert "rate(bkmonitor:dbm_system:net" not in promql
        assert "bytes_recv" not in promql and "bytes_sent" not in promql

    @pytest.mark.parametrize("name, table", [("disk_used_bytes", "PEAK_PROMQL"), ("disk_ips", "COVERAGE_PROMQL")])
    def test_disk_promql_keeps_data_disk_filter(self, name, table):
        promql = getattr(mod, table)[name]
        assert 'device_type=~"ext.?|xfs"' in promql
        assert 'mount_point!~"^(/|/usr/local)$"' in promql

    def test_disk_usage_is_used_bytes_deduped_by_host_and_mount_not_average_percent(self):
        promql = mod._peak_promql("disk_used_bytes", ["a.test.db"], 7)
        assert "bkmonitor:dbm_system:disk:used{" in promql
        assert "disk:in_use" not in promql and "avg by" not in promql
        assert "max by (cluster_domain, bk_target_ip, mount_point)" in promql
        assert promql.count("sum by (cluster_domain)") == 1

    def test_client_traffic_excludes_the_all_topics_series_to_avoid_double_counting(self):
        # 汇总序列和分 topic 序列并存，不过滤的话求和会翻倍
        for metric in ("producer_bps", "consumer_bps"):
            assert 'topic!=""' in mod.PEAK_PROMQL[metric]

    def test_every_metric_is_scoped_to_given_clusters_only(self):
        for table in (mod.PEAK_PROMQL, mod.COVERAGE_PROMQL):
            for metric in table:
                assert "__SEL__" in table[metric]

    @pytest.mark.parametrize("metric", sorted(mod.COVERAGE_PROMQL))
    def test_coverage_promql_returns_one_series_per_broker_without_subquery(self, metric):
        promql = mod._coverage_promql(metric, ["a.test.db"])
        # 不数台数：数台数会被重复序列凑够数，盖住真正缺失的 broker
        assert promql.startswith("max by (cluster_domain, ")
        assert "count by" not in promql and "sum by" not in promql
        assert "max_over_time" not in promql and "[" not in promql
        assert "__SEL__" not in promql
        assert 'cluster_domain=~"a\\\\.test\\\\.db"' in promql

    @pytest.mark.parametrize(
        "metric, label",
        [
            ("producer_ips", "instance"),
            ("cpu_ips", "bk_target_ip"),
            ("net_ips", "bk_target_ip"),
            ("disk_ips", "bk_target_ip"),
        ],
    )
    def test_coverage_promql_keeps_the_broker_identity_label(self, metric, label):
        promql = mod._coverage_promql(metric, ["a.test.db"])
        assert promql.startswith(f"max by (cluster_domain, {label})")

    def test_every_coverage_metric_has_an_output_label(self):
        assert set(mod.COVERAGE_LABELS) == set(mod.COVERAGE_PROMQL)

    def test_producer_coverage_uses_the_all_topics_series_and_never_sums_traffic(self):
        promql = mod._coverage_promql("producer_ips", ["a.test.db"])
        assert 'topic=""' in promql and 'topic!=""' not in promql
        assert "sum by" not in promql and "rate(" not in promql

    def test_net_coverage_requires_both_directions_like_host_net(self):
        promql = mod._coverage_promql("net_ips", ["a.test.db"])
        assert "net:speed_sent_bit" in promql and "net:speed_recv_bit" in promql
        assert "+ on (cluster_domain, bk_target_ip)" in promql


class TestCollectPeaks:
    def _series(self, domain, *values):
        return {"dimensions": {"cluster_domain": domain}, "datapoints": [[v, i] for i, v in enumerate(values)]}

    def test_takes_last_non_null_point_and_ignores_foreign_clusters(self, monkeypatch):
        monkeypatch.setattr(mod.env, "DBA_APP_BK_BIZ_ID", 20002)
        response = {
            "series": [
                self._series("a.test.db", 1, 5, None),
                self._series("other.test.db", 9),
                self._series("b.test.db", None),
            ]
        }
        with patch.object(mod.BKMonitorV3Api, "unify_query", return_value=response) as query:
            peaks, errors = mod.collect_peaks(["a.test.db", "b.test.db"], 30)

        assert errors == {}
        assert peaks["a.test.db"].producer_bps == 5
        assert peaks["b.test.db"].producer_bps is None
        assert "other.test.db" not in peaks
        assert query.call_count == len(mod.PEAK_PROMQL) + len(mod.COVERAGE_PROMQL)
        # 监控查询用监控空间，不是集群所属业务
        assert all(call.args[0]["bk_biz_id"] == 20002 for call in query.call_args_list)

    def test_batches_domains(self, monkeypatch):
        monkeypatch.setattr(mod, "QUERY_DOMAIN_BATCH_SIZE", 2)
        with patch.object(mod.BKMonitorV3Api, "unify_query", return_value={"series": []}) as query:
            mod.collect_peaks(["a.test.db", "b.test.db", "c.test.db"], 30)
        assert query.call_count == 2 * (len(mod.PEAK_PROMQL) + len(mod.COVERAGE_PROMQL))

    def test_failed_metric_is_reported_and_others_continue(self):
        def fake_query(params):
            if "bytesout_total" in params["query_configs"][0]["promql"]:
                raise RuntimeError("monitor unavailable")
            return {"series": [self._series("a.test.db", 3)]}

        with patch.object(mod.BKMonitorV3Api, "unify_query", side_effect=fake_query):
            peaks, errors = mod.collect_peaks(["a.test.db"], 30)

        assert errors == {"consumer_bps": "monitor unavailable"}
        assert peaks["a.test.db"].consumer_bps is None
        assert peaks["a.test.db"].producer_bps == 3

    def _broker_series(self, domain, label, value, *values):
        return {
            "dimensions": {"cluster_domain": domain, label: value},
            "datapoints": [[v, i] for i, v in enumerate(values or (1,))],
        }

    def test_coverage_collects_reporting_ips_per_metric(self):
        def fake_query(params):
            promql = params["query_configs"][0]["promql"]
            if promql.startswith("max by (cluster_domain, instance)"):
                # Kafka 的 JMX 指标没有主机标签，broker 靠 instance 标识，格式是 "IP-端口"
                return {
                    "series": [
                        self._broker_series("a.test.db", "instance", "127.0.0.1-9092"),
                        self._broker_series("a.test.db", "instance", "127.0.0.2-9092"),
                    ]
                }
            if promql.startswith("max by (cluster_domain, bk_target_ip) (bkmonitor:dbm_system:cpu_summary"):
                return {"series": [self._broker_series("a.test.db", "bk_target_ip", "127.0.0.2")]}
            return {"series": []}

        with patch.object(mod.BKMonitorV3Api, "unify_query", side_effect=fake_query):
            peaks, errors = mod.collect_peaks(["a.test.db"], 30)

        assert errors == {}
        assert peaks["a.test.db"].producer_ips == ["127.0.0.1", "127.0.0.2"]
        assert peaks["a.test.db"].cpu_ips == ["127.0.0.2"]

    def test_series_without_data_or_without_ip_or_from_other_clusters_are_not_reporting(self):
        response = {
            "series": [
                self._broker_series("a.test.db", "bk_target_ip", "127.0.0.1", None, None),  # 只有空点
                self._broker_series("a.test.db", "bk_target_ip", "127.0.0.2", None, 1),  # 最近有值
                {"dimensions": {"cluster_domain": "a.test.db"}, "datapoints": [[1, 0]]},  # 取不出 IP
                self._broker_series("other.test.db", "bk_target_ip", "127.0.0.3", 1),  # 不是本次评估的集群
            ]
        }
        with patch.object(mod.BKMonitorV3Api, "unify_query", return_value=response):
            peaks, _errors = mod.collect_peaks(["a.test.db"], 30)
        assert peaks["a.test.db"].cpu_ips == ["127.0.0.2"]
        assert "other.test.db" not in peaks

    def test_successful_query_without_series_means_no_broker_is_reporting(self):
        with patch.object(mod.BKMonitorV3Api, "unify_query", return_value={"series": []}):
            peaks, errors = mod.collect_peaks(["a.test.db"], 30)
        assert errors == {}
        assert peaks["a.test.db"].cpu_ips == [] and peaks["a.test.db"].producer_ips == []

    def test_failed_coverage_query_is_reported_and_leaves_coverage_unknown(self):
        def fake_query(params):
            promql = params["query_configs"][0]["promql"]
            if promql.startswith("max by (cluster_domain, bk_target_ip) (bkmonitor:dbm_system:cpu_summary"):
                raise RuntimeError("monitor unavailable")
            return {"series": []}

        with patch.object(mod.BKMonitorV3Api, "unify_query", side_effect=fake_query):
            peaks, errors = mod.collect_peaks(["a.test.db"], 30)
        assert errors == {"cpu_ips": "monitor unavailable"}
        assert peaks["a.test.db"].cpu_ips is None

    def test_truncated_series_is_an_error_not_a_list_of_missing_brokers(self):
        # 返回的series数顶到监控查询的 slimit，说明被截断了，"没看到的 broker"不能当成没上报
        slimit = mod.UNIFY_QUERY_PARAMS["slimit"]
        series = [
            self._broker_series("a.test.db", "bk_target_ip", f"127.0.{i // 250}.{i % 250 + 1}", 1)
            for i in range(slimit)
        ]
        with patch.object(mod.BKMonitorV3Api, "unify_query", return_value={"series": series}):
            peaks, errors = mod.collect_peaks(["a.test.db"], 30)
        assert "truncated" in errors["cpu_ips"]
        assert peaks["a.test.db"].cpu_ips is None

    def test_queries_are_batched_by_broker_count_too(self, monkeypatch):
        monkeypatch.setattr(mod, "QUERY_BROKER_BUDGET", 10)
        nodes = {"a.test.db": 6, "b.test.db": 6, "c.test.db": 3}
        with patch.object(mod.BKMonitorV3Api, "unify_query", return_value={"series": []}) as query:
            mod.collect_peaks(["a.test.db", "b.test.db", "c.test.db"], 30, nodes)
        # a 单独一批，b+c 一批：每个指标 2 次查询
        assert query.call_count == 2 * (len(mod.PEAK_PROMQL) + len(mod.COVERAGE_PROMQL))

    def test_empty_response_leaves_all_metrics_missing(self):
        with patch.object(mod.BKMonitorV3Api, "unify_query", return_value=None):
            peaks, errors = mod.collect_peaks(["a.test.db"], 30)
        assert errors == {}
        assert peaks["a.test.db"].producer_bps is None and peaks["a.test.db"].disk_used_bytes is None


class TestBatches:
    def test_splits_by_broker_budget_and_keeps_order(self, monkeypatch):
        monkeypatch.setattr(mod, "QUERY_BROKER_BUDGET", 10)
        assert list(mod._batches(["a", "b", "c"], {"a": 6, "b": 6, "c": 3})) == [["a"], ["b", "c"]]

    def test_a_single_oversized_cluster_gets_its_own_batch(self, monkeypatch):
        monkeypatch.setattr(mod, "QUERY_BROKER_BUDGET", 10)
        assert list(mod._batches(["a", "b", "c"], {"a": 3, "b": 50, "c": 3})) == [["a"], ["b"], ["c"]]

    def test_splits_by_domain_count(self, monkeypatch):
        monkeypatch.setattr(mod, "QUERY_DOMAIN_BATCH_SIZE", 2)
        assert list(mod._batches(["a", "b", "c"])) == [["a", "b"], ["c"]]

    def test_no_domains_no_batches(self):
        assert list(mod._batches([])) == []

    def test_every_domain_appears_exactly_once(self, monkeypatch):
        monkeypatch.setattr(mod, "QUERY_BROKER_BUDGET", 7)
        domains = [f"{i}.test.db" for i in range(30)]
        nodes = {d: (i % 5) + 1 for i, d in enumerate(domains)}
        batches = list(mod._batches(domains, nodes))
        assert [d for batch in batches for d in batch] == domains
        assert all(sum(nodes[d] for d in batch) <= 7 for batch in batches)


def make_spec(spec_id=1, cpu=96, mem=128, disks=(14000,)):
    return SimpleNamespace(
        pk=spec_id,
        spec_id=spec_id,
        cpu={"min": cpu},
        mem={"min": mem},
        storage_spec=[{"mount_point": f"/data{i}", "min": size} for i, size in enumerate(disks)],
    )


def make_instance(spec_id=1, ip="127.0.0.1"):
    return SimpleNamespace(machine=SimpleNamespace(spec_id=spec_id, ip=ip))


def make_relation(cluster_id=1, instance=None, spec_id=1, ip="127.0.0.1"):
    """StorageInstance.cluster 中间表的一行：(集群, 实例)"""
    return SimpleNamespace(cluster_id=cluster_id, storageinstance=instance or make_instance(spec_id, ip))


def make_cluster(cluster_id=1, domain="a.test.db", region="sh"):
    return SimpleNamespace(id=cluster_id, bk_biz_id=10, immute_domain=domain, alias=None, region=region)


THROUGH = StorageInstance.cluster.through


class TestCollectInventory:
    """
    用真实的 Django 模型构造查询，只拦截查询的执行，并把每条查询编译成 SQL。
    不能 mock 掉 StorageInstance/Cluster 这些模型：MagicMock 接受任意字段名，会让写错的字段（比如
    StorageInstance 上并不存在的 cluster_id）在单测里一路绿灯，到生产才报 FieldError。
    """

    def _run(self, clusters, relations, specs, city=None, biz_ids=(10,)):
        rows = {Cluster: clusters, THROUGH: relations, Spec: list(specs.values())}
        executed = []

        def fake_fetch_all(queryset):
            # 跟真实的 _fetch_all 一样，已经取过就不再重复"执行"，否则 list(qs) 会被算成两次查询
            if queryset._result_cache is None:
                executed.append((queryset.model, str(queryset.query)))
                queryset._result_cache = list(rows[queryset.model])

        with patch.object(QuerySet, "_fetch_all", fake_fetch_all):
            result = mod.collect_inventory(None if biz_ids is None else list(biz_ids), city)
        return result, executed

    def _sql(self, executed, model):
        return [sql for queried_model, sql in executed if queried_model is model]

    def test_builds_per_node_capacity_from_spec(self):
        result, _executed = self._run(
            [make_cluster()],
            [make_relation(ip="127.0.0.1"), make_relation(ip="127.0.0.2")],
            {1: make_spec(disks=(3500, 3500, 3500, 3500))},
        )
        assert len(result) == 1
        inv = result[0]
        assert (inv.nodes, inv.cpu_cores_per_node, inv.mem_gb_per_node) == (2, 96, 128)
        assert inv.disk_gb_per_node == 14000
        assert inv.broker_ips == ["127.0.0.1", "127.0.0.2"]
        assert inv.alias == ""

    def test_inventory_does_not_resolve_bandwidth(self):
        result, _executed = self._run([make_cluster()], [make_relation()], {1: make_spec()})
        assert result[0].bandwidth_mbps_per_node is None
        assert result[0].bandwidth_missing_ips == []

    def test_takes_the_smallest_node_when_specs_differ(self):
        result, _executed = self._run(
            [make_cluster()],
            [make_relation(spec_id=1, ip="127.0.0.1"), make_relation(spec_id=2, ip="127.0.0.2")],
            {1: make_spec(1, cpu=96, mem=128, disks=(14000,)), 2: make_spec(2, cpu=48, mem=64, disks=(7000,))},
        )
        inv = result[0]
        assert (inv.cpu_cores_per_node, inv.mem_gb_per_node, inv.disk_gb_per_node) == (48, 64, 7000)

    def test_node_without_spec_makes_capacity_unknown(self):
        result, _executed = self._run(
            [make_cluster()],
            [make_relation(spec_id=1, ip="127.0.0.1"), make_relation(spec_id=99, ip="127.0.0.2")],
            {1: make_spec()},
        )
        assert result[0].disk_gb_per_node == 0
        assert result[0].cpu_cores_per_node == 0

    def test_cluster_without_brokers_has_zero_nodes(self):
        result, _executed = self._run([make_cluster()], [], {})
        assert result[0].nodes == 0
        assert result[0].broker_ips == []

    def test_no_clusters_returns_empty_without_querying_instances(self):
        result, executed = self._run([], [], {})
        assert result == []
        assert [model for model, _sql in executed] == [Cluster]

    def test_brokers_are_grouped_by_their_own_cluster(self):
        result, _executed = self._run(
            [make_cluster(1, "a.test.db"), make_cluster(2, "b.test.db")],
            [
                make_relation(cluster_id=1, ip="127.0.0.1"),
                make_relation(cluster_id=2, ip="127.0.1.1"),
                make_relation(cluster_id=2, ip="127.0.1.2"),
            ],
            {1: make_spec()},
        )
        by_domain = {inv.immute_domain: inv for inv in result}
        assert by_domain["a.test.db"].broker_ips == ["127.0.0.1"]
        assert by_domain["b.test.db"].broker_ips == ["127.0.1.1", "127.0.1.2"]

    def test_instance_shared_by_several_clusters_is_counted_in_each(self):
        # StorageInstance.cluster 是多对多：同一个实例属于两个集群时，两个集群都要有它，不能只归到其中一个
        shared = make_instance(ip="127.0.0.9")
        result, _executed = self._run(
            [make_cluster(1, "a.test.db"), make_cluster(2, "b.test.db")],
            [make_relation(cluster_id=1, instance=shared), make_relation(cluster_id=2, instance=shared)],
            {1: make_spec()},
        )
        assert [inv.nodes for inv in result] == [1, 1]
        assert [inv.broker_ips for inv in result] == [["127.0.0.9"], ["127.0.0.9"]]

    def test_queries_resolve_on_real_models_and_filter_as_intended(self):
        _result, executed = self._run([make_cluster(7)], [make_relation(cluster_id=7)], {1: make_spec()})
        cluster_sql = self._sql(executed, Cluster)[0]
        assert "`bk_biz_id` IN (10)" in cluster_sql
        assert "`cluster_type` = kafka" in cluster_sql
        through_sql = self._sql(executed, THROUGH)[0]
        assert "`db_meta_storageinstance_cluster`.`cluster_id` IN (7)" in through_sql
        assert "`db_meta_storageinstance`.`instance_role` = broker" in through_sql
        assert "JOIN `db_meta_machine`" in through_sql  # select_related 到 machine，后面取 ip/spec_id 不会逐条查库
        assert len(self._sql(executed, Spec)) == 1

    def test_biz_scope_none_means_all_businesses_but_still_only_kafka(self):
        _result, executed = self._run([make_cluster()], [make_relation()], {1: make_spec()}, biz_ids=None)
        cluster_sql = self._sql(executed, Cluster)[0]
        # SELECT 的列里本来就有 bk_biz_id，要看的是 WHERE 里没有按业务过滤
        assert "`bk_biz_id` IN" not in cluster_sql
        assert "`cluster_type` = kafka" in cluster_sql

    def test_biz_scope_list_limits_to_those_businesses(self):
        _result, executed = self._run([make_cluster()], [make_relation()], {1: make_spec()}, biz_ids=(10, 11))
        assert "`bk_biz_id` IN (10, 11)" in self._sql(executed, Cluster)[0]

    def test_city_filter_is_applied_only_when_given(self):
        _result, executed = self._run([make_cluster()], [make_relation()], {1: make_spec()}, city=None)
        assert "logicalcity" not in self._sql(executed, Cluster)[0]

        _result, executed = self._run([make_cluster()], [make_relation()], {1: make_spec()}, city="sh")
        cluster_sql = self._sql(executed, Cluster)[0]
        # 集群登记的 region，或 broker 机器所在的逻辑城市，任一命中即可；联表后要去重
        assert "`region` = sh" in cluster_sql
        assert "`db_meta_logicalcity`.`name` = sh" in cluster_sql
        assert cluster_sql.startswith("SELECT DISTINCT")


class TestBandwidthPromql:
    def test_is_the_rebalance_expression_scoped_to_given_ips(self):
        promql = mod._bandwidth_promql(["127.0.0.1", "127.0.0.2"])
        selector = '{bk_target_ip=~"127\\\\.0\\\\.0\\\\.1|127\\\\.0\\\\.0\\\\.2"}'
        assert selector in promql
        # 去掉选择器后，跟均衡自动调速用的带宽表达式逐字一致
        assert promql.replace(selector, "") == mod.BANDWIDTH_PROMQL


class TestCollectBandwidth:
    def _steps(self, **by_ip):
        return 1, {ip.replace("_", "."): steps for ip, steps in by_ip.items()}

    def test_takes_the_latest_step_value(self):
        steps = self._steps(**{"127_0_0_1": {100: 5000.0, 200: 10000.0, 150: 7000.0}})
        with patch.object(mod, "_query_steps_by_ip", return_value=steps):
            result, errors = mod.collect_bandwidth(["127.0.0.1"])
        assert result == {"127.0.0.1": 10000.0}
        assert errors == {}

    def test_unconfigured_default_and_zero_are_not_valid_bandwidth(self):
        steps = self._steps(**{"127_0_0_1": {1: float(INT_MAX)}, "127_0_0_2": {1: 0.0}, "127_0_0_3": {1: 10000.0}})
        with patch.object(mod, "_query_steps_by_ip", return_value=steps):
            result, _errors = mod.collect_bandwidth(["127.0.0.1", "127.0.0.2", "127.0.0.3"])
        assert result == {"127.0.0.3": 10000.0}

    def test_ignores_ips_that_were_not_requested(self):
        steps = self._steps(**{"127_0_0_1": {1: 10000.0}, "127_9_9_9": {1: 10000.0}})
        with patch.object(mod, "_query_steps_by_ip", return_value=steps):
            result, _errors = mod.collect_bandwidth(["127.0.0.1"])
        assert result == {"127.0.0.1": 10000.0}

    def test_queries_monitor_space_with_scoped_promql_over_the_short_window(self, monkeypatch):
        monkeypatch.setattr(mod.env, "DBA_APP_BK_BIZ_ID", 20002)
        with patch.object(mod, "_query_steps_by_ip", return_value=(0, {})) as query:
            mod.collect_bandwidth(["127.0.0.1"])
        biz_id, promql, start, end = query.call_args.args
        assert biz_id == 20002
        assert promql == mod._bandwidth_promql(["127.0.0.1"])
        assert end - start == mod.BANDWIDTH_WINDOW_SECONDS

    def test_batches_and_dedupes_ips(self, monkeypatch):
        monkeypatch.setattr(mod, "QUERY_IP_BATCH_SIZE", 2)
        with patch.object(mod, "_query_steps_by_ip", return_value=(0, {})) as query:
            mod.collect_bandwidth(["127.0.0.3", "127.0.0.1", "127.0.0.2", "127.0.0.1"])
        assert query.call_count == 2

    def test_no_ips_does_not_query(self):
        with patch.object(mod, "_query_steps_by_ip") as query:
            assert mod.collect_bandwidth([]) == ({}, {})
        query.assert_not_called()

    def test_failed_batch_is_reported_and_other_batches_continue(self, monkeypatch):
        monkeypatch.setattr(mod, "QUERY_IP_BATCH_SIZE", 1)

        def fake_query(_biz_id, promql, _start, _end):
            if "127\\\\.0\\\\.0\\\\.1" in promql:
                raise RuntimeError("monitor unavailable")
            return self._steps(**{"127_0_0_2": {1: 10000.0}})

        with patch.object(mod, "_query_steps_by_ip", side_effect=fake_query):
            result, errors = mod.collect_bandwidth(["127.0.0.1", "127.0.0.2"])
        assert errors == {"bandwidth": "monitor unavailable"}
        assert result == {"127.0.0.2": 10000.0}


class TestApplyBandwidth:
    def test_takes_the_smallest_node_bandwidth(self):
        inv = make_inv(broker_ips=["127.0.0.1", "127.0.0.2"], bandwidth_mbps_per_node=None)
        mod.apply_bandwidth([inv], {"127.0.0.1": 10000.0, "127.0.0.2": 5000.0})
        assert inv.bandwidth_mbps_per_node == 5000.0
        assert inv.bandwidth_missing_ips == []

    def test_one_missing_node_makes_the_whole_cluster_unknown(self):
        inv = make_inv(broker_ips=["127.0.0.1", "127.0.0.2"])
        mod.apply_bandwidth([inv], {"127.0.0.1": 10000.0})
        assert inv.bandwidth_mbps_per_node is None
        assert inv.bandwidth_missing_ips == ["127.0.0.2"]
        assert mod.decide_cluster(inv, make_peaks(), PARAMS).reasons == [mod.REASON_BANDWIDTH_UNKNOWN]

    def test_cluster_without_broker_ips_is_left_alone(self):
        inv = make_inv(nodes=0, broker_ips=[], bandwidth_mbps_per_node=None)
        mod.apply_bandwidth([inv], {"127.0.0.1": 10000.0})
        assert inv.bandwidth_mbps_per_node is None
        assert inv.bandwidth_missing_ips == []


def patch_pipeline(inventories, peaks_by_domain, errors=None):
    return (
        patch.object(mod, "collect_inventory", return_value=inventories),
        patch.object(mod, "collect_peaks", return_value=(peaks_by_domain, errors or {})),
        patch.object(mod, "collect_bandwidth", return_value=({ip: 10000.0 for ip in ALL_IPS}, {})),
    )


class TestRightsizeEntry:
    def _fixture(self):
        invs = [
            make_inv(cluster_id=1, immute_domain="empty.test.db", nodes=4, bk_biz_id=10),
            make_inv(cluster_id=2, immute_domain="big.test.db", nodes=60, bk_biz_id=10),
            make_inv(cluster_id=3, immute_domain="busy.test.db", nodes=10, bk_biz_id=11),
            make_inv(cluster_id=4, immute_domain="nodata.test.db", nodes=5, bk_biz_id=11),
            make_inv(cluster_id=5, immute_domain="small.test.db", nodes=3, bk_biz_id=11, disk_gb_per_node=100),
        ]
        peaks = {
            "empty.test.db": make_peaks(producer_bps=0, consumer_bps=0),
            "big.test.db": make_peaks(),
            "busy.test.db": make_peaks(cpu_peak_pct=55),
            "nodata.test.db": mod.ClusterPeaks(),
            "small.test.db": make_peaks(log_size_bytes=GB, host_net_bps=1e6),
        }
        return invs, peaks

    def _run(self, **kwargs):
        invs, peaks = self._fixture()
        first, second, third = patch_pipeline(invs, peaks, kwargs.pop("errors", None))
        with first, second, third:
            return mod.kafka_cluster_rightsize([10, 11], **kwargs)

    def test_summary_covers_all_clusters(self):
        result = self._run()
        summary = result["summary"]
        assert summary["cluster_count"] == 5
        assert summary["by_verdict"] == {"decommission": 1, "rightsize": 1, "keep": 2, "unclear": 1}
        assert summary["reclaimable"]["decommission"]["nodes"] == 4
        assert summary["reclaimable"]["rightsize"]["nodes"] == 57
        assert summary["reclaimable"]["total"]["nodes"] == 61
        assert summary["reclaimable"]["total"]["cpu_cores"] == (4 + 57) * 96
        assert summary["reclaimable"]["total"]["memory_gb"] == (4 + 57) * 128

    def test_by_biz_breakdown(self):
        by_biz = {item["bk_biz_id"]: item for item in self._run()["summary"]["by_biz"]}
        assert by_biz[10] == {"bk_biz_id": 10, "clusters": 2, "actionable_clusters": 2, "nodes": 61}
        assert by_biz[11] == {"bk_biz_id": 11, "clusters": 3, "actionable_clusters": 0, "nodes": 0}

    def test_sorted_actionable_first_by_reclaim_then_unclear_and_keep_hidden_by_default(self):
        result = self._run()
        assert [c["immute_domain"] for c in result["clusters"]] == ["big.test.db", "empty.test.db", "nodata.test.db"]
        assert result["returned_cluster_count"] == 3

    def test_include_keep_returns_everything(self):
        result = self._run(include_keep=True)
        assert [c["immute_domain"] for c in result["clusters"]] == [
            "big.test.db",
            "empty.test.db",
            "nodata.test.db",
            "busy.test.db",
            "small.test.db",
        ]

    def test_limit_truncates_details_but_not_summary(self):
        result = self._run(include_keep=True, limit=2)
        assert len(result["clusters"]) == 2
        assert result["returned_cluster_count"] == 2
        assert result["summary"]["cluster_count"] == 5

    def test_query_errors_are_passed_through(self):
        assert self._run(errors={"host_net_bps": "boom"})["query_errors"] == {"host_net_bps": "boom"}

    def test_params_are_echoed(self):
        result = self._run(city="sh", days=7)
        assert result["params"] == {
            "window_days": 7,
            "city": "sh",
            "disk_target_percent": 60.0,
            "net_watermark_percent": 50.0,
            "cpu_guard_percent": 40.0,
            "min_nodes": 3,
        }

    def test_no_clusters_does_not_query_monitor(self):
        with patch.object(mod, "collect_inventory", return_value=[]), patch.object(mod, "collect_peaks") as peaks:
            result = mod.kafka_cluster_rightsize([10])
        peaks.assert_not_called()
        assert result["clusters"] == []
        assert result["summary"]["cluster_count"] == 0

    def test_item_content_for_rightsize(self):
        item = next(c for c in self._run()["clusters"] if c["immute_domain"] == "big.test.db")
        assert item["verdict"] == "rightsize"
        assert item["current"]["nodes"] == 60
        assert item["observed"]["log_size_gb"] == 1
        assert item["observed"]["disk_used_gb"] == 23040
        assert item["observed"]["reporting_brokers"] == {"producer": 60, "cpu": 60, "host_net": 60, "disk": 60}
        assert item["observed"]["missing_brokers"] == {}
        assert "disk_used_percent" not in item["observed"] and "disk_used_gb_estimate" not in item["observed"]
        assert item["recommendation"]["target_nodes"] == 3
        assert item["recommendation"]["binding_constraint"] == "disk"
        assert item["recommendation"]["reclaim"] == {
            "cpu_cores": 57 * 96,
            "memory_gb": 57 * 128,
            "disk_gb": 57 * 14000,
        }

    def test_output_matches_response_serializer(self):
        result = self._run(include_keep=True)
        serializer = KafkaClusterRightsizeOutputSerializer(data=result)
        assert serializer.is_valid(), serializer.errors


class TestRightsizeEntryBandwidth:
    def _invs(self):
        return [
            make_inv(
                cluster_id=1,
                immute_domain="ok.test.db",
                nodes=60,
                broker_ips=["127.0.0.1", "127.0.0.2"],
                bandwidth_mbps_per_node=None,
            ),
            make_inv(
                cluster_id=2,
                immute_domain="gap.test.db",
                nodes=60,
                broker_ips=["127.0.1.1", "127.0.1.2"],
                bandwidth_mbps_per_node=None,
            ),
        ]

    def test_collects_all_broker_ips_applies_bandwidth_and_merges_errors(self):
        peaks = {"ok.test.db": make_peaks(), "gap.test.db": make_peaks()}
        bandwidth = ({"127.0.0.1": 10000.0, "127.0.0.2": 10000.0, "127.0.1.1": 10000.0}, {"bandwidth": "partial"})
        with patch.object(mod, "collect_inventory", return_value=self._invs()), patch.object(
            mod, "collect_peaks", return_value=(peaks, {"cpu_peak_pct": "boom"})
        ), patch.object(mod, "collect_bandwidth", return_value=bandwidth) as collect:
            result = mod.kafka_cluster_rightsize([10], include_keep=True)

        assert sorted(collect.call_args.args[0]) == ["127.0.0.1", "127.0.0.2", "127.0.1.1", "127.0.1.2"]
        by_domain = {c["immute_domain"]: c for c in result["clusters"]}
        assert by_domain["ok.test.db"]["verdict"] == "rightsize"
        assert by_domain["ok.test.db"]["current"]["bandwidth_mbps_per_node"] == 10000.0
        assert by_domain["gap.test.db"]["verdict"] == "unclear"
        assert by_domain["gap.test.db"]["reasons"] == ["bandwidth_unknown"]
        assert by_domain["gap.test.db"]["current"]["bandwidth_missing_ips"] == ["127.0.1.2"]
        assert result["query_errors"] == {"cpu_peak_pct": "boom", "bandwidth": "partial"}
        assert KafkaClusterRightsizeOutputSerializer(data=result).is_valid()


class TestRightsizeEntryCoverage:
    def test_cluster_with_partial_reporting_is_unclear_end_to_end_and_not_counted_as_reclaimable(self):
        invs = [
            make_inv(cluster_id=1, immute_domain="full.test.db", nodes=60, bandwidth_mbps_per_node=10000),
            make_inv(cluster_id=2, immute_domain="partial.test.db", nodes=60, bandwidth_mbps_per_node=10000),
        ]
        peaks = {
            "full.test.db": make_peaks(),
            # 只有一台空闲 broker 在上报生产流量，聚合出来是0
            "partial.test.db": make_peaks(producer_bps=0, consumer_bps=0, producer_ips=ips(1)),
        }
        with patch.object(mod, "collect_inventory", return_value=invs), patch.object(
            mod, "collect_peaks", return_value=(peaks, {})
        ), patch.object(mod, "collect_bandwidth", return_value=({ip: 10000.0 for ip in ALL_IPS}, {})):
            result = mod.kafka_cluster_rightsize([10], include_keep=True)

        by_domain = {c["immute_domain"]: c for c in result["clusters"]}
        assert by_domain["partial.test.db"]["verdict"] == "unclear"
        assert by_domain["partial.test.db"]["reasons"] == ["metrics_incomplete"]
        assert by_domain["partial.test.db"]["observed"]["reporting_brokers"]["producer"] == 1
        assert by_domain["partial.test.db"]["observed"]["missing_brokers"]["producer"] == ips(60)[1:]
        assert result["summary"]["reclaimable"]["decommission"]["nodes"] == 0
        assert result["summary"]["by_verdict"]["unclear"] == 1
        assert KafkaClusterRightsizeOutputSerializer(data=result).is_valid()


class TestInputSerializer:
    def test_defaults(self):
        serializer = KafkaClusterRightsizeInputSerializer(data={})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data == {
            "days": 30,
            "disk_target_percent": 60,
            "net_watermark_percent": 50,
            "cpu_guard_percent": 40,
            "min_nodes": 3,
            "limit": 20,
            "include_keep": False,
        }

    @pytest.mark.parametrize(
        "data",
        [{"days": 0}, {"days": 31}, {"disk_target_percent": 99}, {"min_nodes": 0}, {"limit": 0}, {"limit": 201}],
    )
    def test_rejects_out_of_range(self, data):
        assert not KafkaClusterRightsizeInputSerializer(data=data).is_valid()


class TestRightsizeView:
    """
    直接调用装饰后的视图函数，走真实的 wrapper -> check_permissions 路径，只桩掉 IAM 和 DBA 身份判断。
    验证接线：不传业务只有 DBA 能调且不限业务；传了业务要过业务管理权限且只评估该业务。
    """

    IS_DBA = "backend.iam_app.handlers.drf_perm.mcp.DBAdministrator.is_dba"

    def _call(self, data, validated, is_dba=True, biz_manage=True):
        view = MagicMock()
        view.action = "cluster_rightsize"
        view.params_validate.return_value = validated
        request = SimpleNamespace(method="POST", data=data, query_params={}, user=SimpleNamespace(username="alice"))
        parsed = []

        def fake_biz_permission(perm, request_, view_):
            # 业务路径上，装饰器挂的鉴权解析函数要能从请求里解析出业务
            parsed.append(perm.mcp_auth_parser(request_, view_))
            return biz_manage

        # 本地 local.env 里 DEBUG_MCP=1 时装饰器会整个跳过权限校验，这里显式关掉，保证本地和 CI 行为一致
        with patch.object(decorators_mod.env, "DEBUG_MCP", False), patch.object(
            view_mod, "kafka_cluster_rightsize", return_value={"clusters": []}
        ) as impl, patch(self.IS_DBA, return_value=is_dba), patch.object(
            McpDBManagePermission, "has_permission", fake_biz_permission
        ):
            response = view_mod.KafkaMetricsMcpToolsViewSet.cluster_rightsize(view, request)
        return response, impl, parsed

    VALIDATED = dict(
        city="sh",
        days=7,
        disk_target_percent=60,
        net_watermark_percent=50,
        cpu_guard_percent=40,
        min_nodes=3,
        limit=20,
        include_keep=False,
    )

    def test_dba_without_biz_evaluates_all_businesses(self):
        response, impl, _parsed = self._call({}, dict(self.VALIDATED))
        assert response.data == {"clusters": []}
        assert impl.call_args.kwargs["bk_biz_ids"] is None
        assert impl.call_args.kwargs["city"] == "sh"
        assert impl.call_args.kwargs["days"] == 7

    def test_empty_string_biz_is_treated_as_no_biz_like_the_permission_class(self):
        _response, impl, _parsed = self._call({"bk_biz_id": ""}, dict(self.VALIDATED, bk_biz_id=""))
        assert impl.call_args.kwargs["bk_biz_ids"] is None

    def test_non_dba_without_biz_is_denied_and_nothing_is_queried(self):
        with pytest.raises(PermissionDenied):
            self._call({}, dict(self.VALIDATED), is_dba=False)

    def test_with_biz_only_that_biz_is_evaluated(self):
        _response, impl, parsed = self._call({"bk_biz_id": 123}, dict(self.VALIDATED, bk_biz_id=123), is_dba=False)
        assert impl.call_args.kwargs["bk_biz_ids"] == [123]
        assert parsed == [[123]]

    def test_with_biz_but_without_manage_permission_is_denied_even_for_dba(self):
        with pytest.raises(PermissionDenied):
            self._call({"bk_biz_id": 123}, dict(self.VALIDATED, bk_biz_id=123), is_dba=True, biz_manage=False)

    def test_biz_zero_never_widens_to_all_businesses(self):
        # 序列化器会拒绝 0，这里是纵深防御：就算 0 漏进视图，也只能是"指定了一个业务"，不能被当成"没传"而变成全业务评估
        _response, impl, _parsed = self._call({"bk_biz_id": 0}, dict(self.VALIDATED, bk_biz_id=0), is_dba=True)
        assert impl.call_args.kwargs["bk_biz_ids"] == [0]

    def test_biz_zero_is_rejected_by_the_input_serializer(self):
        # 0 在权限类里算"传了业务"，在视图里不能被当成"没传"，所以序列化器直接拒绝
        assert not KafkaClusterRightsizeInputSerializer(data={"bk_biz_id": 0}).is_valid()
        assert KafkaClusterRightsizeInputSerializer(data={"bk_biz_id": 1}).is_valid()
