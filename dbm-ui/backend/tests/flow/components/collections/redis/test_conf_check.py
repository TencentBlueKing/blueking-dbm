# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Pure-logic unit tests for the unified REDIS_CONF_CHECK checkers. These exercise
``evaluate`` (no DB / no DRS), the on-host conf-read snippet builder and the
<CONFCHK> log parser. All findings share a single report subtype, so a checker
returns subtype-less rows carrying only state + msg per instance.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

from backend.db_report.enums import ReportStateType
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.flow.plugins.components.collections.redis.conf_check.base import CheckTarget
from backend.flow.plugins.components.collections.redis.conf_check.candidate_selection import (
    checker_query_filters,
    get_candidate_cluster_tuples,
)
from backend.flow.plugins.components.collections.redis.conf_check.components import (
    CONFCHK_PATTERN,
    PHASE_BATCH_DELAY,
    PHASE_EVALUATE,
    PHASE_POLL_JOBS,
    PHASE_RUN_DRS,
    RedisConfCheckBatchService,
    _collapse_conf_check_report_rows,
    _collect_host_conf_data,
    _run_drs_groups,
    _run_single_drs_chunk,
    _target_from_info,
    _target_to_info,
)
from backend.flow.plugins.components.collections.redis.conf_check.predixy_servers_checker import PredixyServersChecker
from backend.flow.plugins.components.collections.redis.conf_check.role_checker import RoleChecker
from backend.flow.utils.redis.redis_script_template import build_predixy_conf_check_snippet

ABNORMAL = ReportStateType.ABNORMAL.value
NORMAL = ReportStateType.NORMAL.value


def _storage_target(meta_role: str) -> CheckTarget:
    return CheckTarget(cluster_id=1, bk_cloud_id=0, ip="1.1.1.1", port=30000, extra={"meta_role": meta_role})


def _proxy_target(meta_servers=None) -> CheckTarget:
    return CheckTarget(
        cluster_id=1,
        bk_cloud_id=0,
        ip="1.1.1.9",
        port=50000,
        extra={"meta_servers": meta_servers or ["1.1.1.1:30000", "2.2.2.2:30000"]},
    )


def _predixy_info_servers(entries) -> str:
    """Render a predixy `INFO Servers` reply. entries: [(server, current_is_fail), ...]."""
    blocks = []
    for server, current_is_fail in entries:
        blocks.append(
            "Server:{}\nRole:master\nGroup:g1\nCurrentIsFail:{}\nConnections:1".format(server, current_is_fail)
        )
    # predixy separates server blocks with blank lines; trailing blank flushes the last one
    return "# Servers\n" + "\n\n".join(blocks) + "\n\n"


class TestRoleChecker:
    def test_role_checker_does_not_require_host_script(self):
        assert RoleChecker().requires_host_script is False

    def test_role_match(self):
        results = RoleChecker().evaluate(
            _storage_target("redis_master"), "role:master\r\nconnected_slaves:1\r\n", None
        )
        assert len(results) == 1
        assert results[0].state == NORMAL

    def test_role_mismatch(self):
        results = RoleChecker().evaluate(_storage_target("redis_master"), "role:slave\r\n", None)
        assert results[0].state == ABNORMAL
        assert "不匹配" in results[0].msg

    def test_role_drs_failure_is_abnormal(self):
        results = RoleChecker().evaluate(_storage_target("redis_slave"), None, None)
        assert results[0].state == ABNORMAL

    def test_role_drs_error_reason_in_msg(self):
        results = RoleChecker().evaluate(
            _storage_target("redis_slave"), None, None, drs_error="drs_rpc_error: timeout"
        )
        assert results[0].state == ABNORMAL
        assert "drs_rpc_error: timeout" in results[0].msg


