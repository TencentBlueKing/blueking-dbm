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
# 本文件只测试脚本构造/解析/远程调用编排逻辑，全部通过mock隔离JobApi/BKMonitorV3Api/ORM，无需django_db标记。
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.flow.utils.kafka import rebalance_throttle_util as mod


class TestRunRemoteScript:
    @patch.object(mod, "get_job_exec_status")
    @patch.object(mod.JobApi, "fast_execute_script")
    def test_returns_log_content_when_finished(self, mock_fast_execute, mock_status):
        mock_fast_execute.return_value = {"job_instance_id": 1}
        mock_status.return_value = {
            "finished": True,
            "job_log_resp": [{"log_content": "line1"}, {"log_content": "line2"}],
        }

        output = mod._run_remote_script("127.0.0.1", 0, "echo 1", task_name="t")

        assert output == "line1\nline2"

    @patch.object(mod, "time")
    @patch.object(mod, "get_job_exec_status")
    @patch.object(mod.JobApi, "fast_execute_script")
    def test_raises_on_timeout(self, mock_fast_execute, mock_status, mock_time):
        mock_fast_execute.return_value = {"job_instance_id": 1}
        mock_status.return_value = {"finished": False, "job_log_resp": []}

        with pytest.raises(Exception, match="远程执行脚本超时"):
            mod._run_remote_script("127.0.0.1", 0, "echo 1", task_name="t")

        assert mock_status.call_count == mod.JOB_POLL_MAX_RETRIES


class TestReadRebalanceState:
    @patch.object(mod, "_run_remote_script")
    def test_all_three_files_present(self, mock_run):
        mock_run.return_value = '{"status": "in_progress"}\n___STATE___\n104857600\n___STATE___\nmanual'

        result = mod.read_rebalance_state("127.0.0.1", 0, 100)

        assert result == {
            "progress": '{"status": "in_progress"}',
            "throttle_rate": "104857600",
            "override_mode": "manual",
        }

    @patch.object(mod, "_run_remote_script")
    def test_all_three_files_missing(self, mock_run):
        mock_run.return_value = "__FILE_NOT_FOUND__\n___STATE___\n__FILE_NOT_FOUND__\n___STATE___\n__FILE_NOT_FOUND__"

        result = mod.read_rebalance_state("127.0.0.1", 0, 100)

        # override文件不存在时归一化为"auto"（默认自动模式），跟progress/throttle_rate的None语义不同——
        # 没设置过override本来就该走自动调速，不需要调用方再判断一次"None即auto"
        assert result == {"progress": None, "throttle_rate": None, "override_mode": "auto"}

    @patch.object(mod, "_run_remote_script")
    def test_override_file_with_invalid_content_falls_back_to_auto(self, mock_run):
        mock_run.return_value = '{"status": "pending"}\n___STATE___\n__FILE_NOT_FOUND__\n___STATE___\ngarbage'

        result = mod.read_rebalance_state("127.0.0.1", 0, 100)

        assert result["override_mode"] == "auto"

    @patch.object(mod, "_run_remote_script")
    def test_progress_present_throttle_missing(self, mock_run):
        mock_run.return_value = '{"status": "pending"}\n___STATE___\n__FILE_NOT_FOUND__\n___STATE___\nauto'

        result = mod.read_rebalance_state("127.0.0.1", 0, 100)

        assert result["progress"] == '{"status": "pending"}'
        assert result["throttle_rate"] is None

    @patch.object(mod, "_run_remote_script")
    def test_uses_uid_as_ticket_id_in_path(self, mock_run):
        mock_run.return_value = "__FILE_NOT_FOUND__\n___STATE___\n__FILE_NOT_FOUND__\n___STATE___\n__FILE_NOT_FOUND__"

        mod.read_rebalance_state("127.0.0.1", 0, 267)

        script = mock_run.call_args.args[2]
        assert "/data/install/dbactuator-267/progress.json" in script
        assert "/data/install/dbactuator-267/throttle_rate.txt" in script
        assert "/data/install/dbactuator-267/throttle_override.txt" in script

    @patch.object(mod, "_run_remote_script")
    def test_progress_read_error_raises_not_treated_as_not_found(self, mock_run):
        # 文件存在但读取失败（权限/磁盘异常）不能跟"文件不存在"混为一谈，否则真实的基础设施
        # 故障会被静默当成"rebalance还没跑到写文件的阶段"
        mock_run.return_value = "__FILE_READ_ERROR__\n___STATE___\n104857600\n___STATE___\nauto"

        with pytest.raises(Exception, match="远程读取progress.json失败"):
            mod.read_rebalance_state("127.0.0.1", 0, 100)

    @patch.object(mod, "_run_remote_script")
    def test_throttle_read_error_raises(self, mock_run):
        mock_run.return_value = '{"status": "in_progress"}\n___STATE___\n__FILE_READ_ERROR__\n___STATE___\nauto'

        with pytest.raises(Exception, match="远程读取throttle_rate.txt失败"):
            mod.read_rebalance_state("127.0.0.1", 0, 100)

    @patch.object(mod, "_run_remote_script")
    def test_override_read_error_raises(self, mock_run):
        mock_run.return_value = '{"status": "in_progress"}\n___STATE___\n104857600\n___STATE___\n__FILE_READ_ERROR__'

        with pytest.raises(Exception, match="远程读取throttle_override.txt失败"):
            mod.read_rebalance_state("127.0.0.1", 0, 100)


