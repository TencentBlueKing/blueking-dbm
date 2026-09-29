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
    @staticmethod
    def _query_router(utilization_response, bandwidth_response):
        """按promql内容区分两次查询：只查带宽的那条（没有speed_recv_bit）返回bandwidth_response，
        其余（利用率那条，以及按app查空后退回的第二次）都返回utilization_response。
        用内容而不是调用顺序来分流，避免新增一次"退回不带app"的查询后测试里side_effect顺序错位。"""

        def _fake_unify_query(query_params):
            promql = query_params["query_configs"][0]["promql"]
            return bandwidth_response if "speed_recv_bit" not in promql else utilization_response

        return _fake_unify_query

    @patch.object(mod, "Cluster")
    def test_no_brokers_returns_empty(self, mock_cluster_cls):
        cluster = MagicMock(immute_domain="kafka.test.db")
        cluster.storageinstance_set.filter.return_value = []
        mock_cluster_cls.objects.get.return_value = cluster

        assert mod.get_broker_bandwidth_utilization(100) == []

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_computes_utilization_per_broker(self, mock_cluster_cls, mock_bkmonitor, mock_app_cache):
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        broker2 = MagicMock()
        broker2.machine.ip = "127.0.0.2"
        cluster.storageinstance_set.filter.return_value = [broker1, broker2]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        # 两次unify_query依次是: 监控侧算好的利用率(recv/sent/bandwidth已join), dbm_bandwidth
        def _series(ip_values):
            return {
                "series": [
                    {"dimensions": {"bk_target_ip": ip}, "datapoints": [[val, 1000]]} for ip, val in ip_values.items()
                ]
            }

        promqls = []
        query_params_list = []

        def _capture_and_return(series_list):
            def _fake_unify_query(query_params):
                promqls.append(query_params["query_configs"][0]["promql"])
                query_params_list.append(query_params)
                return series_list.pop(0)

            return _fake_unify_query

        series_responses = [
            _series({"127.0.0.1": 0.8, "127.0.0.2": 0.08}),  # 利用率比值(broker1: 80%)
            _series({"127.0.0.1": 1500, "127.0.0.2": 1500}),  # dbm_bandwidth Mbps
        ]
        mock_bkmonitor.unify_query.side_effect = _capture_and_return(series_responses)

        results = mod.get_broker_bandwidth_utilization(100)
        by_ip = {r["bk_target_ip"]: r for r in results}

        assert by_ip["127.0.0.1"]["utilization_pct"] == pytest.approx(80.0, abs=0.1)
        assert by_ip["127.0.0.2"]["utilization_pct"] < by_ip["127.0.0.1"]["utilization_pct"]

        # 指标名称必须是speed_recv_bit/speed_sent_bit（Kafka Dashboard已验证是bit/s），
        # 不能是bytes_recv/bytes_sent那套counter指标名，也不能再用rate()包一层
        assert any("speed_recv_bit" in p for p in promqls)
        assert any("speed_sent_bit" in p for p in promqls)
        assert not any("bytes_recv" in p or "bytes_sent" in p for p in promqls)
        assert not any("rate(" in p for p in promqls)
        assert len(query_params_list) == 2
        assert all(params["bk_biz_id"] == 10001 for params in query_params_list)

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_utilization_promql_golden(self, mock_cluster_cls, mock_bkmonitor, mock_app_cache):
        """整条promql做golden断言：group_left后跟右操作数时不能加括号（加了会被解析成grouping label
        列表而不是右操作数，query直接语法报错、被sidecar的except吞掉，自动调速彻底失效）；
        分子用/1e6对齐DeviceClass.bandwidth的Mbps口径；三侧都套3m平滑（实测采集周期60s，
        [1m]窗口里只有一个样本、等于没平滑）。子串断言看不出这些问题。"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        cluster.storageinstance_set.filter.return_value = [broker1]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        promqls = []

        def _fake_unify_query(query_params):
            promqls.append(query_params["query_configs"][0]["promql"])
            return {"series": []}

        mock_bkmonitor.unify_query.side_effect = _fake_unify_query

        mod.get_broker_bandwidth_utilization(100)

        labels = 'app="dba",cluster_domain="kafka.test.db",instance_role="broker"'
        expected = (
            f"(max by (bk_target_ip) (avg_over_time(bkmonitor:dbm_system:net:speed_sent_bit{{{labels}}}[3m]))"
            f" + max by (bk_target_ip) (avg_over_time(bkmonitor:dbm_system:net:speed_recv_bit{{{labels}}}[3m])))"
            " / 1000000 / on(bk_target_ip) group_left max by (bk_target_ip)"
            " (avg_over_time(bkmonitor:script_dbm_bandwidth:dbm_bandwidth[3m]))"
        )
        assert promqls[0] == expected
        # 右操作数前不能有括号
        assert "group_left (" not in promqls[0]
        # 分母必须字面复用 BANDWIDTH_PROMQL，不能另写一份：否则"利用率分母"和"单独查带宽"
        # 可能用上不同的聚合算子/窗口，同一台机器两边算出来的带宽就不是同一个值了
        assert mod.BANDWIDTH_PROMQL in promqls[0]

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_falls_back_to_query_without_app_when_app_filter_matches_nothing(
        self, mock_cluster_cls, mock_bkmonitor, mock_app_cache
    ):
        """app口径一旦跟监控series上的实际值对不上，加了app会让所有broker都查不到数据、功能静默失效。
        按app查回0条series时必须自动退回不带app的查询，并把这次回退打进日志。"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        cluster.storageinstance_set.filter.return_value = [broker1]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        promqls = []
        reported = []

        def _fake_unify_query(query_params):
            promqls.append(query_params["query_configs"][0]["promql"])
            # 带app的利用率查询返回0条；退回后的查询有数据；带宽查询有数据
            if "app=" in promqls[-1]:
                return {"series": []}
            return {"series": [{"dimensions": {"bk_target_ip": "127.0.0.1"}, "datapoints": [[0.5, 1000]]}]}

        mock_bkmonitor.unify_query.side_effect = _fake_unify_query

        results = mod.get_broker_bandwidth_utilization(100, on_missing=reported.append)

        assert [r["bk_target_ip"] for r in results] == ["127.0.0.1"]
        assert "app=" not in promqls[1] and 'cluster_domain="kafka.test.db"' in promqls[1]
        assert any("退回不带app的查询" in msg for msg in reported), reported

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_series_with_null_last_datapoint_falls_back_to_earlier_step(
        self, mock_cluster_cls, mock_bkmonitor, mock_app_cache
    ):
        """末点为空是采集/计算延迟的常见现象（range查询最后一个step正好落在"现在"），
        不能因此把整轮判成数据不完整——应该回退到更早一个step取值，而不是跳过"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        cluster.storageinstance_set.filter.return_value = [broker1]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        def _series(value):
            return {
                "series": [
                    {
                        "dimensions": {"bk_target_ip": "127.0.0.1"},
                        "datapoints": [[value, 1000], [None, 2000]],  # 末点(2000)为空，前一点(1000)有值
                    }
                ]
            }

        mock_bkmonitor.unify_query.side_effect = self._query_router(_series(0.9), _series(1500))

        results = mod.get_broker_bandwidth_utilization(100)

        assert len(results) == 1
        assert results[0]["utilization_pct"] == 90.0
        assert results[0]["bandwidth_mbps"] == 1500

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_aligned_step_covers_as_many_brokers_as_possible(self, mock_cluster_cls, mock_bkmonitor, mock_app_cache):
        """对齐step取"覆盖broker最多"的那个：127.0.0.2晚一个step才有数据时，
        不能跟着它退到更早的step，也不能丢掉它——选两者都有的那个step"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1, broker2 = MagicMock(), MagicMock()
        broker1.machine.ip = "127.0.0.1"
        broker2.machine.ip = "127.0.0.2"
        cluster.storageinstance_set.filter.return_value = [broker1, broker2]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        def _series(points_by_ip):
            return {
                "series": [{"dimensions": {"bk_target_ip": ip}, "datapoints": pts} for ip, pts in points_by_ip.items()]
            }

        utilization = _series(
            {
                "127.0.0.1": [[0.9, 1000], [0.5, 2000], [0.4, 3000]],
                "127.0.0.2": [[None, 1000], [0.2, 2000], [0.1, 3000]],
            }
        )
        bandwidth = _series(
            {
                "127.0.0.1": [[1500, 1000], [1500, 2000], [1500, 3000]],
                "127.0.0.2": [[None, 1000], [1500, 2000], [1500, 3000]],
            }
        )
        mock_bkmonitor.unify_query.side_effect = self._query_router(utilization, bandwidth)

        results = mod.get_broker_bandwidth_utilization(100)
        by_ip = {r["bk_target_ip"]: r for r in results}

        # step=3000 两台都有数据，选它；127.0.0.1在step=3000的利用率是40%而不是90%
        assert set(by_ip) == {"127.0.0.1", "127.0.0.2"}
        assert by_ip["127.0.0.1"]["utilization_pct"] == 40.0
        assert by_ip["127.0.0.2"]["utilization_pct"] == 10.0

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_missing_reason_distinguishes_delayed_broker_from_absent_metric(
        self, mock_cluster_cls, mock_bkmonitor, mock_app_cache
    ):
        """整个窗口都没有 vs 对齐step上没有（采集延迟）要分开报，排查方向完全不同"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1, broker2, broker3 = MagicMock(), MagicMock(), MagicMock()
        broker1.machine.ip = "127.0.0.1"
        broker2.machine.ip = "127.0.0.2"
        broker3.machine.ip = "127.0.0.3"
        cluster.storageinstance_set.filter.return_value = [broker1, broker2, broker3]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        def _series(points_by_ip):
            return {
                "series": [{"dimensions": {"bk_target_ip": ip}, "datapoints": pts} for ip, pts in points_by_ip.items()]
            }

        # 127.0.0.1 正常；127.0.0.2 只在前一个step有值（延迟）；127.0.0.3 整个窗口都没有
        utilization = _series({"127.0.0.1": [[0.5, 2000]], "127.0.0.2": [[0.5, 1000]]})
        bandwidth = _series({"127.0.0.1": [[1500, 2000]], "127.0.0.2": [[1500, 1000]]})
        mock_bkmonitor.unify_query.side_effect = self._query_router(utilization, bandwidth)
        reported = []

        mod.get_broker_bandwidth_utilization(100, on_missing=reported.append)

        assert len(reported) == 1
        detail = reported[0]
        # 覆盖最多的step是1000（只有127.0.0.2），但它不含127.0.0.1；step=2000只含127.0.0.1。
        # 两种step各覆盖1台，取更新的那个(2000)，此时127.0.0.2算"采集延迟"
        assert "'127.0.0.2': '对齐step上bandwidth无数据（采集延迟）'" in detail, detail
        assert "'127.0.0.3': 'bandwidth指标整个窗口无数据'" in detail, detail
        assert "利用率查询2条series、带宽查询2条series" in detail, detail
        assert "对齐step=2000" in detail, detail

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_bandwidth_only_promql_golden(self, mock_cluster_cls, mock_bkmonitor, mock_app_cache):
        """单独查带宽那条的窗口也从3m改成过1m、又改回3m（实测采集周期60s，1m撑得住但没有平滑），
        一并锁住文本"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        cluster.storageinstance_set.filter.return_value = [broker1]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        promqls = []

        def _fake_unify_query(query_params):
            promqls.append(query_params["query_configs"][0]["promql"])
            value = 0.5 if "speed_recv_bit" in promqls[-1] else 1500
            return {"series": [{"dimensions": {"bk_target_ip": "127.0.0.1"}, "datapoints": [[value, 1000]]}]}

        mock_bkmonitor.unify_query.side_effect = _fake_unify_query

        mod.get_broker_bandwidth_utilization(100)

        # 覆盖率完整时不该多打一次"退回不带app"的查询，恰好两次
        assert len(promqls) == 2
        assert promqls[1] == "max by (bk_target_ip) (avg_over_time(bkmonitor:script_dbm_bandwidth:dbm_bandwidth[3m]))"
        # 测试里的分流依赖"利用率那条含speed_recv_bit"，哪天不再包含这个指标名，这里会先炸
        assert "speed_recv_bit" in promqls[0] and "speed_recv_bit" not in promqls[1]

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_missing_detail_message_is_rendered(self, mock_cluster_cls, mock_bkmonitor, mock_app_cache):
        """真实调用（只在监控接口这层mock），断言渲染出来的缺失明细文本：
        缺哪几台、缺的是哪一侧、两条查询各返回几条series、app解析成了什么"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1, broker2 = MagicMock(), MagicMock()
        broker1.machine.ip = "127.0.0.1"
        broker2.machine.ip = "127.0.0.2"
        cluster.storageinstance_set.filter.return_value = [broker1, broker2]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        def _series(ip_values):
            return {
                "series": [
                    {"dimensions": {"bk_target_ip": ip}, "datapoints": [[val, 1000]]} for ip, val in ip_values.items()
                ]
            }

        mock_bkmonitor.unify_query.side_effect = self._query_router(
            _series({"127.0.0.1": 0.5}),  # 利用率：只有127.0.0.1
            _series({"127.0.0.1": 1500}),  # 带宽：只有127.0.0.1
        )
        reported = []

        mod.get_broker_bandwidth_utilization(100, on_missing=reported.append)

        assert len(reported) == 1, reported
        detail = reported[0]
        assert "1/2台broker带宽监控数据不完整" in detail
        assert "{'127.0.0.2': 'bandwidth指标整个窗口无数据'}" in detail
        assert "利用率查询1条series、带宽查询1条series" in detail
        assert "对齐step=1000" in detail
        assert "app标签=dba" in detail

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_falls_back_when_app_filter_only_covers_part_of_brokers(
        self, mock_cluster_cls, mock_bkmonitor, mock_app_cache
    ):
        """app口径只对部分主机不匹配（业务改名过程中、只有部分机器标签缺失）时返回的是部分series，
        不能因为"不是0条"就不回退——只要覆盖不全就退回试一次，取覆盖更全的那次"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1, broker2 = MagicMock(), MagicMock()
        broker1.machine.ip = "127.0.0.1"
        broker2.machine.ip = "127.0.0.2"
        cluster.storageinstance_set.filter.return_value = [broker1, broker2]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        def _series(ip_values):
            return {
                "series": [
                    {"dimensions": {"bk_target_ip": ip}, "datapoints": [[val, 1000]]} for ip, val in ip_values.items()
                ]
            }

        # 带app只覆盖1台；不带app覆盖2台 -> 应采纳不带app的那次
        mock_bkmonitor.unify_query.side_effect = [
            _series({"127.0.0.1": 0.5}),  # 带app：只有1台
            _series({"127.0.0.1": 0.5, "127.0.0.2": 0.5}),  # 不带app：2台
            _series({"127.0.0.1": 1500, "127.0.0.2": 1500}),  # 带宽
        ]
        reported = []

        results = mod.get_broker_bandwidth_utilization(100, on_missing=reported.append)

        assert {r["bk_target_ip"] for r in results} == {"127.0.0.1", "127.0.0.2"}
        assert any("只覆盖1/2台broker" in msg for msg in reported), reported

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_disjoint_step_grids_reported_as_such_not_as_collection_delay(
        self, mock_cluster_cls, mock_bkmonitor, mock_app_cache
    ):
        """两条查询的step网格完全错开时，'每台broker都缺'的真正原因是没有共同step。
        不能让它落到按台明细里被说成'采集延迟'——那会把人往采集侧带。"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        cluster.storageinstance_set.filter.return_value = [broker1]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        def _series(ip_values):
            return {
                "series": [
                    {"dimensions": {"bk_target_ip": ip}, "datapoints": [[val, 1000]]} for ip, val in ip_values.items()
                ]
            }

        # 利用率只在 step=1000、带宽只在 step=2000(不同设备/不同采集源导致网格错开)
        mock_bkmonitor.unify_query.side_effect = [
            _series({"127.0.0.1": 0.5}),
            {"series": [{"dimensions": {"bk_target_ip": "127.0.0.1"}, "datapoints": [[1500, 2000]]}]},
        ]
        reported = []

        assert mod.get_broker_bandwidth_utilization(100, on_missing=reported.append) == []
        assert len(reported) == 1, reported
        assert "没有共同的step" in reported[0]
        assert "利用率1个step、带宽1个step" in reported[0]
        assert "采集延迟" not in reported[0]

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_intersecting_grids_without_overlapping_brokers_keep_per_broker_detail(
        self, mock_cluster_cls, mock_bkmonitor, mock_app_cache
    ):
        """网格有交集、但没有一台broker同时在两边同一个step上有数据时，覆盖数也是0，
        不能据此判成"没有共同的step"（step明明对得上）——这种情况按台明细才是准确的：
        A缺bandwidth、B缺recv/sent"""
        cluster = MagicMock(immute_domain="kafka.test.db", bk_biz_id=10001)
        broker1, broker2 = MagicMock(), MagicMock()
        broker1.machine.ip = "127.0.0.1"
        broker2.machine.ip = "127.0.0.2"
        cluster.storageinstance_set.filter.return_value = [broker1, broker2]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        def _series(ip_values):
            return {
                "series": [
                    {"dimensions": {"bk_target_ip": ip}, "datapoints": [[val, 1000]]} for ip, val in ip_values.items()
                ]
            }

        # 两边step都是1000（有交集），但利用率只有.1、带宽只有.2
        mock_bkmonitor.unify_query.side_effect = self._query_router(
            _series({"127.0.0.1": 0.5}), _series({"127.0.0.2": 1500})
        )
        reported = []

        assert mod.get_broker_bandwidth_utilization(100, on_missing=reported.append) == []
        assert len(reported) == 1, reported
        detail = reported[0]
        assert "没有共同的step" not in detail
        assert "'127.0.0.1': 'bandwidth指标整个窗口无数据'" in detail
        assert "'127.0.0.2': 'recv/sent指标整个窗口无数据'" in detail

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_broker_missing_bandwidth_metric_is_excluded(self, mock_cluster_cls, mock_bkmonitor, mock_app_cache):
        cluster = MagicMock(immute_domain="kafka.test.db")
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        cluster.storageinstance_set.filter.return_value = [broker1]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        mock_bkmonitor.unify_query.side_effect = self._query_router(
            {"series": []},  # 利用率: 无数据
            {"series": []},  # bandwidth: 无数据 -> 该broker应被跳过
        )

        assert mod.get_broker_bandwidth_utilization(100) == []

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_broker_with_only_recv_missing_is_excluded_not_treated_as_zero(
        self, mock_cluster_cls, mock_bkmonitor, mock_app_cache
    ):
        """recv/sent缺失时不能拿另一侧当0凑出偏低利用率，否则会误判为低利用率从而错误提速。
        合并成一条promql后，recv/sent缺失表现为利用率那条查不到该IP，但带宽单独查询仍有数据。"""
        cluster = MagicMock(immute_domain="kafka.test.db")
        broker1 = MagicMock()
        broker1.machine.ip = "127.0.0.1"
        cluster.storageinstance_set.filter.return_value = [broker1]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        def _series(ip_values):
            return {
                "series": [
                    {"dimensions": {"bk_target_ip": ip}, "datapoints": [[val, 1000]]} for ip, val in ip_values.items()
                ]
            }

        mock_bkmonitor.unify_query.side_effect = self._query_router(
            {"series": []},  # 利用率(recv/sent): 缺失
            _series({"127.0.0.1": 1500}),  # bandwidth: 有数据
        )

        assert mod.get_broker_bandwidth_utilization(100) == []

    @patch.object(mod, "AppCache")
    @patch.object(mod, "BKMonitorV3Api")
    @patch.object(mod, "Cluster")
    def test_all_brokers_incomplete_returns_empty(self, mock_cluster_cls, mock_bkmonitor, mock_app_cache):
        cluster = MagicMock(immute_domain="kafka.test.db")
        broker1, broker2 = MagicMock(), MagicMock()
        broker1.machine.ip = "127.0.0.1"
        broker2.machine.ip = "127.0.0.2"
        cluster.storageinstance_set.filter.return_value = [broker1, broker2]
        mock_cluster_cls.objects.get.return_value = cluster
        mock_app_cache.get_app_attr.return_value = "dba"

        mock_bkmonitor.unify_query.side_effect = self._query_router({"series": []}, {"series": []})

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

    @patch.object(mod, "get_broker_bandwidth_utilization", return_value=[])
    @patch.object(mod, "Cluster")
    def test_skip_reason_goes_through_callers_logger(self, mock_cluster_cls, mock_get_stats):
        """跳过原因要能交给调用方的日志通道（sidecar的log_warning带root_id/node_id，可按流程检索到），
        而不是只落在本模块不带extra的logger里——否则流程日志里只剩一句"暂无带宽监控数据"，没法排查"""
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(3)
        reported = []

        assert mod.get_rebalance_throttle_bounds(100, on_skip=reported.append) is None
        assert any("0/3" in msg for msg in reported), reported

    @patch.object(mod, "get_broker_bandwidth_utilization", return_value=[])
    @patch.object(mod, "Cluster")
    def test_missing_detail_logger_is_handed_to_bandwidth_query(self, mock_cluster_cls, mock_get_stats):
        """缺失明细（缺哪些IP、缺哪类指标）是在get_broker_bandwidth_utilization里发现的，
        on_skip必须原样透传给它，否则明细出不来"""
        mock_cluster_cls.objects.get.return_value = _cluster_with_broker_count(3)
        reporter = mod.logger.warning

        mod.get_rebalance_throttle_bounds(100, on_skip=reporter)

        mock_get_stats.assert_called_once_with(100, on_missing=reporter)