class TestPredixyServersChecker:
    def setup_method(self):
        self.checker = PredixyServersChecker()

    def test_predixy_checker_requires_host_script(self):
        assert self.checker.requires_host_script is True

    def test_healthy_no_fail_no_drift(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0), ("2.2.2.2:30000", 0)])
        host_block = {"servers": ["1.1.1.1:30000", "2.2.2.2:30000"]}
        results = self.checker.evaluate(_proxy_target(), drs, host_block)
        assert len(results) == 1
        assert results[0].state == NORMAL

    def test_current_is_fail_flagged(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0), ("2.2.2.2:30000", 1)])
        # conf equals the non-failed running set -> isolate the CurrentIsFail issue
        host_block = {"servers": ["1.1.1.1:30000"]}
        results = self.checker.evaluate(_proxy_target(), drs, host_block)
        assert len(results) == 1
        assert results[0].state == ABNORMAL
        assert "failed_in_memory" in results[0].msg
        assert "2.2.2.2:30000" in results[0].msg
        assert "建议执行" not in results[0].msg

    def test_current_is_fail_in_conf_flagged(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0), ("2.2.2.2:30000", 1)])
        host_block = {"servers": ["1.1.1.1:30000", "2.2.2.2:30000"]}
        results = self.checker.evaluate(_proxy_target(), drs, host_block)
        assert len(results) == 1
        assert results[0].state == ABNORMAL
        assert "failed_in_conf" in results[0].msg
        assert "2.2.2.2:30000" in results[0].msg

    def test_conf_drift_detected(self):
        # running ok = {1.1.1.1:30000, 2.2.2.2:30000}; conf has a stale server and misses one
        drs = _predixy_info_servers([("1.1.1.1:30000", 0), ("2.2.2.2:30000", 0)])
        host_block = {"servers": ["1.1.1.1:30000", "3.3.3.3:30000"]}
        results = self.checker.evaluate(_proxy_target(), drs, host_block)
        assert len(results) == 1
        assert results[0].state == ABNORMAL
        assert "servers_mismatch" in results[0].msg
        assert "2.2.2.2:30000" in results[0].msg  # only_in_memory
        assert "3.3.3.3:30000" in results[0].msg  # only_in_conf

    def test_meta_only_backend_detected(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0)])
        host_block = {"servers": ["1.1.1.1:30000"]}
        target = _proxy_target(meta_servers=["1.1.1.1:30000", "2.2.2.2:30000"])
        results = self.checker.evaluate(target, drs, host_block)
        assert len(results) == 1
        assert results[0].state == ABNORMAL
        assert "only_in_meta" in results[0].msg
        assert "2.2.2.2:30000" in results[0].msg

    def test_conf_server_not_in_meta_detected_even_when_in_memory(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0), ("3.3.3.3:30000", 0)])
        host_block = {"servers": ["1.1.1.1:30000", "3.3.3.3:30000"]}
        target = _proxy_target(meta_servers=["1.1.1.1:30000"])
        results = self.checker.evaluate(target, drs, host_block)
        assert len(results) == 1
        assert results[0].state == ABNORMAL
        assert "not_in_meta" in results[0].msg
        assert "3.3.3.3:30000" in results[0].msg

    def test_conf_unreadable_is_abnormal(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0)])
        results = self.checker.evaluate(_proxy_target(), drs, {"error": "conf_not_found"})
        assert len(results) == 1
        assert results[0].state == ABNORMAL
        assert "predixy.conf" in results[0].msg

    def test_drs_failure_is_abnormal(self):
        results = self.checker.evaluate(_proxy_target(), None, {"servers": []})
        assert len(results) == 1
        assert results[0].state == ABNORMAL
        assert "查询失败" in results[0].msg

    def test_drs_error_reason_in_msg(self):
        results = self.checker.evaluate(
            _proxy_target(), None, {"servers": []}, drs_error="drs_rpc_error: connection refused"
        )
        assert results[0].state == ABNORMAL
        assert "drs_rpc_error: connection refused" in results[0].msg

    def test_empty_drs_snapshot_is_abnormal(self):
        results = self.checker.evaluate(_proxy_target(), "# Servers\n\n", {"servers": ["1.1.1.1:30000"]})
        assert results[0].state == ABNORMAL
        assert "empty_drs_snapshot" in results[0].msg

    def test_host_collection_error_vs_conf_not_found(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0)])
        job_fail = self.checker.evaluate(_proxy_target(), drs, {"error": "job_failed"})
        assert "主机配置采集失败" in job_fail[0].msg
        assert "job_failed" in job_fail[0].msg
        bad_json = self.checker.evaluate(_proxy_target(), drs, {"error": "bad_json"})
        assert "主机配置采集失败" in bad_json[0].msg
        conf_miss = self.checker.evaluate(_proxy_target(), drs, {"error": "conf_not_found"})
        assert "predixy.conf" in conf_miss[0].msg
        assert "conf_not_found" in conf_miss[0].msg

    def test_question_ip_in_memory_flagged_by_default(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0), ("?:30000", 0)])
        host_block = {"servers": ["1.1.1.1:30000"]}
        results = self.checker.evaluate(_proxy_target(), drs, host_block)
        assert results[0].state == ABNORMAL
        assert "?:30000" in results[0].msg

    def test_question_ip_in_memory_ignored_when_configured(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0), ("?:30000", 0)])
        host_block = {"servers": ["1.1.1.1:30000"]}
        results = self.checker.evaluate(
            _proxy_target(meta_servers=["1.1.1.1:30000"]),
            drs,
            host_block,
            checker_config={"ignore_question_ip_in_memory": True},
        )
        assert results[0].state == NORMAL

    def test_question_ip_failed_in_memory_ignored_when_configured(self):
        drs = _predixy_info_servers([("1.1.1.1:30000", 0), ("?:30000", 1)])
        host_block = {"servers": ["1.1.1.1:30000"]}
        results = self.checker.evaluate(
            _proxy_target(meta_servers=["1.1.1.1:30000"]),
            drs,
            host_block,
            checker_config={"ignore_question_ip_in_memory": True},
        )
        assert results[0].state == NORMAL
        assert "failed_in_memory=['" not in results[0].msg