class TestSetManualThrottleRate:
    @patch.object(mod, "_run_remote_script")
    def test_writes_both_files_in_one_script(self, mock_run):
        mock_run.return_value = mod._WRITE_OK_MARKER

        mod.set_manual_throttle_rate("127.0.0.1", 0, 267, 104857600, max_throttle_bytes_per_sec=200 * 1024 * 1024)

        assert mock_run.call_count == 1
        script = mock_run.call_args.args[2]
        assert 'echo "104857600" > "/data/install/dbactuator-267/throttle_rate.txt.tmp"' in script
        assert 'echo "manual" > "/data/install/dbactuator-267/throttle_override.txt.tmp"' in script
        assert "set -e" in script

    @patch.object(mod, "_run_remote_script")
    def test_rejects_rate_below_min(self, mock_run):
        with pytest.raises(ValueError, match="超出合法范围"):
            mod.set_manual_throttle_rate(
                "127.0.0.1", 0, 267, mod.MIN_THROTTLE_BYTES_PER_SEC - 1, max_throttle_bytes_per_sec=200 * 1024 * 1024
            )

        mock_run.assert_not_called()

    @patch.object(mod, "_run_remote_script")
    def test_rejects_rate_above_dynamic_max(self, mock_run):
        max_throttle = 300 * 1024 * 1024
        with pytest.raises(ValueError, match="超出合法范围"):
            mod.set_manual_throttle_rate(
                "127.0.0.1", 0, 267, max_throttle + 1, max_throttle_bytes_per_sec=max_throttle
            )

        mock_run.assert_not_called()

    @patch.object(mod, "_run_remote_script")
    def test_raises_when_readback_verification_missing_from_output(self, mock_run):
        mock_run.return_value = "some unrelated output without the marker"

        with pytest.raises(Exception, match="人工限速写入校验失败"):
            mod.set_manual_throttle_rate("127.0.0.1", 0, 267, 104857600, max_throttle_bytes_per_sec=200 * 1024 * 1024)


class TestClearThrottleOverride:
    @patch.object(mod, "_run_remote_script")
    def test_removes_override_file(self, mock_run):
        mock_run.return_value = mod._WRITE_OK_MARKER

        mod.clear_throttle_override("127.0.0.1", 0, 267)

        script = mock_run.call_args.args[2]
        assert 'rm -f "/data/install/dbactuator-267/throttle_override.txt"' in script

    @patch.object(mod, "_run_remote_script")
    def test_raises_when_removal_not_verified(self, mock_run):
        mock_run.return_value = "some unrelated output without the marker"

        with pytest.raises(Exception, match="恢复自动调速失败"):
            mod.clear_throttle_override("127.0.0.1", 0, 267)


