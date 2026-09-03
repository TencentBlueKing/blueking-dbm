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
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType, InstanceStatus
from backend.db_report.enums import ReportStateType

pytestmark = pytest.mark.django_db


class TestBuildPromqlRegexPattern:
    def test_joins_values(self, check_exporter):
        assert check_exporter.build_promql_regex_pattern(["aa", "bb"]) == "^(aa|bb)$"

    def test_single_value(self, check_exporter):
        assert check_exporter.build_promql_regex_pattern(["127.0.0.1"]) == "^(127.0.0.1)$"


class TestNodeAddrHelpers:
    def test_node_to_addr(self, check_exporter):
        node = {"ip": "127.0.0.1", "port": 6379}
        assert check_exporter._node_to_addr(node) == "127.0.0.1:6379"

    def test_addr_to_node_roundtrip(self, check_exporter):
        addr = "127.0.0.1:6380"
        node = check_exporter._addr_to_node(addr)
        assert check_exporter._node_to_addr(node) == addr


class TestGetProxyType:
    def test_twemproxy(self, check_exporter):
        cluster = MagicMock()
        cluster.cluster_type = "TwemproxyRedisInstance"
        assert check_exporter.get_proxy_type(cluster) == "twemproxy"

    def test_predixy(self, check_exporter):
        cluster = MagicMock()
        cluster.cluster_type = "PredixyTendisSSDInstance"
        assert check_exporter.get_proxy_type(cluster) == "predixy"

    def test_empty(self, check_exporter):
        cluster = MagicMock()
        cluster.cluster_type = ClusterType.TendisRedisInstance.value
        assert check_exporter.get_proxy_type(cluster) == ""


class TestGetProxyMetricsName:
    def test_twemproxy(self, check_exporter):
        assert "twemproxy" in check_exporter.get_proxy_metrics_name("TwemproxyRedisInstance").lower()

    def test_predixy(self, check_exporter):
        assert "predixy" in check_exporter.get_proxy_metrics_name("PredixyCluster").lower()

    def test_unknown(self, check_exporter):
        assert check_exporter.get_proxy_metrics_name(ClusterType.TendisRedisInstance.value) == ""


class TestUpMetricPromql:
    def test_redis_up_uses_sum_not_count(self, check_exporter):
        q = check_exporter._promql_redis_up_by_cluster("r.test.db")
        assert "sum by" in q
        assert "count by" not in q
        q_ip = check_exporter._promql_redis_up_by_iplist(["127.0.0.1"])
        assert "sum by" in q_ip
        assert "count by" not in q_ip

    def test_proxy_up_uses_sum_not_count(self, check_exporter):
        metric = check_exporter.get_proxy_metrics_name("TwemproxyRedisInstance")
        q = check_exporter._promql_proxy_up_by_cluster(metric, "r.test.db")
        assert "sum by" in q
        assert "count by" not in q
        assert "twemproxy_up" in q
        q_ip = check_exporter._promql_proxy_up_by_iplist(metric, ["127.0.0.2"])
        assert "sum by" in q_ip
        assert "count by" not in q_ip


class TestShortAddrList:
    def test_single_port(self, check_exporter):
        nodes = [{"ip": "1.1.1.1", "port": 6379}]
        assert check_exporter._short_addr_list(nodes) == ["1.1.1.1:6379"]

    def test_continuous_ports_same_ip(self, check_exporter):
        nodes = [
            {"ip": "1.1.1.1", "port": 6379},
            {"ip": "1.1.1.1", "port": 6380},
        ]
        assert check_exporter._short_addr_list(nodes) == ["1.1.1.1:6379-6380"]

    def test_non_continuous_ports_same_ip(self, check_exporter):
        nodes = [
            {"ip": "1.1.1.1", "port": 6379},
            {"ip": "1.1.1.1", "port": 6381},
        ]
        out = check_exporter._short_addr_list(nodes)
        assert "1.1.1.1:6379" in out
        assert "1.1.1.1:6381" in out

    def test_sorts_by_ip_port(self, check_exporter):
        nodes = [
            {"ip": "2.2.2.2", "port": 100},
            {"ip": "1.1.1.1", "port": 200},
        ]
        assert check_exporter._short_addr_list(nodes) == ["1.1.1.1:200", "2.2.2.2:100"]