class TestConfCheckScript:
    def test_snippet_embeds_ports(self):
        snippet = build_predixy_conf_check_snippet([50000, 50001])
        assert "__dbm_predixy_conf_servers" in snippet
        assert '__dbm_predixy_conf_servers "50000"' in snippet
        assert '__dbm_predixy_conf_servers "50001"' in snippet

    def test_snippet_skips_non_numeric_ports(self):
        snippet = build_predixy_conf_check_snippet(["50000", "bad"])
        assert '__dbm_predixy_conf_servers "50000"' in snippet
        assert "bad" not in snippet

    def test_confchk_pattern_parses_blocks(self):
        log = (
            "some preamble\n"
            '<CONFCHK checker="predixy_servers" port="50000">{"servers": ["1.1.1.1:30000"]}</CONFCHK>\n'
            "noise\n"
            '<CONFCHK checker="predixy_servers" port="50001">{"error": "conf_not_found"}</CONFCHK>\n'
        )
        matches = list(CONFCHK_PATTERN.finditer(log))
        assert len(matches) == 2
        assert matches[0].group("checker") == "predixy_servers"
        assert matches[0].group("port") == "50000"
        assert matches[1].group("body") == '{"error": "conf_not_found"}'


class TestConfCheckTargetSerialization:
    def test_target_info_round_trip(self):
        cluster = SimpleNamespace(
            id=1,
            immute_domain="cache.test.db",
            cluster_type="TendisPredixyRedisCluster",
            bk_biz_id=1001,
            bk_cloud_id=0,
        )
        checker = SimpleNamespace(name="role")
        target = CheckTarget(
            cluster_id=1,
            bk_cloud_id=0,
            ip="1.1.1.1",
            port=30000,
            extra={"meta_role": "redis_master"},
        )

        target_info = _target_to_info(cluster, checker, target)
        restored = _target_from_info(target_info)

        assert target_info["cluster"] == "cache.test.db"
        assert target_info["checker"] == "role"
        assert restored.address == "1.1.1.1:30000"
        assert restored.extra["meta_role"] == "redis_master"