class TestWriteRemoteThrottleRate:
    @patch.object(mod, "_run_remote_script")
    def test_writes_via_atomic_tmp_then_mv(self, mock_run):
        mock_run.return_value = mod._WRITE_OK_MARKER

        mod.write_remote_throttle_rate("127.0.0.1", 0, 267, 104857600, max_throttle_bytes_per_sec=200 * 1024 * 1024)

        script = mock_run.call_args.args[2]
        assert 'echo "104857600" > "/data/install/dbactuator-267/throttle_rate.txt.tmp"' in script
        assert (
            'mv "/data/install/dbactuator-267/throttle_rate.txt.tmp" "/data/install/dbactuator-267/throttle_rate.txt"'
            in script
        )
        assert "set -e" in script

    @patch.object(mod, "_run_remote_script")
    def test_rejects_rate_below_min(self, mock_run):
        with pytest.raises(ValueError, match="超出合法范围"):
            mod.write_remote_throttle_rate(
                "127.0.0.1", 0, 267, mod.MIN_THROTTLE_BYTES_PER_SEC - 1, max_throttle_bytes_per_sec=200 * 1024 * 1024
            )

        mock_run.assert_not_called()

    @patch.object(mod, "_run_remote_script")
    def test_rejects_rate_above_dynamic_max(self, mock_run):
        max_throttle = 300 * 1024 * 1024
        with pytest.raises(ValueError, match="超出合法范围"):
            mod.write_remote_throttle_rate(
                "127.0.0.1", 0, 267, max_throttle + 1, max_throttle_bytes_per_sec=max_throttle
            )

        mock_run.assert_not_called()

    @patch.object(mod, "_run_remote_script")
    def test_raises_when_readback_verification_missing_from_output(self, mock_run):
        # Job "finished" 不代表脚本真的成功——mv失败/磁盘满等情况下，_run_remote_script仍可能
        # 正常返回（只是标准输出里没有_WRITE_OK_MARKER），此时必须视为写入失败
        mock_run.return_value = "some unrelated output without the marker"

        with pytest.raises(Exception, match="限速写入校验失败"):
            mod.write_remote_throttle_rate(
                "127.0.0.1", 0, 267, 104857600, max_throttle_bytes_per_sec=200 * 1024 * 1024
            )


class TestResolveAndValidateExecIp:
    @patch.object(mod, "Cluster")
    def test_valid_broker_returns_bk_cloud_id(self, mock_cluster_cls):
        cluster = MagicMock(bk_cloud_id=0, immute_domain="kafka.test.db", cluster_type=ClusterType.Kafka)
        cluster.storageinstance_set.filter.return_value.values_list.return_value = ["127.0.0.1", "127.0.0.2"]
        mock_cluster_cls.objects.get.return_value = cluster

        bk_cloud_id = mod.resolve_and_validate_exec_ip(100, "127.0.0.1")

        assert bk_cloud_id == 0

    @patch.object(mod, "Cluster")
    def test_ip_not_a_broker_raises(self, mock_cluster_cls):
        cluster = MagicMock(bk_cloud_id=0, immute_domain="kafka.test.db", cluster_type=ClusterType.Kafka)
        cluster.storageinstance_set.filter.return_value.values_list.return_value = ["127.0.0.1"]
        mock_cluster_cls.objects.get.return_value = cluster

        with pytest.raises(ValueError, match="不是集群"):
            mod.resolve_and_validate_exec_ip(100, "127.0.0.2")

    @patch.object(mod, "Cluster")
    def test_non_kafka_cluster_rejected(self, mock_cluster_cls):
        cluster = MagicMock(bk_cloud_id=0, immute_domain="mysql.test.db", cluster_type=ClusterType.TenDBHA)
        mock_cluster_cls.objects.get.return_value = cluster

        with pytest.raises(ValueError, match="不是Kafka集群"):
            mod.resolve_and_validate_exec_ip(100, "127.0.0.1")

        # 不是Kafka集群时应在校验broker列表之前就拒绝，不去查storageinstance_set
        cluster.storageinstance_set.filter.assert_not_called()

    @patch.object(mod, "Cluster")
    def test_cluster_not_found_propagates(self, mock_cluster_cls):
        mock_cluster_cls.DoesNotExist = Exception
        mock_cluster_cls.objects.get.side_effect = mock_cluster_cls.DoesNotExist

        with pytest.raises(Exception):
            mod.resolve_and_validate_exec_ip(999, "127.0.0.1")