class TestCheckRedisUpMetricTaskHelpers:
    def test_instance_role_to_exporter_prefix(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        assert task._instance_role_to_exporter_prefix("redis_master") == "redis_master"
        assert task._instance_role_to_exporter_prefix("redis_slave") == "redis_slave"
        assert task._instance_role_to_exporter_prefix("twemproxy") == "twemproxy"
        assert task._instance_role_to_exporter_prefix("predixy") == "predixy"
        assert task._instance_role_to_exporter_prefix("custom") == "custom"

    def test_is_skip_check_temporary_true(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = MagicMock()
        tag = MagicMock()
        tag.key = "temporary"
        tag.value = "true"
        cluster.tags.all.return_value = [tag]
        skip, reason = task.is_skip_check(cluster)
        assert skip is True
        assert "temporary" in reason

    def test_is_skip_check_not_temporary(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = MagicMock()
        tag = MagicMock()
        tag.key = "other"
        tag.value = "x"
        cluster.tags.all.return_value = [tag]
        skip, reason = task.is_skip_check(cluster)
        assert skip is False
        assert reason == ""

    def test_is_skip_check_no_tags(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = MagicMock()
        cluster.tags = None
        skip, reason = task.is_skip_check(cluster)
        assert skip is False


class TestCheckNodesMetric:
    def test_all_ok_running(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"},
        ]
        metric_val = {"127.0.0.1:6379": {"value": 1}}
        msg_list = task._check_nodes_metric(nodes, metric_val, "")
        assert set(msg_list.keys()) == {"ok"}
        assert len(msg_list["ok"]) == 1

    def test_exporter_down_running_node(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"},
        ]
        metric_val = {"127.0.0.1:6379": {"value": 0}}
        msg_list = task._check_nodes_metric(nodes, metric_val, "")
        keys = [k for k in msg_list if k != "ok"]
        assert any("exporter_down" in k for k in keys)

    def test_mixed_up_zero_and_one_is_down(self, check_exporter):
        """同一 addr 同时有 up=0 与 up=1 时按 down，不能被合计为 1 后判 ok。"""
        task = check_exporter.CheckRedisUpMetricTask()
        nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"},
        ]
        metric_val = {
            "127.0.0.1:6379": [
                {"value": 0, "instance_role": "redis_master"},
                {"value": 1, "instance_role": "redis_master"},
            ],
        }
        msg_list = task._check_nodes_metric(nodes, metric_val, "")
        assert any("exporter_down" in k for k in msg_list)

    def test_duplicate_metric(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"},
        ]
        metric_val = {"127.0.0.1:6379": {"value": 2}}
        msg_list = task._check_nodes_metric(nodes, metric_val, "")
        assert any("duplicate" in k for k in msg_list)

    def test_same_addr_multiple_series_sums_value(self, check_exporter):
        """_instant_query_metric 同一 ip:port 多条 series 时 value 合并为求和，用于 duplicate 判定。"""
        task = check_exporter.CheckRedisUpMetricTask()
        nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"},
        ]
        metric_val = {
            "127.0.0.1:6379": [
                {"value": 1, "instance_role": "redis_master"},
                {"value": 1, "instance_role": "redis_master"},
            ],
        }
        msg_list = task._check_nodes_metric(nodes, metric_val, "")
        assert any("duplicate" in k for k in msg_list)

    def test_same_addr_master_and_slave_is_mixed_role(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"},
        ]
        metric_val = {
            "127.0.0.1:6379": [
                {"value": 1, "instance_role": "redis_master"},
                {"value": 1, "instance_role": "redis_slave"},
            ],
        }
        msg_list = task._check_nodes_metric(nodes, metric_val, "")
        assert "redis_exporter_mixed_role" in msg_list
        assert not any("duplicate" in k for k in msg_list)

    def test_same_host_different_ports_master_and_slave_is_mixed_role(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"},
            {"ip": "127.0.0.1", "port": 6380, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_slave"},
        ]
        metric_val = {
            "127.0.0.1:6379": [{"value": 1, "instance_role": "redis_master"}],
            "127.0.0.1:6380": [{"value": 1, "instance_role": "redis_slave"}],
        }
        msg_list = task._check_nodes_metric(nodes, metric_val, "")
        assert set(msg_list.keys()) == {"redis_exporter_mixed_role"}
        assert len(msg_list["redis_exporter_mixed_role"]) == 2

    def test_master_and_slave_on_different_hosts_ok(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"},
            {"ip": "127.0.0.2", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_slave"},
        ]
        metric_val = {
            "127.0.0.1:6379": [{"value": 1, "instance_role": "redis_master"}],
            "127.0.0.2:6379": [{"value": 1, "instance_role": "redis_slave"}],
        }
        msg_list = task._check_nodes_metric(nodes, metric_val, "")
        assert set(msg_list.keys()) == {"ok"}


class TestMetricSeriesHelpers:
    def test_aggregate_metric_for_addr_list(self, check_exporter):
        m = {"a:1": [{"value": 1, "instance_role": "redis_master"}, {"value": 1, "instance_role": "redis_master"}]}
        agg = check_exporter._aggregate_metric_for_addr(m, "a:1")
        assert agg["value"] == 2

    def test_first_instance_role(self, check_exporter):
        m = {"a:1": [{"instance_role": "redis_slave", "value": 1}]}
        assert check_exporter._first_instance_role_for_addr(m, "a:1") == "redis_slave"

    def test_storage_role_kind(self, check_exporter):
        assert check_exporter._storage_role_kind("redis_master") == "master"
        assert check_exporter._storage_role_kind("redis_slave") == "slave"
        assert check_exporter._storage_role_kind("twemproxy") == ""

    def test_mixed_role_ips(self, check_exporter):
        metric_val = {
            "127.0.0.1:6379": [{"instance_role": "redis_master", "value": 1}],
            "127.0.0.1:6380": [{"instance_role": "redis_slave", "value": 1}],
            "127.0.0.2:6379": [{"instance_role": "redis_master", "value": 1}],
        }
        assert check_exporter._mixed_role_ips(metric_val) == {"127.0.0.1"}


class TestCheckClusterInner:
    report_day = 20250101

    def _base_cluster(self):
        c = MagicMock()
        c.id = 1
        c.bk_biz_id = 2
        c.bk_cloud_id = 0
        c.immute_domain = "r.test.db"
        c.cluster_type = "TwemproxyRedisInstance"
        c.tags.all.return_value = []
        return c

    def test_skip_no_storage(self, check_exporter):
        with patch.object(check_exporter, "fetch_proxy_metric_by_iplist"), patch.object(
            check_exporter, "fetch_proxy_metric_by_cluster"
        ), patch.object(check_exporter, "fetch_metric_by_iplist"), patch.object(
            check_exporter, "fetch_metric_by_cluster"
        ), patch.object(
            check_exporter, "get_all_proxy_nodes"
        ), patch.object(
            check_exporter, "get_proxy_type"
        ), patch.object(
            check_exporter, "get_all_storage_nodes", return_value=[]
        ):
            task = check_exporter.CheckRedisUpMetricTask()
            cluster = self._base_cluster()
            from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

            cr = RedisClusterReport(cluster, self.report_day, task.check_type)
            rows = task.check_cluster_inner(cr, cluster)
            assert len(rows) >= 1
            assert "no storage" in rows[0].msg.lower()

    def test_skip_all_nodes_not_running(self, check_exporter):
        with patch.object(check_exporter, "fetch_proxy_metric_by_iplist"), patch.object(
            check_exporter, "fetch_proxy_metric_by_cluster"
        ), patch.object(check_exporter, "fetch_metric_by_iplist"), patch.object(
            check_exporter, "fetch_metric_by_cluster"
        ), patch.object(
            check_exporter, "get_all_proxy_nodes"
        ), patch.object(
            check_exporter, "get_proxy_type", return_value=""
        ), patch.object(
            check_exporter,
            "get_all_storage_nodes",
            return_value=[
                {
                    "ip": "127.0.0.1",
                    "port": 6379,
                    "status": InstanceStatus.UNAVAILABLE.value,
                    "instance_role": "redis_master",
                },
            ],
        ):
            task = check_exporter.CheckRedisUpMetricTask()
            cluster = self._base_cluster()
            from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

            cr = RedisClusterReport(cluster, self.report_day, task.check_type)
            rows = task.check_cluster_inner(cr, cluster)
            assert any("no running" in r.msg.lower() for r in rows)

    def test_storage_ok_no_proxy_type(self, check_exporter):
        with patch.object(check_exporter, "fetch_proxy_metric_by_iplist"), patch.object(
            check_exporter, "fetch_proxy_metric_by_cluster"
        ), patch.object(check_exporter, "fetch_metric_by_iplist", return_value={}), patch.object(
            check_exporter,
            "fetch_metric_by_cluster",
            return_value={"127.0.0.1:6379": [{"value": 1, "instance_role": "redis_master"}]},
        ), patch.object(
            check_exporter, "get_all_proxy_nodes"
        ), patch.object(
            check_exporter, "get_proxy_type", return_value=""
        ), patch.object(
            check_exporter,
            "get_all_storage_nodes",
            return_value=[
                {
                    "ip": "127.0.0.1",
                    "port": 6379,
                    "status": InstanceStatus.RUNNING.value,
                    "instance_role": "redis_master",
                },
            ],
        ):
            task = check_exporter.CheckRedisUpMetricTask()
            cluster = self._base_cluster()
            cluster.cluster_type = ClusterType.TendisRedisInstance.value
            from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

            cr = RedisClusterReport(cluster, self.report_day, task.check_type)
            rows = task.check_cluster_inner(cr, cluster)
            assert rows[0].state == ReportStateType.NORMAL.value

    def test_warning_no_proxy_nodes(self, check_exporter):
        with patch.object(check_exporter, "fetch_proxy_metric_by_iplist", return_value={}), patch.object(
            check_exporter, "fetch_proxy_metric_by_cluster", return_value={}
        ), patch.object(check_exporter, "fetch_metric_by_iplist", return_value={}), patch.object(
            check_exporter,
            "fetch_metric_by_cluster",
            return_value={"127.0.0.1:6379": [{"value": 1, "instance_role": "redis_master"}]},
        ), patch.object(
            check_exporter, "get_all_proxy_nodes", return_value=[]
        ), patch.object(
            check_exporter, "get_proxy_type", return_value="twemproxy"
        ), patch.object(
            check_exporter,
            "get_all_storage_nodes",
            return_value=[
                {
                    "ip": "127.0.0.1",
                    "port": 6379,
                    "status": InstanceStatus.RUNNING.value,
                    "instance_role": "redis_master",
                },
            ],
        ):
            task = check_exporter.CheckRedisUpMetricTask()
            cluster = self._base_cluster()
            from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

            cr = RedisClusterReport(cluster, self.report_day, task.check_type)
            rows = task.check_cluster_inner(cr, cluster)
            # print rows for debug
            for row in rows:
                print(row.__dict__)
                print("-" * 100)
            # why no any "no proxy node" in rows?
            assert any("no proxy node" in row.msg.lower() for row in rows)


class TestCheckClusterRetry:
    report_day = 20250101

    def test_retries_then_error_record(self, check_exporter):
        with patch.object(check_exporter.time, "sleep") as mock_sleep:
            task = check_exporter.CheckRedisUpMetricTask()
            cluster = MagicMock()
            cluster.id = 1
            cluster.bk_biz_id = 2
            cluster.bk_cloud_id = 0
            cluster.immute_domain = "r.test.db"
            cluster.cluster_type = ClusterType.TendisRedisInstance.value

            with patch.object(task, "check_cluster_inner", side_effect=RuntimeError("boom")):
                rows = task.check_cluster(cluster, self.report_day)
            assert mock_sleep.call_count == 3
            assert len(rows) >= 1
            assert "retry" in rows[0].msg.lower() or "system error" in rows[0].msg.lower()


class TestStorageErrorTypes:
    report_day = 20250101

    def _base_cluster(self):
        c = MagicMock()
        c.id = 1
        c.bk_biz_id = 2
        c.bk_cloud_id = 0
        c.immute_domain = "r.test.db"
        c.cluster_type = ClusterType.TendisRedisInstance.value
        c.tags.all.return_value = []
        return c

    def test_storage_down(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = self._base_cluster()
        storage_nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"}
        ]
        from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

        cr = RedisClusterReport(cluster, self.report_day, task.check_type)
        with patch.object(
            check_exporter,
            "fetch_metric_by_cluster",
            return_value={"127.0.0.1:6379": [{"value": 0, "instance_role": "redis_master"}]},
        ), patch.object(check_exporter, "fetch_metric_by_iplist", return_value={}):
            task.check_storage(cluster, storage_nodes, cr)
            rows = cr.make_records()
            assert any("redis_master_exporter_down" in row.msg for row in rows)

    def test_storage_duplicate(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = self._base_cluster()
        storage_nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"}
        ]
        from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

        cr = RedisClusterReport(cluster, self.report_day, task.check_type)
        with patch.object(
            check_exporter,
            "fetch_metric_by_cluster",
            return_value={"127.0.0.1:6379": [{"value": 2, "instance_role": "redis_master"}]},
        ), patch.object(check_exporter, "fetch_metric_by_iplist", return_value={}):
            task.check_storage(cluster, storage_nodes, cr)
            rows = cr.make_records()
            assert any("redis_master_exporter_duplicate" in row.msg for row in rows)

    def test_storage_redundant(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = self._base_cluster()
        storage_nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"}
        ]
        from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

        cr = RedisClusterReport(cluster, self.report_day, task.check_type)
        with patch.object(
            check_exporter,
            "fetch_metric_by_cluster",
            return_value={
                "127.0.0.1:6379": [{"value": 1, "instance_role": "redis_master"}],
                "127.0.0.2:6380": [{"value": 1, "instance_role": "redis_master"}],
            },
        ), patch.object(check_exporter, "fetch_metric_by_iplist", return_value={}):
            task.check_storage(cluster, storage_nodes, cr)
            rows = cr.make_records()
            assert any("redis_master_exporter_redundant" in row.msg for row in rows)

    def test_storage_redundant2(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = self._base_cluster()
        cluster.cluster_type = "TwemproxyRedisInstance"
        storage_nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"}
        ]
        from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

        cr = RedisClusterReport(cluster, self.report_day, task.check_type)
        with patch.object(
            check_exporter,
            "fetch_metric_by_cluster",
            return_value={"127.0.0.1:6379": [{"value": 1, "instance_role": "redis_master"}]},
        ), patch.object(
            check_exporter,
            "fetch_metric_by_iplist",
            return_value={
                "127.0.0.1:6379": [
                    {"cluster_domain": "r.test.db", "instance_role": "redis_master"},
                    {"cluster_domain": "other.domain", "instance_role": "redis_master"},
                ]
            },
        ):
            task.check_storage(cluster, storage_nodes, cr)
            rows = cr.make_records()
            assert any("redis_master_exporter_redundant2" in row.msg for row in rows)

    def test_storage_mixed_role(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = self._base_cluster()
        storage_nodes = [
            {"ip": "127.0.0.1", "port": 6379, "status": InstanceStatus.RUNNING.value, "instance_role": "redis_master"},
        ]
        from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

        cr = RedisClusterReport(cluster, self.report_day, task.check_type)
        with patch.object(
            check_exporter,
            "fetch_metric_by_cluster",
            return_value={
                "127.0.0.1:6379": [{"value": 1, "instance_role": "redis_master"}],
                "127.0.0.1:6380": [{"value": 1, "instance_role": "redis_slave"}],
            },
        ), patch.object(check_exporter, "fetch_metric_by_iplist", return_value={}):
            task.check_storage(cluster, storage_nodes, cr)
            rows = cr.make_records()
            assert any("redis_exporter_mixed_role" in row.msg for row in rows)
            mixed = next(row for row in rows if "redis_exporter_mixed_role" in row.msg)
            assert "127.0.0.1:6379" in mixed.msg
            assert "127.0.0.1:6380" in mixed.msg


class TestProxyErrorTypes:
    report_day = 20250101

    def _base_cluster(self):
        c = MagicMock()
        c.id = 1
        c.bk_biz_id = 2
        c.bk_cloud_id = 0
        c.immute_domain = "r.test.db"
        c.cluster_type = "TwemproxyRedisInstance"
        c.tags.all.return_value = []
        return c

    def test_proxy_down(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = self._base_cluster()
        proxy_nodes = [
            {"ip": "127.0.0.2", "port": 5000, "status": InstanceStatus.RUNNING.value, "instance_role": "twemproxy"}
        ]
        from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

        cr = RedisClusterReport(cluster, self.report_day, task.check_type)
        with patch.object(
            check_exporter,
            "fetch_proxy_metric_by_cluster",
            return_value={"127.0.0.2:5000": [{"value": 0, "instance_role": "twemproxy"}]},
        ), patch.object(check_exporter, "fetch_proxy_metric_by_iplist", return_value={}):
            task.check_proxy(cluster, proxy_nodes, "twemproxy", cr)
            rows = cr.make_records()
            assert any("twemproxy_exporter_down" in row.msg for row in rows)

    def test_proxy_duplicate(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = self._base_cluster()
        proxy_nodes = [
            {"ip": "127.0.0.2", "port": 5000, "status": InstanceStatus.RUNNING.value, "instance_role": "twemproxy"}
        ]
        from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

        cr = RedisClusterReport(cluster, self.report_day, task.check_type)
        with patch.object(
            check_exporter,
            "fetch_proxy_metric_by_cluster",
            return_value={"127.0.0.2:5000": [{"value": 2, "instance_role": "twemproxy"}]},
        ), patch.object(check_exporter, "fetch_proxy_metric_by_iplist", return_value={}):
            task.check_proxy(cluster, proxy_nodes, "twemproxy", cr)
            rows = cr.make_records()
            assert any("twemproxy_exporter_duplicate" in row.msg for row in rows)

    def test_proxy_redundant(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = self._base_cluster()
        proxy_nodes = [
            {"ip": "127.0.0.2", "port": 5000, "status": InstanceStatus.RUNNING.value, "instance_role": "twemproxy"}
        ]
        from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

        cr = RedisClusterReport(cluster, self.report_day, task.check_type)
        with patch.object(
            check_exporter,
            "fetch_proxy_metric_by_cluster",
            return_value={
                "127.0.0.2:5000": [{"value": 1, "instance_role": "twemproxy"}],
                "127.0.0.3:5001": [{"value": 1, "instance_role": "twemproxy"}],
            },
        ), patch.object(check_exporter, "fetch_proxy_metric_by_iplist", return_value={}):
            task.check_proxy(cluster, proxy_nodes, "twemproxy", cr)
            rows = cr.make_records()
            assert any("twemproxy_exporter_redundant" in row.msg for row in rows)

    def test_proxy_redundant2(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        cluster = self._base_cluster()
        proxy_nodes = [
            {"ip": "127.0.0.2", "port": 5000, "status": InstanceStatus.RUNNING.value, "instance_role": "twemproxy"}
        ]
        from backend.db_periodic_task.local_tasks.redis_tasks.report_op import RedisClusterReport

        cr = RedisClusterReport(cluster, self.report_day, task.check_type)
        with patch.object(
            check_exporter,
            "fetch_proxy_metric_by_cluster",
            return_value={"127.0.0.2:5000": [{"value": 1, "instance_role": "twemproxy"}]},
        ), patch.object(
            check_exporter,
            "fetch_proxy_metric_by_iplist",
            return_value={"127.0.0.2:5001": [{"cluster_domain": "other.domain", "instance_role": "twemproxy"}]},
        ):
            task.check_proxy(cluster, proxy_nodes, "twemproxy", cr)
            rows = cr.make_records()
            assert any("twemproxy_exporter_redundant2" in row.msg for row in rows)