class TestConfCheckReportCollapse:
    def _row(self, cluster_id: int, instance: str, state: str = NORMAL) -> dict:
        return {
            "cluster_id": cluster_id,
            "subtype": RedisCheckSubType.ConfigInconsistent.value,
            "cluster": "cache{}.test.db".format(cluster_id),
            "cluster_type": "TendisPredixyRedisCluster",
            "bk_biz_id": 1001,
            "bk_cloud_id": 0,
            "report_day": 20260630,
            "creator": "pytest",
            "state": state,
            "msg": "detail",
            "instance": instance,
        }

    def test_all_instances_pass_emits_single_cluster_row(self):
        rows = [
            self._row(1, "1.1.1.1:30000"),
            self._row(1, "1.1.1.2:30000"),
        ]
        collapsed = _collapse_conf_check_report_rows(rows)
        assert len(collapsed) == 1
        assert collapsed[0]["instance"] == "all"
        assert collapsed[0]["state"] == NORMAL
        assert "配置检查通过" in collapsed[0]["msg"]

    def test_any_instance_fail_emits_only_abnormal_rows(self):
        rows = [
            self._row(1, "1.1.1.1:30000", NORMAL),
            self._row(1, "1.1.1.2:30000", ABNORMAL),
        ]
        collapsed = _collapse_conf_check_report_rows(rows)
        assert len(collapsed) == 1
        assert collapsed[0]["instance"] == "1.1.1.2:30000"
        assert collapsed[0]["state"] == ABNORMAL

    def test_clusters_collapsed_independently(self):
        rows = [
            self._row(1, "1.1.1.1:30000", NORMAL),
            self._row(1, "1.1.1.2:30000", NORMAL),
            self._row(2, "2.2.2.2:30000", ABNORMAL),
        ]
        collapsed = _collapse_conf_check_report_rows(rows)
        assert len(collapsed) == 2
        by_cluster = {row["cluster_id"]: row for row in collapsed}
        assert by_cluster[1]["instance"] == "all"
        assert by_cluster[2]["instance"] == "2.2.2.2:30000"


class TestConfCheckDrsChunking:
    def test_drs_chunk_failure_does_not_drop_other_chunks(self):
        drs_groups = {(0, "pwd", "INFO REPLICATION"): {"1.1.1.1:30000", "1.1.1.2:30000", "1.1.1.3:30000"}}

        def fake_redis_rpc(payload):
            addresses = payload["addresses"]
            if addresses == ["1.1.1.2:30000"]:
                raise Exception("boom")
            return [{"address": address, "result": "role:master"} for address in addresses]

        with patch(
            "backend.flow.plugins.components.collections.redis.conf_check.components.DRSApi.redis_rpc",
            side_effect=fake_redis_rpc,
        ) as redis_rpc:
            errors = {}
            result_map = _run_drs_groups(drs_groups, chunk_size=1, errors_out=errors)

        assert redis_rpc.call_count == 3
        assert result_map[(0, "INFO REPLICATION", "1.1.1.1:30000")] == "role:master"
        assert result_map[(0, "INFO REPLICATION", "1.1.1.3:30000")] == "role:master"
        assert (0, "INFO REPLICATION", "1.1.1.2:30000") not in result_map
        assert "drs_rpc_error: boom" in errors[(0, "INFO REPLICATION", "1.1.1.2:30000")]

    def test_run_single_drs_chunk_empty_result_records_error(self):
        with patch(
            "backend.flow.plugins.components.collections.redis.conf_check.components.DRSApi.redis_rpc",
            return_value=[{"address": "1.1.1.1:30000", "result": "", "error_msg": "auth failed"}],
        ):
            errors = {}
            result = _run_single_drs_chunk(
                (0, 1, "redis_password", "INFO REPLICATION"),
                ["1.1.1.1:30000"],
                {1: {"redis_password": "pwd"}},
                {},
                errors,
            )
        assert result == {}
        assert errors[(0, "INFO REPLICATION", "1.1.1.1:30000")] == "empty_result: auth failed"


class TestConfCheckHostCollectionErrors:
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._get_job_ip_log",
        return_value=("", "log_fetch_failed: permission denied"),
    )
    def test_collect_host_conf_data_log_fetch_error(self, _log):
        jobs = [
            {
                "job_instance_id": 1,
                "exec_ip": "1.1.1.1",
                "conf_targets": [{"checker": "predixy_servers", "port": 50000, "cluster_id": 1}],
            }
        ]
        conf_data = _collect_host_conf_data(jobs)
        assert conf_data[("predixy_servers", "1.1.1.1", 50000)] == {"error": "log_fetch_failed: permission denied"}

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._get_job_ip_log",
        return_value=("noise without tags\n", None),
    )
    def test_collect_host_conf_data_no_confchk_output(self, _log):
        jobs = [
            {
                "job_instance_id": 2,
                "exec_ip": "1.1.1.1",
                "conf_targets": [{"checker": "predixy_servers", "port": 50000, "cluster_id": 1}],
            }
        ]
        conf_data = _collect_host_conf_data(jobs)
        assert conf_data[("predixy_servers", "1.1.1.1", 50000)] == {"error": "no_confchk_output"}