class TestGetBrokerBandwidthUtilization:
    @patch.object(mod, "Cluster")
    def test_no_brokers_returns_empty(self, mock_cluster_cls):
        cluster = MagicMock(immute_domain="kafka.test.db")
        cluster.storageinstance_set.filter.return_value = []
        mock_cluster_cls.objects.get.return_value = cluster

        assert mod.get_broker_bandwidth_utilization(100) == []

    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_computes_utilization_per_broker(self, mock_cluster_cls, mock_bkmonitor):
        cluster = MagicMock(immute_domain="kafka.test.db")
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        broker2 = MagicMock()
        broker2.machine.ip = "127.0.0.2"
        cluster.storageinstance_set.filter.return_value = [broker1, broker2]
        mock_cluster_cls.objects.get.return_value = cluster

        # 三次unify_query依次是: speed_recv_bit, speed_sent_bit, dbm_bandwidth
        def _series(ip_values):
            return {
                "series": [
                    {"dimensions": {"bk_target_ip": ip}, "datapoints": [[val, 1000]]} for ip, val in ip_values.items()
                ]
            }

        promqls = []

        def _capture_and_return(series_list):
            def _fake_unify_query(query_params):
                promqls.append(query_params["query_configs"][0]["promql"])
                return series_list.pop(0)

            return _fake_unify_query

        series_responses = [
            _series({"127.0.0.1": 800 * 1024 * 1024, "127.0.0.2": 80 * 1024 * 1024}),  # speed_recv_bit (bit/s)
            _series({"127.0.0.1": 400 * 1024 * 1024, "127.0.0.2": 40 * 1024 * 1024}),  # speed_sent_bit (bit/s)
            _series({"127.0.0.1": 1500, "127.0.0.2": 1500}),  # dbm_bandwidth Mbps
        ]
        mock_bkmonitor.unify_query.side_effect = _capture_and_return(series_responses)

        results = mod.get_broker_bandwidth_utilization(100)
        by_ip = {r["bk_target_ip"]: r for r in results}

        # broker1: (800+400)Mibit/s / 1500Mbps = 80%，broker2远低于此
        assert by_ip["127.0.0.1"]["utilization_pct"] == pytest.approx(80.0, abs=0.1)
        assert by_ip["127.0.0.2"]["utilization_pct"] < by_ip["127.0.0.1"]["utilization_pct"]

        # 指标名称必须是speed_recv_bit/speed_sent_bit（Kafka Dashboard已验证是bit/s），
        # 不能是bytes_recv/bytes_sent那套counter指标名，也不能再用rate()包一层
        assert any("speed_recv_bit" in p for p in promqls)
        assert any("speed_sent_bit" in p for p in promqls)
        assert not any("bytes_recv" in p or "bytes_sent" in p for p in promqls)
        assert not any("rate(" in p for p in promqls)

    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_broker_missing_bandwidth_metric_is_excluded(self, mock_cluster_cls, mock_bkmonitor):
        cluster = MagicMock(immute_domain="kafka.test.db")
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        cluster.storageinstance_set.filter.return_value = [broker1]
        mock_cluster_cls.objects.get.return_value = cluster

        mock_bkmonitor.unify_query.side_effect = [
            {"series": []},  # recv: 无数据
            {"series": []},  # sent: 无数据
            {"series": []},  # bandwidth: 无数据 -> 该broker应被跳过
        ]

        assert mod.get_broker_bandwidth_utilization(100) == []

    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_broker_with_only_recv_missing_is_excluded_not_treated_as_zero(self, mock_cluster_cls, mock_bkmonitor):
        """一侧指标缺失不能拿另一侧当0凑出偏低利用率，否则会误判为低利用率从而错误提速"""
        cluster = MagicMock(immute_domain="kafka.test.db")
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        cluster.storageinstance_set.filter.return_value = [broker1]
        mock_cluster_cls.objects.get.return_value = cluster

        def _series(ip_values):
            return {
                "series": [
                    {"dimensions": {"bk_target_ip": ip}, "datapoints": [[val, 1000]]} for ip, val in ip_values.items()
                ]
            }

        mock_bkmonitor.unify_query.side_effect = [
            {"series": []},  # recv: 缺失
            _series({"127.0.0.1": 400 * 1024 * 1024}),  # sent: 有数据
            _series({"127.0.0.1": 1500}),  # bandwidth: 有数据
        ]

        assert mod.get_broker_bandwidth_utilization(100) == []

    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_all_brokers_incomplete_returns_empty(self, mock_cluster_cls, mock_bkmonitor):
        cluster = MagicMock(immute_domain="kafka.test.db")
        broker1, broker2 = MagicMock(), MagicMock()
        broker1.machine.ip = "127.0.0.1"
        broker2.machine.ip = "127.0.0.2"
        cluster.storageinstance_set.filter.return_value = [broker1, broker2]
        mock_cluster_cls.objects.get.return_value = cluster

        mock_bkmonitor.unify_query.side_effect = [
            {"series": []},
            {"series": []},
            {"series": []},
        ]

        assert mod.get_broker_bandwidth_utilization(100) == []


