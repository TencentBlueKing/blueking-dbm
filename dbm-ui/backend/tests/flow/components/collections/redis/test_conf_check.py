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
from unittest.mock import patch

from backend.db_report.enums import ReportStateType
from backend.flow.plugins.components.collections.redis.conf_check.base import CheckTarget
from backend.flow.plugins.components.collections.redis.conf_check.components import (
    CONFCHK_PATTERN,
    RedisConfCheckReportService,
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


class TestConfCheckDrsChunking:
    def test_drs_chunk_failure_does_not_drop_other_chunks(self):
        service = RedisConfCheckReportService()
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
            result_map = service._run_drs_groups(drs_groups, chunk_size=1)

        assert redis_rpc.call_count == 3
        assert result_map[(0, "INFO REPLICATION", "1.1.1.1:30000")] == "role:master"
        assert result_map[(0, "INFO REPLICATION", "1.1.1.3:30000")] == "role:master"
        assert (0, "INFO REPLICATION", "1.1.1.2:30000") not in result_map