class TestConfCheckPasswordBatch:
    def test_batch_get_password_groups_items_by_cluster_id(self):
        from backend.flow.utils.base.payload_handler import PayloadHandler

        clusters = [
            SimpleNamespace(id=1, bk_cloud_id=0, bk_biz_id=1, immute_domain="c1", db_module_id=1, proxy_version=""),
            SimpleNamespace(id=2, bk_cloud_id=0, bk_biz_id=1, immute_domain="c2", db_module_id=1, proxy_version=""),
        ]
        encoded = "cGFzcw=="

        def fake_get_password(query_params):
            assert len(query_params["instances"]) == 2
            return {
                "items": [
                    {
                        "ip": "1",
                        "username": "default",
                        "component": "redis",
                        "password": encoded,
                    },
                    {
                        "ip": "2",
                        "username": "default",
                        "component": "redis_proxy",
                        "password": encoded,
                    },
                ]
            }

        with patch(
            "backend.flow.utils.base.payload_handler.DBPrivManagerApi.get_password",
            side_effect=fake_get_password,
        ):
            result = PayloadHandler.redis_batch_get_cluster_passwords(clusters, chunk_size=10)

        assert result[1]["redis_password"] == "pass"
        assert result[2]["redis_proxy_password"] == "pass"

    @patch(
        (
            "backend.flow.plugins.components.collections.redis.conf_check.components."
            "PayloadHandler.redis_batch_get_cluster_passwords"
        ),
        return_value={1: {"redis_password": "pwd"}},
    )
    @patch("backend.flow.plugins.components.collections.redis.conf_check.components.Cluster.objects.filter")
    def test_build_password_cache_uses_batch_api(self, cluster_filter, _batch):
        from backend.flow.plugins.components.collections.redis.conf_check.components import _build_password_cache
        from backend.flow.plugins.components.collections.redis.conf_check.password_cache import (
            put_cached_cluster_passwords,
        )

        put_cached_cluster_passwords({99: {"redis_password": "cached"}})
        cluster = SimpleNamespace(id=1, bk_cloud_id=0)
        cluster_filter.return_value = [cluster]
        cache, password_errors = _build_password_cache({1, 2, 99}, password_batch_size=50)
        assert cache[99]["redis_password"] == "cached"
        assert cache[1]["redis_password"] == "pwd"
        assert password_errors[2] == "cluster_not_in_meta"
        _batch.assert_called_once()
        assert _batch.call_args.kwargs["chunk_size"] == 50