def _cluster_with_broker_count(count):
    cluster = MagicMock()
    cluster.storageinstance_set.filter.return_value.count.return_value = count
    return cluster


class TestGetRebalanceThrottleBounds:
    @patch.object(mod, "get_broker_bandwidth_utilization")
    @patch.object(mod, "Cluster")
    def test_utilization_is_max_across_brokers(self, mock_cluster_cls, mock_get_stats):
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(2)
        mock_get_stats.return_value = [
            {"bk_target_ip": "127.0.0.1", "utilization_pct": 40.0, "bandwidth_mbps": 1500},
            {"bk_target_ip": "127.0.0.2", "utilization_pct": 92.5, "bandwidth_mbps": 1500},
        ]

        bounds = mod.get_rebalance_throttle_bounds(100)

        assert bounds["utilization_pct"] == 92.5

    @patch.object(mod, "get_broker_bandwidth_utilization")
    @patch.object(mod, "Cluster")
    def test_max_throttle_is_ratio_of_min_broker_bandwidth(self, mock_cluster_cls, mock_get_stats):
        # 两台broker规格不一致时，动态上限必须按更慢的那台算——木桶效应，
        # 按更快的那台算会让限速上限超过慢broker的实际承载能力
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(2)
        mock_get_stats.return_value = [
            {"bk_target_ip": "127.0.0.1", "utilization_pct": 10.0, "bandwidth_mbps": 1500},  # 1.5Gbps
            {"bk_target_ip": "127.0.0.2", "utilization_pct": 10.0, "bandwidth_mbps": 10000},  # 10Gbps
        ]

        bounds = mod.get_rebalance_throttle_bounds(100)

        # 1500Mbps * 1024*1024/8 * 0.7，留30%给客户端流量
        expected = int(1500 * 1024 * 1024 / 8 * mod.MAX_THROTTLE_BANDWIDTH_RATIO)
        assert bounds["max_throttle_bytes_per_sec"] == expected

    @patch.object(mod, "get_broker_bandwidth_utilization")
    @patch.object(mod, "Cluster")
    def test_large_broker_bandwidth_allows_high_throttle_ceiling(self, mock_cluster_cls, mock_get_stats):
        # 之前写死200MB/s上限的bug：10Gbps broker的合理上限应该远高于200MB/s，
        # 不能被一个固定猜测值卡住
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(1)
        mock_get_stats.return_value = [
            {"bk_target_ip": "127.0.0.1", "utilization_pct": 10.0, "bandwidth_mbps": 10000},  # 10Gbps
        ]

        bounds = mod.get_rebalance_throttle_bounds(100)

        assert bounds["max_throttle_bytes_per_sec"] > 200 * 1024 * 1024

    @patch.object(mod, "get_broker_bandwidth_utilization")
    @patch.object(mod, "Cluster")
    def test_small_broker_bandwidth_keeps_ceiling_within_physical_capacity(self, mock_cluster_cls, mock_get_stats):
        # 之前写死200MB/s(~1.6-1.68Gbps)的bug：已经超过1.5Gbps最小规格broker的物理带宽，
        # 等于没有上限保护。动态上限必须严格小于broker实际带宽
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(1)
        mock_get_stats.return_value = [
            {"bk_target_ip": "127.0.0.1", "utilization_pct": 10.0, "bandwidth_mbps": 1500},  # 1.5Gbps
        ]

        bounds = mod.get_rebalance_throttle_bounds(100)
        broker_bandwidth_bytes_per_sec = 1500 * 1024 * 1024 / 8

        assert bounds["max_throttle_bytes_per_sec"] < broker_bandwidth_bytes_per_sec

    @patch.object(mod, "get_broker_bandwidth_utilization")
    @patch.object(mod, "Cluster")
    def test_dynamic_max_never_below_min_floor(self, mock_cluster_cls, mock_get_stats):
        # 极端情况下（带宽指标异常小）动态上限也不能低于MIN_THROTTLE_BYTES_PER_SEC这个绝对下限
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(1)
        mock_get_stats.return_value = [
            {"bk_target_ip": "127.0.0.1", "utilization_pct": 10.0, "bandwidth_mbps": 1},
        ]

        bounds = mod.get_rebalance_throttle_bounds(100)

        assert bounds["max_throttle_bytes_per_sec"] >= mod.MIN_THROTTLE_BYTES_PER_SEC

    @patch.object(mod, "get_broker_bandwidth_utilization")
    @patch.object(mod, "Cluster")
    def test_returns_none_when_no_brokers_in_cluster(self, mock_cluster_cls, mock_get_stats):
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(0)

        assert mod.get_rebalance_throttle_bounds(100) is None
        # 集群没有broker时应该在查带宽利用率之前就短路返回，不用再多打一次监控查询
        mock_get_stats.assert_not_called()

    @patch.object(mod, "get_broker_bandwidth_utilization", return_value=[])
    @patch.object(mod, "Cluster")
    def test_returns_none_when_all_brokers_missing_data(self, mock_cluster_cls, mock_get_stats):
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(3)

        assert mod.get_rebalance_throttle_bounds(100) is None

    @patch.object(mod, "get_broker_bandwidth_utilization")
    @patch.object(mod, "Cluster")
    def test_returns_none_when_some_brokers_missing_data(self, mock_cluster_cls, mock_get_stats):
        # 集群有3台broker，但只有2台监控数据完整——不能只用这2台数据继续算：
        # 缺数据的那台可能恰好是热点（漏看会误判为"利用率不高"从而错误提速），
        # 也可能恰好是带宽最低的那台（漏看会让动态上限被其他broker的数据高估）
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(3)
        mock_get_stats.return_value = [
            {"bk_target_ip": "127.0.0.1", "utilization_pct": 40.0, "bandwidth_mbps": 1500},
            {"bk_target_ip": "127.0.0.2", "utilization_pct": 50.0, "bandwidth_mbps": 1500},
        ]

        assert mod.get_rebalance_throttle_bounds(100) is None