class TestConfCheckBatchPhases:
    def _make_service(self):
        service = RedisConfCheckBatchService()
        service.log_info = MagicMock()
        service.log_warning = MagicMock()
        service.log_error = MagicMock()
        service.finish_schedule = MagicMock()
        return service

    def _make_data(self, **output_kwargs):
        outputs = SimpleNamespace(**output_kwargs)
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "node_name": "test_batch",
                "candidates_key": "dbm:redis_conf_check:candidates:test",
                "batch_num": 1,
                "batch_size": 10,
                "total_batches": 1,
                "interval": 1,
                "max_retries": 3,
                "drs_chunk_size": 1,
                "drs_chunks_per_tick": 1,
            },
            "global_data": {"created_by": "tester"},
        }.get(key)
        data.outputs = outputs
        return data

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._resolve_batch_clusters",
        return_value=[{"cluster_id": 1, "bk_cloud_id": 0}],
    )
    @patch.object(
        RedisConfCheckBatchService,
        "runtime_attrs",
        new_callable=PropertyMock,
        return_value={"root_pipeline_id": "testroot"},
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._build_target_infos",
        return_value=([{"checker": "role", "cluster_id": 1}], {"target_count": 1}),
    )
    @patch("backend.flow.plugins.components.collections.redis.conf_check.components._build_host_map", return_value={})
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._build_drs_chunk_queue",
        return_value=[((0, 1, "redis_password", "INFO REPLICATION"), ["1.1.1.1:30000"])] * 3,
    )
    def test_pure_drs_batch_skips_poll_jobs(self, _queue, _host_map, _targets, _runtime, _resolve):
        service = self._make_service()
        data = self._make_data()
        service._execute(data, {})
        assert data.outputs.phase == PHASE_RUN_DRS
        assert data.outputs.pending_jobs == {}

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._resolve_batch_clusters",
        return_value=[{"cluster_id": 1, "bk_cloud_id": 0}],
    )
    @patch.object(
        RedisConfCheckBatchService,
        "runtime_attrs",
        new_callable=PropertyMock,
        return_value={"root_pipeline_id": "testroot"},
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._build_target_infos",
        return_value=([{"checker": "predixy_servers", "cluster_id": 1}], {"target_count": 1}),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._build_host_map",
        return_value={(0, "1.1.1.1"): {"snippets": ["echo"], "conf_targets": []}},
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._build_drs_chunk_queue",
        return_value=[],
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._issue_host_jobs",
        return_value=([{"job_instance_id": 99, "bk_cloud_id": 0, "exec_ip": "1.1.1.1", "conf_targets": []}], 0),
    )
    def test_host_script_batch_starts_poll_jobs(self, _issue, _queue, _host_map, _targets, _runtime, _resolve):
        service = self._make_service()
        data = self._make_data()
        service._execute(data, {})
        assert data.outputs.phase == PHASE_POLL_JOBS
        assert 99 in data.outputs.pending_jobs

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._run_single_drs_chunk",
        return_value={(0, "INFO REPLICATION", "1.1.1.1:30000"): "role:master"},
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._get_password_cache_for_drs",
        return_value=({1: {"redis_password": "pwd"}}, {}),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._evaluate_and_report",
        return_value=(1, 0),
    )
    def test_drs_chunks_paced_across_ticks(self, _evaluate, _passwords, _run_chunk):
        service = self._make_service()
        queue = [((0, 1, "redis_password", "INFO REPLICATION"), ["1.1.1.1:30000"])] * 3
        data = self._make_data(
            phase=PHASE_RUN_DRS,
            target_infos=[],
            poll_count=0,
            drs_chunk_queue=queue,
            drs_cursor=0,
            drs_result_map={},
            drs_error_map={},
            host_conf_data={},
        )

        assert service._schedule(data, {}) is True
        assert data.outputs.drs_cursor == 1
        service.finish_schedule.assert_not_called()

        assert service._schedule(data, {}) is True
        assert data.outputs.drs_cursor == 2
        service.finish_schedule.assert_not_called()

        assert service._schedule(data, {}) is True
        assert data.outputs.drs_cursor == 3
        assert data.outputs.phase == PHASE_EVALUATE
        service.finish_schedule.assert_called_once()
        assert _run_chunk.call_count == 3

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components.delete_candidates_key",
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._evaluate_and_report",
        return_value=(1, 0),
    )
    def test_evaluate_enters_batch_delay_before_finish(self, _evaluate, _delete):
        from django.utils import timezone

        service = self._make_service()
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "node_name": "test_batch",
                "clusters": [],
                "candidates_key": "dbm:redis_conf_check:candidates:test",
                "batch_num": 1,
                "total_batches": 2,
                "delay_after_seconds": 10,
            },
            "global_data": {"created_by": "tester"},
        }.get(key)
        data.outputs = SimpleNamespace(
            phase=PHASE_EVALUATE,
            target_infos=[],
            host_conf_data={},
            drs_result_map={},
            drs_error_map={},
            drs_chunk_queue=[],
        )

        assert service._schedule(data, {}) is True
        assert data.outputs.phase == PHASE_BATCH_DELAY
        assert service.interval.interval == 10
        service.finish_schedule.assert_not_called()

        data.outputs.delay_target_time = timezone.now()
        assert service._schedule(data, {}) is True
        service.finish_schedule.assert_called_once()
        _delete.assert_not_called()


class TestRedisConfCheckCandidates:
    @patch("backend.flow.plugins.components.collections.redis.conf_check.redis_candidates.RedisConn")
    def test_push_and_slice_by_batch_num(self, redis_conn):
        from backend.flow.plugins.components.collections.redis.conf_check.redis_candidates import (
            push_candidate_cluster_ids,
            slice_candidate_cluster_ids,
        )

        redis_conn.lrange.return_value = [b"3", b"4"]

        push_candidate_cluster_ids("test:key", [2, 1, 2], ttl=3600)
        redis_conn.delete.assert_called_once_with("test:key")
        redis_conn.rpush.assert_called_once_with("test:key", 1, 2)
        redis_conn.expire.assert_called_with("test:key", 3600)

        ids = slice_candidate_cluster_ids("test:key", batch_num=2, batch_size=2)
        redis_conn.lrange.assert_called_with("test:key", 2, 3)
        assert ids == [3, 4]

    @patch("backend.flow.plugins.components.collections.redis.conf_check.redis_candidates.RedisConn")
    def test_count_candidates(self, redis_conn):
        from backend.flow.plugins.components.collections.redis.conf_check.redis_candidates import (
            count_candidate_cluster_ids,
        )

        redis_conn.llen.return_value = 5
        assert count_candidate_cluster_ids("test:key") == 5

    @patch("backend.flow.engine.bamboo.scene.redis.redis_conf_check.Builder")
    @patch(
        "backend.flow.engine.bamboo.scene.redis.redis_conf_check.count_candidate_cluster_ids",
        return_value=3,
    )
    def test_flow_act_kwargs_omit_clusters(self, _count, builder_cls):
        from backend.flow.engine.bamboo.scene.redis.redis_conf_check import RedisConfCheckFlow

        builder = MagicMock()
        builder_cls.return_value = builder
        RedisConfCheckFlow(
            "root",
            {"candidates_key": "dbm:redis_conf_check:candidates:root", "batch_size": 2},
        ).run_flow()

        assert builder.add_act.call_count == 2
        for call in builder.add_act.call_args_list:
            kwargs = call.kwargs["kwargs"]
            assert "clusters" not in kwargs
            assert kwargs["candidates_key"] == "dbm:redis_conf_check:candidates:root"
            assert "batch_num" in kwargs


class TestConfCheckCustomizedConfig:
    def test_checker_query_filters_bk_cloud_override(self):
        config = SimpleNamespace(bk_cloud_ids=[], customized={"role": {"bk_cloud_ids": [0]}}, cluster_types=None)
        from backend.flow.plugins.components.collections.redis.conf_check.role_checker import RoleChecker

        filters = checker_query_filters(config, RoleChecker())
        assert filters["bk_cloud_ids"] == [0]

    @patch("backend.flow.plugins.components.collections.redis.conf_check.candidate_selection.Cluster")
    def test_customized_excludes_checker_by_cloud(self, cluster_model):
        from backend.flow.plugins.components.collections.redis.conf_check.predixy_servers_checker import (
            PredixyServersChecker,
        )
        from backend.flow.plugins.components.collections.redis.conf_check.role_checker import RoleChecker

        role_qs = MagicMock()
        role_qs.exclude.return_value = role_qs
        role_qs.filter.return_value = role_qs
        role_qs.values_list.return_value = [(0, 1)]

        predixy_qs = MagicMock()
        predixy_qs.exclude.return_value = predixy_qs
        predixy_qs.filter.return_value = predixy_qs
        predixy_qs.values_list.return_value = [(1, 2)]

        def filter_side_effect(**kwargs):
            types = set(kwargs.get("cluster_type__in", []))
            if types == set(RoleChecker().cluster_types):
                return role_qs
            if types == set(PredixyServersChecker().cluster_types):
                return predixy_qs
            return MagicMock(values_list=MagicMock(return_value=[]))

        cluster_model.objects.filter.side_effect = filter_side_effect

        config = SimpleNamespace(
            cluster_types=None,
            bizs_ignored=[],
            clusters_ignored=[],
            bk_cloud_ids=[],
            customized={"role": {"bk_cloud_ids": [0]}, "predixy_servers": {"bk_cloud_ids": [1]}},
        )
        result = get_candidate_cluster_tuples(config)
        assert (0, 1) in result
        assert (1, 2) in result
        assert len(result) == 2
