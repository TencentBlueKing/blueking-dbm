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
import base64
import gzip
import json
import os
import shutil
import subprocess
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from backend.db_meta.enums import ClusterType
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
    _evaluate_and_report,
    _load_batch_clusters,
    _run_drs_chunk_slice,
    _run_single_drs_chunk,
    _target_from_info,
    _target_to_info,
)
from backend.flow.plugins.components.collections.redis.conf_check.predixy_servers_checker import PredixyServersChecker
from backend.flow.plugins.components.collections.redis.conf_check.storage_conf_checker import (
    CLUSTER_CTX_KEY,
    StorageClusterContext,
    StorageConfChecker,
    load_cluster_contexts,
)
from backend.flow.plugins.components.collections.redis.conf_check.storage_conf_parse import (
    compare_directives,
    join_directive_values,
    parse_config_pairs,
    parse_disk_conf,
    parse_info,
    parse_mem_bytes,
    parse_storage_host_block,
    parse_store_masters,
    resolve_expected_conf,
    same_conf_value,
    same_conf_value_for,
    split_dbconfig_entries,
)
from backend.flow.utils.redis.redis_script_template import (
    CONF_CHECK_SCRIPT_HEADER,
    build_predixy_conf_check_snippet,
    build_storage_conf_check_snippet,
)

ABNORMAL = ReportStateType.ABNORMAL.value
NORMAL = ReportStateType.NORMAL.value

FAKE_PASSWORD = "FakePass_For_Test_Only"
_STORAGE_CONF_MOD = "backend.flow.plugins.components.collections.redis.conf_check.storage_conf_checker"
COMPONENTS = "backend.flow.plugins.components.collections.redis.conf_check.components"

# Prefer the system bash (3.2 on macOS) so the snippet's bash 3.2 compatibility is exercised.
SYSTEM_BASH = "/bin/bash" if os.path.exists("/bin/bash") else shutil.which("bash")
HOST_TOOLS_AVAILABLE = bool(SYSTEM_BASH and shutil.which("bash") and shutil.which("gzip") and shutil.which("base64"))

# Mimics /home/mysql/dbtools/redis-cmd.sh: echoes the redis-cli command line with the
# password, then answers the command read from stdin from per-port fixture files.
_STUB_REDIS_CMD = r"""#!/bin/bash
port="$1"
echo "$#" >> "$STUB_DIR/argc.log"
echo "/usr/local/redis/bin/redis-cli -a FakePass_For_Test_Only -h 1.1.1.1 -p $port -c "
IFS= read -r cmd
printf '%s|%s\n' "$port" "$cmd" >> "$STUB_DIR/calls.log"
d="$STUB_DIR/$port"
if [ -f "$d/warning" ]; then
    echo "Warning: Using a password with '-a' or '-u' option on the command line interface may not be safe." >&2
fi
case "$cmd" in
    "info replication") f=info ;;
    "confxx get *") f=confxx ;;
    "config get *") f=config ;;
    *) echo "ERR unexpected command"; exit 0 ;;
esac
[ -f "$d/$f.out" ] && cat "$d/$f.out"
if [ -f "$d/$f.rc" ]; then exit "$(cat "$d/$f.rc")"; fi
exit 0
"""

# Host samples with IPs and passwords replaced by test placeholders.
REDIS_MASTER_INFO = (
    "# Replication\r\nrole:master\r\nconnected_slaves:1\r\n"
    "slave0:ip=2.2.2.2,port=30000,state=online,offset=1089500468,lag=0\r\n"
    "master_failover_state:no-failover\r\n"
)
REDIS_CONFIG = "rdbchecksum\nyes\ndaemonize\nyes\nio-threads-do-reads\nyes\ntimeout\n300\n"
TENDISSSD_SLAVE_CONFIG = (
    "dbfilename\ndump.rdb\nrequirepass\n{pwd}\nmasterauth\n{pwd}\nunixsocket\n\ntimeout\n300\n".format(
        pwd=FAKE_PASSWORD
    )
)
TENDISSSD_MASTER_CONFIG = "dbfilename\ndump.rdb\nrequirepass\n{pwd}\nmasterauth\n\nunixsocket\n\n".format(
    pwd=FAKE_PASSWORD
)


REDIS_SLAVE_INFO = (
    "# Replication\r\nrole:slave\r\nmaster_host:1.1.1.1\r\nmaster_port:30000\r\nmaster_link_status:up\r\n"
    "master_last_io_seconds_ago:1\r\nmaster_sync_in_progress:0\r\nslave_repl_offset:2932579419\r\n"
)
TENDISPLUS_MASTER_INFO = (
    "# Replication\r\nrole:master\r\nconnected_slaves:1\r\n"
    "slave0:ip=2.2.2.2,port=30000,state=online,offset=1085641,lag=0,binlog_lag=0\r\n"
    "master_repl_offset:1085641\r\n"
    "rocksdb0_slave0:ip=2.2.2.2,port=30000,dest_store_id=0,state=online,binlog_pos=108564,lag=0,binlog_lag=0\r\n"
    "rocksdb1_slave0:ip=2.2.2.2,port=30000,dest_store_id=1,state=online,binlog_pos=108564,lag=0,binlog_lag=0\r\n"
)
TENDISPLUS_SLAVE_INFO = (
    "# Replication\r\nrole:slave\r\nmaster_host:1.1.1.1\r\nmaster_port:30000\r\nmaster_link_status:up\r\n"
    "master_last_io_seconds_ago:0\r\nmaster_last_binlog_seconds_ago:0\r\nmaster_sync_in_progress:0\r\n"
    "master_repl_offset:1085791\r\n"
    + "".join(
        "rocksdb{i}_master:ip=1.1.1.1,port=30000,src_store_id={i},state=online,fullsync_succ_times=1,"
        "binlog_pos=108579,lag=0\r\n".format(i=i)
        for i in range(10)
    )
)
TENDISPLUS_CONFIG = "allow-cross-slot\nno\naof-enabled\nno\naof-psync-num\n500\n"
TENDISSSD_MASTER_INFO = (
    "# Replication\r\nrole:master\r\nconnected_slaves:1\r\n"
    "slave0:ip=2.2.2.2,port=30000,state=online,offset=0,seq=19916728\r\n"
    "master_repl_offset:0\r\nrepl_backlog_active:0\r\nrepl_backlog_size:1048576\r\n"
)
TENDISSSD_SLAVE_INFO = REDIS_SLAVE_INFO


def _decode_section(value: str) -> str:
    return gzip.decompress(base64.b64decode(value)).decode()


def _encode_section(text: str) -> str:
    return base64.b64encode(gzip.compress(text.encode())).decode()


def _storage_block(disk="port 30000\n", repl=REDIS_MASTER_INFO, mem=REDIS_CONFIG, **overrides) -> dict:
    block = {
        "conf_path": "/data/redis/30000/redis.conf",
        "conf_paths": ["/data/redis/30000/redis.conf"],
        "disk": _encode_section(disk) if disk is not None else "",
        "repl": _encode_section(repl) if repl is not None else "",
        "mem": _encode_section(mem) if mem is not None else "",
        "mem_cmd": "confxx",
        "disk_err": "",
        "repl_err": "",
        "mem_err": "",
    }
    block.update(overrides)
    return block


class _StorageHostSim:
    """Temp config tree + stub redis-cmd.sh for running the storage_conf snippet under bash."""

    def __init__(self, root):
        self.root = root
        self.stub_dir = root / "stub"
        self.stub_dir.mkdir()
        self.redis_cmd = root / "redis-cmd.sh"
        self.redis_cmd.write_text(_STUB_REDIS_CMD)
        self.data_dirs = [root / "data1", root / "data"]

    def write_conf(self, data_dir: str, port: int, name: str, content: str):
        conf = self.root / data_dir / "redis" / str(port) / name
        conf.parent.mkdir(parents=True, exist_ok=True)
        conf.write_text(content)
        return conf

    def answer(self, port: int, kind: str, out: str = "", rc: int = None, warning: bool = False):
        port_dir = self.stub_dir / str(port)
        port_dir.mkdir(exist_ok=True)
        (port_dir / "{}.out".format(kind)).write_bytes(out.encode())
        if rc is not None:
            (port_dir / "{}.rc".format(kind)).write_text(str(rc))
        if warning:
            (port_dir / "warning").write_text("1")

    def calls(self):
        log = self.stub_dir / "calls.log"
        return log.read_text().splitlines() if log.exists() else []

    def run(self, ports, cwd=None):
        script = CONF_CHECK_SCRIPT_HEADER + build_storage_conf_check_snippet(
            ports, redis_cmd=str(self.redis_cmd), data_dirs=[str(d) for d in self.data_dirs]
        )
        script_path = self.root / "job.sh"
        script_path.write_text(script)
        env = {k: v for k, v in os.environ.items() if k != "REDIS_DATA_DIR"}
        env["STUB_DIR"] = str(self.stub_dir)
        proc = subprocess.run(
            [SYSTEM_BASH, str(script_path)],
            cwd=str(cwd or self.root),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        stdout = proc.stdout + proc.stderr
        blocks = {}
        for match in CONFCHK_PATTERN.finditer(stdout):
            assert match.group("checker") == "storage_conf"
            blocks[int(match.group("port"))] = json.loads(match.group("body"))
        return stdout, blocks


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


class TestStorageConfSnippetBuilder:
    def test_snippet_embeds_numeric_ports_only(self):
        snippet = build_storage_conf_check_snippet([30000, "30001", "bad"])
        assert '__dbm_scc_port "30000"' in snippet and '__dbm_scc_port "30001"' in snippet
        assert "bad" not in snippet and "python" not in snippet
        assert '"${REDIS_DATA_DIR:-}" /data1 /data;' in snippet
        assert build_storage_conf_check_snippet([]) == ""


@pytest.mark.skipif(not HOST_TOOLS_AVAILABLE, reason="bash/gzip/base64 required")
class TestStorageConfHostSnippet:
    def test_payload_decodes_with_include_order_and_no_credentials(self, tmp_path):
        sim = _StorageHostSim(tmp_path)
        sim.write_conf(
            "data", 30000, "redis.conf", "bind 1.1.1.1\ninclude instance.conf\ntimeout 300\n# requirepass old\n"
        )
        sim.write_conf(
            "data",
            30000,
            "instance.conf",
            'timeout 0\nrequirepass "{pwd}"\n  MasterAuth {pwd}\nuser default on >{pwd} ~* +@all\n'
            "rename-command flushall cleanall\n".format(pwd=FAKE_PASSWORD),
        )
        sim.answer(30000, "info", REDIS_MASTER_INFO, warning=True)
        sim.answer(30000, "confxx", TENDISSSD_MASTER_CONFIG)

        stdout, blocks = sim.run([30000])

        assert FAKE_PASSWORD not in stdout
        assert " -a " not in stdout
        assert "Warning: Using a password" not in stdout
        block = blocks[30000]
        assert block["conf_path"] == str(tmp_path / "data" / "redis" / "30000" / "redis.conf")
        assert block["disk_err"] == block["repl_err"] == block["mem_err"] == ""
        assert block["mem_cmd"] == "confxx"
        assert _decode_section(block["disk"]) == "bind 1.1.1.1\ntimeout 0\ntimeout 300\n"
        assert _decode_section(block["repl"]) == REDIS_MASTER_INFO
        assert _decode_section(block["mem"]) == "dbfilename\ndump.rdb\nunixsocket\n\n"

    def test_runtime_credentials_removed_with_pairs_aligned(self, tmp_path):
        sim = _StorageHostSim(tmp_path)
        sim.write_conf("data1", 30000, "redis.conf", "port 30000\n")
        sim.answer(30000, "info", REDIS_MASTER_INFO)
        sim.answer(30000, "confxx", TENDISSSD_SLAVE_CONFIG)

        stdout, blocks = sim.run([30000])

        assert FAKE_PASSWORD not in stdout
        mem = _decode_section(blocks[30000]["mem"])
        assert mem.split("\n")[:-1] == ["dbfilename", "dump.rdb", "unixsocket", "", "timeout", "300"]

    def test_wildcard_reaches_wrapper_unexpanded(self, tmp_path):
        sim = _StorageHostSim(tmp_path)
        workdir = tmp_path / "cwd"
        workdir.mkdir()
        (workdir / "Changelog").write_text("x")
        sim.write_conf("data", 30000, "redis.conf", "port 30000\n")
        sim.answer(30000, "info", REDIS_MASTER_INFO)
        sim.answer(30000, "confxx", REDIS_CONFIG)

        _stdout, blocks = sim.run([30000], cwd=workdir)

        assert "30000|confxx get *" in sim.calls()
        assert set((sim.stub_dir / "argc.log").read_text().split()) == {"1"}
        assert _decode_section(blocks[30000]["mem"]) == REDIS_CONFIG

    def test_falls_back_to_config_get_only_on_unknown_command(self, tmp_path):
        sim = _StorageHostSim(tmp_path)
        for port in (30000, 30001):
            sim.write_conf("data", port, "redis.conf", "port {}\n".format(port))
            sim.answer(port, "info", REDIS_MASTER_INFO)
            sim.answer(port, "config", REDIS_CONFIG)
        sim.answer(30000, "confxx", "ERR unknown command 'confxx', with args beginning with: 'get' '*' \n")
        sim.answer(
            30001, "confxx", "ERR Unknown subcommand or wrong number of arguments for 'get'. Try CONFXX HELP.\n"
        )

        stdout, blocks = sim.run([30000, 30001])

        assert (blocks[30000]["mem_cmd"], blocks[30000]["mem_err"]) == ("config", "")
        assert _decode_section(blocks[30000]["mem"]) == REDIS_CONFIG
        assert (blocks[30001]["mem_err"], blocks[30001]["mem"]) == ("redis_cmd_failed", "")
        assert "30001|config get *" not in sim.calls()
        assert "Unknown subcommand" not in stdout

    def test_data_dir_probing(self, tmp_path):
        sim = _StorageHostSim(tmp_path)
        sim.write_conf("data1", 30000, "redis.conf", "port 30000\n")
        sim.write_conf("data", 30000, "redis.conf", "port 30000\n")
        for port in (30000, 30001):
            sim.answer(port, "info", REDIS_MASTER_INFO)
            sim.answer(port, "confxx", REDIS_CONFIG)

        _stdout, blocks = sim.run([30000, 30001])

        assert blocks[30000]["conf_path"] == str(tmp_path / "data1" / "redis" / "30000" / "redis.conf")
        assert len(blocks[30000]["conf_paths"]) == 2
        assert (blocks[30001]["disk_err"], blocks[30001]["disk"], blocks[30001]["conf_paths"]) == (
            "conf_not_found",
            "",
            [],
        )

    def test_symlinked_data_dirs_are_not_ambiguous(self, tmp_path):
        sim = _StorageHostSim(tmp_path)
        sim.write_conf("data", 30000, "redis.conf", "port 30000\n")
        (tmp_path / "data1").symlink_to(tmp_path / "data")
        sim.answer(30000, "info", REDIS_MASTER_INFO)
        sim.answer(30000, "confxx", REDIS_CONFIG)

        _stdout, blocks = sim.run([30000])

        assert len(blocks[30000]["conf_paths"]) == 1

    def test_failures_yield_only_reason_tokens(self, tmp_path):
        sim = _StorageHostSim(tmp_path)
        answers = {
            30000: ("", 124, "redis_cmd_timeout"),
            30001: ("", None, "redis_cmd_empty"),
            30002: ("NOAUTH Authentication required.\n", None, "redis_cmd_failed"),
            30003: ("partial output\n", 1, "redis_cmd_failed"),
        }
        for port, (out, rc, _err) in answers.items():
            sim.write_conf("data", port, "redis.conf", "port {}\n".format(port))
            sim.answer(port, "confxx", REDIS_CONFIG)
            sim.answer(port, "info", out, rc=rc)

        stdout, blocks = sim.run(list(answers))

        for port, (_out, _rc, err) in answers.items():
            assert (blocks[port]["repl_err"], blocks[port]["repl"], blocks[port]["mem_err"]) == (err, "", "")
        assert "Authentication required" not in stdout
        assert "partial output" not in stdout


class TestStorageConfParse:
    def test_disk_directives(self):
        conf = parse_disk_conf(
            "# comment\nbind 1.1.1.1\nsave 900 1\nsave 300 10\ntimeout 0\nTimeout 300\n"
            "loadmodule /data/twemproxy-0.2.4-v29/modules/libredisbloom.so\n"
            'loadmodule "/usr/local/redis/modules/libredisjson.so" arg1\n'
            "#CONFCHK_ERR include_cycle /data/redis/30000/a.conf\n"
        )
        assert conf.directives["save"] == ["900 1", "300 10"]
        assert conf.last_value("timeout") == "300"
        assert conf.last_value("missing") is None
        assert conf.modules == ["libredisbloom.so", "libredisjson.so"]
        assert conf.include_errors == ["include_cycle /data/redis/30000/a.conf"]
        assert "#confchk_err" not in conf.directives

    @pytest.mark.parametrize(
        "disk_text,replication_of",
        [
            ("slaveof 1.1.1.1 30000\nreplicaof 2.2.2.2 30000\n", "2.2.2.2 30000"),
            ("slaveof 1.1.1.1 30000\nslaveof no one\n", ""),
            ("port 30000\n", ""),
        ],
    )
    def test_disk_effective_replication_follows_line_order(self, disk_text, replication_of):
        assert parse_disk_conf(disk_text).replication_of == replication_of

    @pytest.mark.parametrize(
        "info_text,role",
        [
            (REDIS_MASTER_INFO, "master"),
            (REDIS_SLAVE_INFO, "slave"),
            (TENDISPLUS_MASTER_INFO, "master"),
            (TENDISPLUS_SLAVE_INFO, "slave"),
            (TENDISSSD_MASTER_INFO, "master"),
            (TENDISSSD_SLAVE_INFO, "slave"),
        ],
    )
    def test_info_replication_samples(self, info_text, role):
        info = parse_info(info_text)
        assert info["role"] == role
        if role == "slave":
            assert (info["master_host"], info["master_port"], info["master_link_status"]) == ("1.1.1.1", "30000", "up")
        assert all(not value.endswith("\r") for value in info.values())

    def test_tendisplus_store_masters(self):
        stores = parse_store_masters(parse_info(TENDISPLUS_SLAVE_INFO))
        assert [s.store_id for s in stores] == list(range(10))
        assert {(s.address, s.state) for s in stores} == {("1.1.1.1:30000", "online")}
        assert parse_store_masters(parse_info(TENDISPLUS_MASTER_INFO)) == []
        assert parse_store_masters(parse_info(REDIS_SLAVE_INFO)) == []

    @pytest.mark.parametrize(
        "config_text,expected",
        [
            (REDIS_CONFIG, {"rdbchecksum": "yes", "daemonize": "yes", "io-threads-do-reads": "yes", "timeout": "300"}),
            (TENDISPLUS_CONFIG, {"allow-cross-slot": "no", "aof-enabled": "no", "aof-psync-num": "500"}),
            ("dbfilename\ndump.rdb\nunixsocket\n\n", {"dbfilename": "dump.rdb", "unixsocket": ""}),
            ("dbfilename\ndump.rdb\nunixsocket\n", None),
        ],
    )
    def test_config_pairs_samples(self, config_text, expected):
        assert parse_config_pairs(config_text) == expected

    def test_host_block_round_trip(self):
        data = parse_storage_host_block(
            _storage_block(
                disk="port 30000\nslaveof 1.1.1.1 30000\n", repl=TENDISPLUS_SLAVE_INFO, mem=TENDISPLUS_CONFIG
            )
        )
        assert data.section_errors == {}
        assert data.disk.replication_of == "1.1.1.1 30000"
        assert data.repl["role"] == "slave"
        assert len(data.store_masters) == 10
        assert (data.mem["aof-psync-num"], data.mem_cmd) == ("500", "confxx")

    @pytest.mark.parametrize(
        "overrides,section,error",
        [
            ({"disk": None, "disk_err": "conf_not_found"}, "disk", "conf_not_found"),
            ({"disk": None}, "disk", "missing_section"),
            ({"repl": "garbage without role\n"}, "repl", "repl_unparsable"),
            ({"mem": "a\nb\nc\n"}, "mem", "mem_unpaired"),
            ({"raw_mem": "not-base64!!"}, "mem", "decode_failed"),
        ],
    )
    def test_host_block_section_errors(self, overrides, section, error):
        raw_mem = overrides.pop("raw_mem", None)
        block = _storage_block(**overrides)
        if raw_mem is not None:
            block["mem"] = raw_mem
        data = parse_storage_host_block(block)
        assert data.section_errors == {section: error}
        assert getattr(data, section) is None

    def test_host_block_collection_error(self):
        assert parse_storage_host_block({"error": "job_timeout"}).collection_error == "job_timeout"
        assert parse_storage_host_block(None).collection_error == "no_host_data"


def _expected(dbconfig, cluster_enabled=False, check_databases=False):
    return resolve_expected_conf(
        dbconfig, ip="1.1.1.1", port=30000, cluster_enabled=cluster_enabled, check_databases=check_databases
    )


def _assert_msg(msg, expectations):
    """Each expectation must be a substring of msg; a leading "!" means it must not be."""
    for text in expectations:
        assert (text[1:] not in msg) if text.startswith("!") else (text in msg), (text, msg)


def _table(cases):
    """Rows are (id, *values); returns parametrize kwargs."""
    return {"argvalues": [c[1:] for c in cases], "ids": [c[0] for c in cases]}


_PATHS_DB = {"dir": "{{redis_data_dir}}/data", "logfile": "{{redis_data_dir}}/redis.log"}
_QUOTED_DISK = 'dir "/data/redis/30000/data"\nlogfile "/data/redis/30000/redis.log"\n'
_QUOTED_MEM = {"dir": "/data/redis/30000/data", "logfile": "/data/redis/30000/redis.log"}
_DATA1_DISK = 'dir "/data1/redis/30000/data"\nlogfile /data1/redis/30000/redis.log\n'
_DATA1_MEM = {"dir": "/data1/redis/30000/data", "logfile": "/data1/redis//30000/redis.log"}
_SPEC_DB = {"repl-backlog-size": "512mb", "slave-priority": "100"}
_SPEC_DISK = "repl-backlog-size 536870912\nreplica-priority 100\n"
_SPEC_MEM = {"repl-backlog-size": "536870912", "replica-priority": "100"}
_COBL_DB = {
    "client-output-buffer-limit": "normal 256mb 512mb 300\nclient-output-buffer-limit slave 2048mb 2048mb 300"
    "\nclient-output-buffer-limit pubsub 32mb 8mb 60",
    "save": "",
}
_COBL_DISK = (
    "client-output-buffer-limit normal 256mb 512mb 300\n"
    "client-output-buffer-limit slave 2048mb 2048mb 300\n"
    "client-output-buffer-limit pubsub 32mb 8mb 60\n"
    'save ""\n'
)
_COBL_MEM = {
    "client-output-buffer-limit": "normal 268435456 536870912 300 slave 2147483648 2147483648 300 "
    "pubsub 33554432 8388608 60",
    "save": "",
}
_COBL_MEM_SAVE = dict(_COBL_MEM, save="3600 1 300 100")
_COBL_DB_REPLICA = {
    "client-output-buffer-limit": "normal 256mb 512mb 300\nclient-output-buffer-limit replica 2048mb 2048mb 300"
    "\nclient-output-buffer-limit pubsub 32mb 8mb 60",
    "save": "",
}
_COBL_REPLICA_DISK = (
    "client-output-buffer-limit normal 256mb 512mb 300\n"
    "client-output-buffer-limit replica 2gb 2gb 300\n"
    "client-output-buffer-limit pubsub 32mb 8mb 60\n"
    'save ""\n'
)
_T300 = {"timeout": "300"}
_RO = {"slave-read-only": "yes"}
_RO_DRIFT = "slave-read-only(dbconfig=yes, memory=no, disk=no)"
_SAVE_DRIFT = 'save(dbconfig="", memory=3600 1 300 100, disk="")'
_ABSENT_DRIFT = "timeout(dbconfig=300, memory=300, disk=<absent>)"

# id, dbconfig, disk text, memory (None = not collected), expected drift renders
_COMPARE_CASES = [
    ("quoted_paths", _PATHS_DB, _QUOTED_DISK, _QUOTED_MEM, []),
    ("data1_equals_data", _PATHS_DB, _DATA1_DISK, _DATA1_MEM, []),
    ("bytes", {"hash-max-ziplist-entries": "512mb"}, "hash-max-ziplist-entries 536870912\n", {}, []),
    ("alias_and_bool", _RO, "replica-read-only yes\n", {"replica-read-only": "1"}, []),
    ("alias", {"slave-lazy-flush": "yes"}, "slave-lazy-flush yes\n", {"replica-lazy-flush": "yes"}, []),
    ("spec_bytes_and_priority_alias", _SPEC_DB, _SPEC_DISK, _SPEC_MEM, []),
    ("alias_value_drift", _RO, "replica-read-only no\n", {"replica-read-only": "no"}, [_RO_DRIFT]),
    ("timeout_drift", _T300, "timeout 300\n", {"timeout": "0"}, ["timeout(dbconfig=300, memory=0, disk=300)"]),
    ("disk_last_value_wins", _T300, "timeout 300\ntimeout 0\n", None, ["timeout(dbconfig=300, disk=0)"]),
    ("missing_on_disk", _T300, "port 30000\n", _T300, [_ABSENT_DRIFT]),
    ("startup_only_disk_match", _T300, "timeout 300\n", {}, []),
    ("startup_only_disk_drift", _T300, "timeout 1\n", {}, ["timeout(dbconfig=300, disk=1)"]),
    (
        "extra_ignored",
        {"timeout": "0"},
        "timeout 0\nio-threads 4\n",
        {"timeout": "0", "lua-replicate-commands": "1"},
        [],
    ),
    ("empty_expected_absent", {"unixsocket": ""}, "port 30000\n", {"unixsocket": ""}, []),
    ("unknown_to_both", {"repl-diskless-sync": "no"}, "port 30000\n", {}, []),
    ("multi_entry_match", _COBL_DB, _COBL_DISK, _COBL_MEM, []),
    ("multi_entry_replica_class", _COBL_DB, _COBL_REPLICA_DISK, _COBL_MEM, []),
    ("multi_entry_replica_class_memory", _COBL_DB_REPLICA, _COBL_REPLICA_DISK, _COBL_MEM, []),
    ("rewrite_renamed_lua", {"lua-time-limit": "5000"}, "busy-reply-threshold 5000\n", {"lua-time-limit": "5000"}, []),
    (
        "rewrite_renamed_cpulist",
        {"aof_rewrite_cpulist": "0-3"},
        "aof-rewrite-cpulist 0-3\n",
        {},
        [],
    ),
    ("multi_entry_save_drift", _COBL_DB, _COBL_DISK, _COBL_MEM_SAVE, [_SAVE_DRIFT]),
]


class TestStorageConfCompare:
    # ported from dbactuator pkg/redisconf runtime_test.go TestSameConfRuntimeValue
    @pytest.mark.parametrize(
        "a,b,eq",
        [
            ('"/data/redis/30000/data"', "/data/redis/30000/data", True),
            ("yes", "1", True),
            ("no", "0", True),
            ("256mb", "268435456", True),
            ("3600 1 300 100", "3600 1 300 100", True),
            ("normal 256mb 512mb 300", "normal 268435456 536870912 300", True),
            ("10", "20", False),
            ("", '""', True),
        ],
    )
    def test_same_conf_value(self, a, b, eq):
        assert same_conf_value(a, b) is eq

    def test_cobl_rewrite_canonicalization(self):
        # CONFIG REWRITE writes "replica" and human units; CONFIG GET/dbconfig keep "slave"/bytes.
        assert same_conf_value_for(
            "client-output-buffer-limit",
            "normal 256mb 512mb 300 slave 2048mb 2048mb 300 pubsub 32mb 8mb 60",
            "normal 256mb 512mb 300 replica 2gb 2gb 300 pubsub 32mb 8mb 60",
        )
        # Valkey dbconfig uses "replica" while runtime CONFIG GET reports "slave".
        assert same_conf_value_for(
            "client-output-buffer-limit", "replica 2048mb 2048mb 300", "slave 2147483648 2147483648 300"
        )
        # A changed limit is still drift.
        assert not same_conf_value_for("client-output-buffer-limit", "slave 2048mb 2048mb 300", "replica 1gb 2gb 300")
        # The alias is scoped to client-output-buffer-limit.
        assert not same_conf_value_for("timeout", "slave", "replica")

    def test_value_helpers(self):
        # join_directive_values ported from runtime_test.go TestJoinDirectiveValues
        assert join_directive_values(["3600 1", "300 100"]) == "3600 1 300 100"
        assert join_directive_values(['"xxxxpasswd"']) == "xxxxpasswd"
        assert [parse_mem_bytes(v) for v in ("1kb", "1.5k", "100", "abc")] == [1024, 1536, 100, None]
        assert split_dbconfig_entries("save", "900 1\nsave 300 10") == ["900 1", "300 10"]
        assert split_dbconfig_entries("save", "") == [""]
        assert split_dbconfig_entries("timeout", "0") == ["0"]

    # quoting-only, rewrite normalization and alias pairs are not drift (ported from diff_test.go)
    @pytest.mark.parametrize("dbconfig,disk_text,memory,drifts", **_table(_COMPARE_CASES))
    def test_compare_directives(self, dbconfig, disk_text, memory, drifts):
        result = compare_directives(_expected(dbconfig), parse_disk_conf(disk_text), memory)
        assert [d.render() for d in result] == drifts

    def test_placeholders_resolved_and_unresolved_skipped(self):
        expected = _expected(
            {
                "port": "{{port}}",
                "bind": "{{address}} 127.0.0.1",
                "cluster-enabled": "{{cluster_enabled}}",
                "dir": "{{redis_data_dir}}/data",
                "databases": "{{databases}}",
                "rocks.blockcachemb": "{{rocks_blockcachemb}}",
                "slowlog-max-len": "{{unknown_future_placeholder}}",
            },
            cluster_enabled=True,
            check_databases=True,
        )
        assert expected == {
            "port": ["30000"],
            "bind": ["1.1.1.1 127.0.0.1"],
            "cluster-enabled": ["yes"],
            "dir": ["/data/redis/30000/data"],
        }

    def test_excluded_and_dynamic_directives_skipped(self):
        expected = _expected(
            {
                "requirepass": "{{password}}x",
                "masterauth": "abc",
                "masteruser": "def",
                "primaryauth": "abc",
                "primaryuser": "def",
                "rename-command": "config confxx \nrename-command flushdb cleandb",
                "maxmemory": "1gb",
                "appendonly": "yes",
                "databases": "16",
                "netiothreadnum": "4",
                "daemonize": "yes",
                "timeout": "0",
            }
        )
        assert expected == {"timeout": ["0"]}
        assert _expected({"databases": "16"}, check_databases=True) == {"databases": ["16"]}


_GB1, _GB2, _OF2, _P = "maxmemory 1gb\n", "maxmemory 2gb\n", "slaveof 1.1.1.2 30000\n", "port 30000\n"
_NESTED = {"i.conf": _GB1, "n.conf": "include {inst}/i.conf\n" + _OF2}
_CYCLE = {"a.conf": "include b.conf\n", "b.conf": "include a.conf\ntimeout 1\n"}
_DEEP = dict({"c{}.conf".format(i): "include c{}.conf\n".format(i + 1) for i in range(9)}, **{"c9.conf": _P})

# id, main redis.conf ({inst} = instance dir), extra files, expected expanded disk text
_EXPANSION_CASES = [
    ("none", _P + "# include /nowhere.conf\n\n", {}, _P + "# include /nowhere.conf\n\n"),
    (
        "absolute_in_place",
        _P + "include {inst}/i.conf\n" + _GB2,
        {"i.conf": "requirepass p1\n" + _GB1},
        _P + _GB1 + _GB2,
    ),
    ("relative", "include i.conf\n", {"i.conf": _GB1}, _GB1),
    ("quoted", 'INCLUDE "{inst}/i.conf"\n', {"i.conf": _GB1}, _GB1),
    ("nested", _P + "include n.conf\n", _NESTED, _P + _GB1 + _OF2),
    ("no_eol", "include n.conf\n" + _P, {"n.conf": "timeout 0"}, "timeout 0\n" + _P),
    ("after", "include i.conf\n" + _GB2, {"i.conf": _GB1}, _GB1 + _GB2),
    ("before", _GB2 + "include i.conf\n", {"i.conf": _GB1}, _GB2 + _GB1),
]
# id, main redis.conf, extra files, disk text expectations (see _assert_msg)
_EXPANSION_ERROR_CASES = [
    ("cycle", "include a.conf\n", _CYCLE, ["#CONFCHK_ERR include_cycle", "timeout 1"]),
    ("unreadable", "include missing.conf\n" + _P, {}, ["#CONFCHK_ERR include_unreadable {inst}/missing.conf", _P]),
    ("glob", "include /etc/redis/*.conf\n" + _P, {}, ["#CONFCHK_ERR include_glob /etc/redis/*.conf", _P]),
    ("no_path", "include\n" + _P, {}, ["#CONFCHK_ERR include_no_path ", _P]),
    ("too_deep", "include c0.conf\n", _DEEP, ["#CONFCHK_ERR include_too_deep", "!" + _P]),
]


@pytest.mark.skipif(not HOST_TOOLS_AVAILABLE, reason="bash/gzip/base64 required")
class TestStorageConfIncludeExpansion:
    """Ported from dbactuator pkg/redisconf effective_test.go, run through the bash collector."""

    @staticmethod
    def _disk(tmp_path, main: str, extra_files) -> str:
        inst = tmp_path / "data" / "redis" / "30000"
        sim = _StorageHostSim(tmp_path)
        for name, content in extra_files.items():
            sim.write_conf("data", 30000, name, content.format(inst=inst))
        sim.write_conf("data", 30000, "redis.conf", main.format(inst=inst))
        sim.answer(30000, "info", REDIS_MASTER_INFO)
        sim.answer(30000, "confxx", REDIS_CONFIG)
        _stdout, blocks = sim.run([30000])
        return _decode_section(blocks[30000]["disk"])

    @pytest.mark.parametrize("main,extra_files,expected", **_table(_EXPANSION_CASES))
    def test_expansion(self, tmp_path, main, extra_files, expected):
        assert self._disk(tmp_path, main, extra_files) == expected

    @pytest.mark.parametrize("main,extra_files,expectations", **_table(_EXPANSION_ERROR_CASES))
    def test_errors_are_marked(self, tmp_path, main, extra_files, expectations):
        inst = tmp_path / "data" / "redis" / "30000"
        _assert_msg(self._disk(tmp_path, main, extra_files), [e.format(inst=inst) for e in expectations])


def _cluster_ctx(
    dbconfig=None,
    cluster_type=ClusterType.TendisPredixyRedisCluster.value,
    modules=(),
    unresolved=(),
    dbconfig_error="",
):
    return StorageClusterContext(
        cluster_type=cluster_type,
        major_version="Redis-7",
        dbconfig=None if dbconfig_error else ({"port": "{{port}}"} if dbconfig is None else dbconfig),
        dbconfig_error=dbconfig_error,
        expected_modules=set(modules),
        unresolved_modules=list(unresolved),
    )


_BLOOM_SO, _CELL_SO = "redisbloom-2.6.13.so", "libredis_cell_0.3.1.so"
_SLAVE_DISK = _P + "slaveof 1.1.1.1 30000\n"
_OF3_DISK = _P + "slaveof 3.3.3.3 30000\n"
_BLOOM_DISK = _P + "loadmodule /usr/local/redis/modules/" + _BLOOM_SO + "\n"
_CELL_DISK = _P + "loadmodule /usr/local/redis/modules/" + _CELL_SO + "\n"
_LINK_DOWN = REDIS_SLAVE_INFO.replace("master_link_status:up", "master_link_status:down")
_STORE3_DOWN = TENDISPLUS_SLAVE_INFO.replace("src_store_id=3,state=online", "src_store_id=3,state=connecting")
_STORE3_MSG = "rocksdb3_master=1.1.1.1:30000(state=connecting)"
_MODULE_MSGS = ["missing_on_disk=['" + _BLOOM_SO + "']", "unexpected_on_disk=['" + _CELL_SO + "']"]
_POLICY_MSG = "[conf] maxmemory-policy(dbconfig=noeviction, memory=allkeys-lru, disk=noeviction)"
_BOTH_PATHS = ["/data1/redis/30000/redis.conf", "/data/redis/30000/redis.conf"]
_CYCLE_ERR = "include_cycle /data/redis/30000/a.conf"
_WRONG_MASTER_MSG = "expected_master=3.3.3.3:30000, memory_master=1.1.1.1:30000"
_TIMEOUT_MSGS = ["[collect] repl=redis_cmd_timeout", "timeout(dbconfig=300"]
_MANY = ["x-directive-{:02d}".format(i) for i in range(25)]
_MANY_DISK = _P + "".join("{} no\n".format(name) for name in _MANY)
_MANY_MSGS = [
    "[repl-disk]",
    "[module] missing_on_disk=['m.so']",
    "x-directive-19(",
    "!x-directive-20(",
    "... and 5 more",
]

_PLUS = {"cluster_type": ClusterType.TendisPredixyTendisplusCluster.value}
_TWEM = {"cluster_type": ClusterType.TendisTwemproxyRedisInstance.value}
_BLOOM_CTX = {"dbconfig": {"port": "{{port}}", "loadmodule": "redisbloom"}, "modules": [_BLOOM_SO]}
_POLICY_CTX = {"dbconfig": {"port": "{{port}}", "maxmemory-policy": "noeviction"}}
_TIMEOUT_CTX = {"dbconfig": {"port": "{{port}}", "timeout": "300"}}
_MANY_CTX = dict(_TWEM, dbconfig=dict({name: "yes" for name in _MANY}, port="{{port}}"), modules=["m.so"])

_POLICY_BLOCK = {"disk": _P + "maxmemory-policy noeviction\n", "mem": "port\n30000\nmaxmemory-policy\nallkeys-lru\n"}
_TIMEOUT_BLOCK = {"disk": _P + "timeout 0\n", "repl": None, "repl_err": "redis_cmd_timeout"}

# id, meta role, cluster context overrides ("missing" = none attached), _storage_block overrides
# (None = no host data, "master" key overrides meta master), expected state, msg expectations (see _assert_msg)
_CHECKER_CASES = [
    ("master_ok", "master", {}, {}, NORMAL, ["1.1.1.1:30000"]),
    (
        "master_running_as_slave",
        "master",
        {},
        {"repl": REDIS_SLAVE_INFO},
        ABNORMAL,
        ["meta=redis_master, actual=slave"],
    ),
    (
        "slave_of_wrong_master",
        "slave",
        {},
        {"master": "3.3.3.3:30000", "disk": _OF3_DISK},
        ABNORMAL,
        [_WRONG_MASTER_MSG],
    ),
    ("slave_link_down", "slave", {}, {"repl": _LINK_DOWN}, ABNORMAL, ["master_link_status=down"]),
    ("slave_without_meta_master", "slave", {}, {"master": ""}, ABNORMAL, ["StorageInstanceTuple"]),
    ("plus_stores_online", "slave", _PLUS, {"disk": _P, "repl": TENDISPLUS_SLAVE_INFO}, NORMAL, []),
    (
        "plus_store_down",
        "slave",
        _PLUS,
        {"disk": _P, "repl": _STORE3_DOWN},
        ABNORMAL,
        [_STORE3_MSG, "!rocksdb2_master"],
    ),
    ("master_with_disk_slaveof", "master", {}, {"disk": _OF3_DISK}, ABNORMAL, ["[repl-disk]", "3.3.3.3:30000"]),
    ("master_slaveof_no_one", "master", {}, {"disk": _P + "slaveof no one\n"}, NORMAL, []),
    ("twem_slave_slaveof", "slave", _TWEM, {}, NORMAL, []),
    ("twem_slave_replicaof", "slave", _TWEM, {"disk": _P + "replicaof 1.1.1.1 30000\n"}, NORMAL, []),
    ("twem_slave_disk_absent", "slave", _TWEM, {"disk": _P}, ABNORMAL, ["disk_master=<absent>"]),
    ("twem_slave_disk_wrong", "slave", _TWEM, {"disk": _OF3_DISK}, ABNORMAL, ["disk_master=3.3.3.3:30000"]),
    ("cluster_slave_skips_disk", "slave", {}, {"disk": _P}, NORMAL, []),
    ("modules_match", "master", _BLOOM_CTX, {"disk": _BLOOM_DISK}, NORMAL, []),
    (
        "module_missing_and_unexpected",
        "master",
        {"modules": [_BLOOM_SO]},
        {"disk": _CELL_DISK},
        ABNORMAL,
        _MODULE_MSGS,
    ),
    ("module_unresolved", "master", {"unresolved": ["unknown_mod"]}, {}, ABNORMAL, ["unknown_mod"]),
    ("conf_drift", "master", _POLICY_CTX, _POLICY_BLOCK, ABNORMAL, [_POLICY_MSG]),
    ("several_failures_capped", "slave", _MANY_CTX, {"disk": _MANY_DISK}, ABNORMAL, _MANY_MSGS),
    ("no_host_data", "master", {}, None, ABNORMAL, ["no_host_data", "![conf]"]),
    ("repl_timeout_keeps_disk", "master", _TIMEOUT_CTX, _TIMEOUT_BLOCK, ABNORMAL, _TIMEOUT_MSGS),
    ("conf_in_both_data_dirs", "master", {}, {"conf_paths": _BOTH_PATHS}, ABNORMAL, _BOTH_PATHS),
    ("include_error", "master", {}, {"disk": _P + "#CONFCHK_ERR " + _CYCLE_ERR + "\n"}, ABNORMAL, [_CYCLE_ERR]),
    ("dbconfig_unavailable", "master", {"dbconfig_error": "dbconfig timeout"}, {}, ABNORMAL, ["dbconfig timeout"]),
    ("missing_cluster_context", "master", "missing", {}, ABNORMAL, ["[conf]"]),
]


class TestStorageConfChecker:
    @pytest.mark.parametrize("role,ctx,block,state,expectations", **_table(_CHECKER_CASES))
    def test_evaluate(self, role, ctx, block, state, expectations):
        is_slave = role == "slave"
        block = None if block is None else dict(block)
        master = (block or {}).pop("master", "1.1.1.1:30000")
        extra = {"meta_role": "redis_" + role, "expected_master": master if is_slave else ""}
        if ctx != "missing":
            extra[CLUSTER_CTX_KEY] = _cluster_ctx(**ctx)
        target = CheckTarget(
            cluster_id=1, bk_cloud_id=0, ip="2.2.2.2" if is_slave else "1.1.1.1", port=30000, extra=extra
        )
        if block is not None:
            block.setdefault("mem", "port\n30000\n")
            if is_slave:
                block.setdefault("disk", _SLAVE_DISK)
                block.setdefault("repl", REDIS_SLAVE_INFO)
            block = _storage_block(**block)

        results = StorageConfChecker().evaluate(target, None, block)

        assert [r.state for r in results] == [state]
        _assert_msg(results[0].msg, expectations)

    def test_lifecycle_flags(self):
        checker = StorageConfChecker()
        target = CheckTarget(cluster_id=1, bk_cloud_id=0, ip="1.1.1.1", port=30000)
        assert checker.requires_host_script is True
        assert checker.drs_request(target) is None
        assert checker.host_script_snippet([target, target]).count('__dbm_scc_port "30000"') == 2

    @staticmethod
    def _storage(inst_id, ip, role, status="running", master=None):
        """master: (ip, port) prefetched pair, None = prefetched without pair, False = not prefetched."""
        pairs = []
        if master:
            pairs = [SimpleNamespace(ejector=SimpleNamespace(machine=SimpleNamespace(ip=master[0]), port=master[1]))]
        return SimpleNamespace(
            id=inst_id,
            port=30000,
            status=status,
            instance_role=role,
            machine=SimpleNamespace(ip=ip),
            as_receiver=SimpleNamespace(all=lambda: pairs),
            _prefetched_objects_cache={} if master is False else {"as_receiver": pairs},
        )

    @staticmethod
    def _cluster(storages):
        return SimpleNamespace(
            id=1,
            bk_cloud_id=0,
            storageinstance_set=SimpleNamespace(all=lambda: storages),
            _prefetched_objects_cache={"storageinstance_set": storages},
        )

    def test_collect_targets_running_with_prefetched_master(self):
        storages = [
            self._storage(1, "1.1.1.1", "redis_master"),
            self._storage(2, "2.2.2.2", "redis_slave", master=("1.1.1.1", 30000)),
            self._storage(3, "3.3.3.3", "redis_slave", status="unavailable", master=("1.1.1.1", 30000)),
        ]
        with patch(_STORAGE_CONF_MOD + ".StorageInstanceTuple") as tuple_model:
            targets = StorageConfChecker().collect_targets(self._cluster(storages))
        tuple_model.objects.filter.assert_not_called()
        assert [(t.ip, t.extra["meta_role"], t.extra["expected_master"]) for t in targets] == [
            ("1.1.1.1", "redis_master", ""),
            ("2.2.2.2", "redis_slave", "1.1.1.1:30000"),
        ]

    def test_collect_targets_queries_tuples_when_not_prefetched(self):
        storages = [
            self._storage(1, "1.1.1.1", "redis_master", master=False),
            self._storage(2, "2.2.2.2", "redis_slave", master=False),
        ]
        with patch(_STORAGE_CONF_MOD + ".StorageInstanceTuple") as tuple_model:
            tuple_model.objects.filter.return_value.values.return_value = [
                {"receiver_id": 2, "ejector__machine__ip": "1.1.1.1", "ejector__port": 30000}
            ]
            targets = StorageConfChecker().collect_targets(self._cluster(storages))
        tuple_model.objects.filter.assert_called_once_with(receiver_id__in=[1, 2])
        assert targets[1].extra["expected_master"] == "1.1.1.1:30000"


class TestStorageConfClusterContext:
    @staticmethod
    def _target_info(cluster_id, ip):
        return {
            "cluster_id": cluster_id,
            "cluster": "cache{}.test.db".format(cluster_id),
            "cluster_type": ClusterType.TendisPredixyRedisCluster.value,
            "bk_biz_id": 1,
            "bk_cloud_id": 0,
            "checker": "storage_conf",
            "ip": ip,
            "port": 30000,
            "extra": {"meta_role": "redis_master", "expected_master": ""},
        }

    @staticmethod
    def _patch_meta(stack, dbconfig, module_rows=()):
        def meta_clusters(id__in):
            return [
                SimpleNamespace(
                    id=cid,
                    bk_biz_id=1,
                    immute_domain="cache{}.test.db".format(cid),
                    cluster_type=ClusterType.TendisPredixyRedisCluster.value,
                    major_version="Redis-7",
                )
                for cid in sorted(id__in)
            ]

        stack.enter_context(patch(_STORAGE_CONF_MOD + ".Cluster")).objects.filter.side_effect = meta_clusters
        module_model = stack.enter_context(patch(_STORAGE_CONF_MOD + ".TbRedisModuleSupport"))
        module_model.objects.filter.return_value.values_list.return_value = list(module_rows)
        query = stack.enter_context(patch(_STORAGE_CONF_MOD + ".query_cluster_dbconf_map"))
        query.side_effect = dbconfig if callable(dbconfig) else (lambda **_kw: dict(dbconfig))
        return query, module_model

    @patch(COMPONENTS + ".ingest_daily_cluster_rows")
    @patch(COMPONENTS + ".RedisReportWriter")
    def test_evaluate_loads_dbconfig_once_per_cluster(self, writer_cls, _ingest):
        target_infos = [self._target_info(cid, ip) for cid in (1, 2) for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3")]
        host_conf_data = {
            ("storage_conf", info["ip"], 30000): _storage_block(disk=_BLOOM_DISK, mem="port\n30000\n")
            for info in target_infos
        }
        with ExitStack() as stack:
            query, module_model = self._patch_meta(
                stack,
                {"port": "{{port}}", "loadmodule": "redisbloom"},
                module_rows=[("Redis-7", "redisbloom", "redisbloom-2.6.13.so")],
            )
            ok, abnormal = _evaluate_and_report([], host_conf_data, "system", target_infos=target_infos)

        assert sorted(call.kwargs["level_value"] for call in query.call_args_list) == [
            "cache1.test.db",
            "cache2.test.db",
        ]
        module_model.objects.filter.assert_called_once()
        assert (ok, abnormal) == (2, 0)
        assert all(CLUSTER_CTX_KEY not in info["extra"] for info in target_infos)
        rows = writer_cls.return_value.write_redis_reports.call_args.args[0]
        assert {row["instance"] for row in rows} == {"all"}

    @patch(COMPONENTS + ".ingest_daily_cluster_rows")
    @patch(COMPONENTS + ".RedisReportWriter")
    def test_prepare_failure_marks_targets_abnormal(self, writer_cls, _ingest):
        with patch(_STORAGE_CONF_MOD + ".Cluster") as cluster_model:
            cluster_model.objects.filter.side_effect = RuntimeError("db down")
            ok, abnormal = _evaluate_and_report(
                [],
                {("storage_conf", "1.1.1.1", 30000): _storage_block(mem="port\n30000\n")},
                "system",
                target_infos=[self._target_info(1, "1.1.1.1")],
            )
        assert (ok, abnormal) == (0, 1)
        assert "[conf]" in writer_cls.return_value.write_redis_reports.call_args.args[0][0]["msg"]

    def test_load_cluster_contexts_resolves_modules_and_errors(self):
        def dbconfig(**kwargs):
            if kwargs["level_value"] == "cache2.test.db":
                raise RuntimeError("dbconfig timeout")
            return {"loadmodule": "redisbloom, unknown_mod"}

        with ExitStack() as stack:
            self._patch_meta(stack, dbconfig, module_rows=[("Redis-7", "redisbloom", "redisbloom-2.6.13.so")])
            contexts = load_cluster_contexts({1, 2})

        assert (contexts[1].expected_modules, contexts[1].unresolved_modules) == (
            {"redisbloom-2.6.13.so"},
            ["unknown_mod"],
        )
        assert contexts[2].dbconfig is None
        assert "dbconfig timeout" in contexts[2].dbconfig_error

    def test_load_batch_clusters_prefetches_replication_pairs(self):
        with patch(COMPONENTS + ".Cluster") as cluster_model:
            cluster_model.objects.filter.return_value.prefetch_related.return_value = []
            _load_batch_clusters([{"cluster_id": 1}])
        prefetches = cluster_model.objects.filter.return_value.prefetch_related.call_args.args
        storage = next(p for p in prefetches if p.prefetch_through == "storageinstance_set")
        nested = [getattr(lookup, "prefetch_through", lookup) for lookup in storage.queryset._prefetch_related_lookups]
        assert "as_receiver" in nested


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
    def test_run_single_drs_chunk_empty_result_records_error(self):
        with patch(
            "backend.flow.plugins.components.collections.redis.conf_check.components.DRSApi.redis_rpc",
            return_value=[{"address": "1.1.1.1:30000", "result": "", "error_msg": "auth failed"}],
        ):
            result, errors = _run_single_drs_chunk(
                (0, 1, "redis_password", "INFO REPLICATION"),
                ["1.1.1.1:30000"],
                {1: {"redis_password": "pwd"}},
                {},
            )
        assert result == {}
        assert errors[(0, "INFO REPLICATION", "1.1.1.1:30000")] == "empty_result: auth failed"

    def test_run_drs_chunk_slice_parallel(self):
        chunk_slice = [
            ((0, 1, "redis_password", "INFO REPLICATION"), ["1.1.1.1:30000"]),
            ((0, 2, "redis_password", "INFO REPLICATION"), ["1.1.1.2:30000"]),
            ((0, 3, "redis_password", "INFO REPLICATION"), ["1.1.1.3:30000"]),
        ]

        def fake_redis_rpc(payload):
            addresses = payload["addresses"]
            if addresses == ["1.1.1.2:30000"]:
                raise Exception("boom")
            return [{"address": address, "result": "role:master"} for address in addresses]

        with patch(
            "backend.flow.plugins.components.collections.redis.conf_check.components.DRSApi.redis_rpc",
            side_effect=fake_redis_rpc,
        ) as redis_rpc:
            password_cache = {
                1: {"redis_password": "pwd"},
                2: {"redis_password": "pwd"},
                3: {"redis_password": "pwd"},
            }
            result_map, errors = _run_drs_chunk_slice(chunk_slice, password_cache, {})

        assert redis_rpc.call_count == 3
        assert result_map[(0, "INFO REPLICATION", "1.1.1.1:30000")] == "role:master"
        assert result_map[(0, "INFO REPLICATION", "1.1.1.3:30000")] == "role:master"
        assert (0, "INFO REPLICATION", "1.1.1.2:30000") not in result_map
        assert "drs_rpc_error: boom" in errors[(0, "INFO REPLICATION", "1.1.1.2:30000")]


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
        "backend.flow.plugins.components.collections.redis.conf_check.components._run_drs_chunk_slice",
        return_value=({(0, "INFO REPLICATION", "1.1.1.1:30000"): "role:master"}, {}),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._get_password_cache_for_drs",
        return_value=({1: {"redis_password": "pwd"}}, {}),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._evaluate_and_report",
        return_value=(1, 0),
    )
    def test_drs_chunks_paced_across_ticks(self, _evaluate, _passwords, _run_slice):
        service = self._make_service()
        queue = [((0, 1, "redis_password", "INFO REPLICATION"), ["1.1.1.1:30000"])] * 3
        data = self._make_data(
            phase=PHASE_RUN_DRS,
            target_infos=[],
            poll_count=0,
            pending_jobs={},
            drs_chunk_queue=queue,
            drs_cursor=0,
            drs_result_map={},
            drs_error_map={},
            issue_failed_targets={},
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
        assert _run_slice.call_count == 3

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._run_drs_chunk_slice",
        return_value=({(0, "INFO REPLICATION", "1.1.1.1:30000"): "role:master"}, {}),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._get_password_cache_for_drs",
        return_value=({1: {"redis_password": "pwd"}}, {}),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._evaluate_and_report",
        return_value=(1, 0),
    )
    def test_drs_chunks_per_tick_batches_slice(self, _evaluate, _passwords, _run_slice):
        service = self._make_service()
        queue = [((0, 1, "redis_password", "INFO REPLICATION"), ["1.1.1.1:30000"])] * 3
        data = self._make_data(
            phase=PHASE_RUN_DRS,
            target_infos=[],
            poll_count=0,
            pending_jobs={},
            drs_chunk_queue=queue,
            drs_cursor=0,
            drs_result_map={},
            drs_error_map={},
            issue_failed_targets={},
        )
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
                "drs_chunks_per_tick": 3,
            },
            "global_data": {"created_by": "tester"},
        }.get(key)

        assert service._schedule(data, {}) is True
        assert data.outputs.drs_cursor == 3
        assert data.outputs.phase == PHASE_EVALUATE
        _run_slice.assert_called_once()
        assert len(_run_slice.call_args[0][0]) == 3

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
            issue_failed_targets={},
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

    JOB = {"job_instance_id": 99, "bk_cloud_id": 0, "exec_ip": "1.1.1.1", "conf_targets": []}
    DRS_QUEUE = [((0, 1, "redis_proxy_password", "INFO SERVERS"), ["1.1.1.9:50000"])]
    ISSUE_MARKER = {("storage_conf", "2.2.2.2", 30000): {"error": "job_issue_failed: boom"}}
    LOG_BLOCK = {("storage_conf", "1.1.1.1", 30000): {"disk": "x"}}

    def _scheduled_data(self, **overrides):
        outputs = dict(
            phase=PHASE_RUN_DRS,
            target_infos=[{"checker": "storage_conf", "cluster_id": 1}],
            poll_count=0,
            pending_jobs={99: dict(self.JOB)},
            completed_jobs=[],
            failed_jobs=[],
            issue_failed_targets=dict(self.ISSUE_MARKER),
            drs_chunk_queue=list(self.DRS_QUEUE),
            drs_cursor=0,
            drs_result_map={},
            drs_error_map={},
        )
        outputs.update(overrides)
        return self._make_data(**outputs)

    @staticmethod
    def _poll_results(*statuses):
        """_poll_jobs_once side effect for job 99, one status per tick: running / completed / failed."""
        remaining = list(statuses)

        def poll(pending, completed, failed):
            status = remaining.pop(0)
            if status != "running":
                job = pending.pop(99)
                (completed if status == "completed" else failed).append(job)
            return pending, completed, failed, 1

        return poll

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
        return_value=([{"checker": "storage_conf"}], {"target_count": 1}),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._build_host_map",
        return_value={(0, "1.1.1.1"): {"snippets": ["echo"], "conf_targets": []}},
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._build_drs_chunk_queue",
        return_value=DRS_QUEUE,
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._issue_host_jobs",
        return_value=([JOB], 0),
    )
    def test_execute_runs_drs_before_polling_jobs(self, _issue, _queue, _host_map, _targets, _runtime, _resolve):
        data = self._make_data()
        self._make_service()._execute(data, {})
        assert data.outputs.phase == PHASE_RUN_DRS
        assert 99 in data.outputs.pending_jobs
        assert data.outputs.issue_failed_targets == {}
        assert not hasattr(data.outputs, "host_conf_data")

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._evaluate_and_report",
        return_value=(1, 0),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._collect_host_conf_data",
        return_value=LOG_BLOCK,
    )
    @patch("backend.flow.plugins.components.collections.redis.conf_check.components._poll_jobs_once")
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._get_password_cache_for_drs",
        return_value=({}, {}),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._run_drs_chunk_slice",
        return_value=({(0, "INFO SERVERS", "1.1.1.9:50000"): "ok"}, {}),
    )
    def test_drs_then_poll_then_inline_evaluate(self, _run_slice, _passwords, poll, collect, evaluate):
        poll.side_effect = self._poll_results("running", "completed")
        service = self._make_service()
        data = self._scheduled_data()

        assert service._schedule(data, {}) is True
        assert data.outputs.phase == PHASE_POLL_JOBS
        assert poll.call_count == 1
        collect.assert_not_called()
        evaluate.assert_not_called()

        assert service._schedule(data, {}) is True
        collect.assert_called_once()
        assert collect.call_args.args[0][0]["job_instance_id"] == 99
        host_conf_data = evaluate.call_args.args[1]
        assert host_conf_data == {**self.ISSUE_MARKER, **self.LOG_BLOCK}
        assert evaluate.call_args.kwargs["drs_result_map"] == {(0, "INFO SERVERS", "1.1.1.9:50000"): "ok"}
        service.finish_schedule.assert_called_once()
        assert not hasattr(data.outputs, "host_conf_data")
        assert data.outputs.issue_failed_targets == self.ISSUE_MARKER

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._evaluate_and_report",
        return_value=(0, 1),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._collect_host_conf_data",
        return_value={},
    )
    @patch("backend.flow.plugins.components.collections.redis.conf_check.components._poll_jobs_once")
    def test_poll_timeout_marks_jobs_and_evaluates_same_tick(self, poll, collect, evaluate):
        service = self._make_service()
        data = self._scheduled_data(phase=PHASE_POLL_JOBS, drs_chunk_queue=[], poll_count=3, issue_failed_targets={})

        assert service._schedule(data, {}) is True
        poll.assert_not_called()
        host_conf_data = evaluate.call_args.args[1]
        assert host_conf_data == {}  # conf_targets empty -> nothing to mark
        assert data.outputs.failed_jobs[0]["failure_reason"] == "job_timeout"
        service.finish_schedule.assert_called_once()

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._evaluate_and_report",
        return_value=(0, 1),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._collect_host_conf_data",
        return_value={},
    )
    @patch("backend.flow.plugins.components.collections.redis.conf_check.components._poll_jobs_once")
    def test_failed_job_targets_marked_in_evaluate(self, poll, collect, evaluate):
        poll.side_effect = self._poll_results("failed")
        job = dict(self.JOB, conf_targets=[{"checker": "storage_conf", "port": 30000, "cluster_id": 1}])
        data = self._scheduled_data(phase=PHASE_POLL_JOBS, drs_chunk_queue=[], pending_jobs={99: job})

        assert self._make_service()._schedule(data, {}) is True
        host_conf_data = evaluate.call_args.args[1]
        assert host_conf_data[("storage_conf", "1.1.1.1", 30000)] == {"error": "job_failed"}

    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._evaluate_and_report",
        return_value=(1, 0),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._collect_host_conf_data",
        return_value=LOG_BLOCK,
    )
    @patch("backend.flow.plugins.components.collections.redis.conf_check.components._poll_jobs_once")
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._get_password_cache_for_drs",
        return_value=({}, {}),
    )
    @patch(
        "backend.flow.plugins.components.collections.redis.conf_check.components._run_drs_chunk_slice",
        return_value=({}, {}),
    )
    def test_outputs_from_previous_phase_order_still_finish(self, _run_slice, _passwords, poll, collect, evaluate):
        poll.side_effect = self._poll_results("completed")
        legacy_marker = {("predixy_servers", "1.1.1.9", 50000): {"error": "job_failed"}}
        data = self._scheduled_data(phase=PHASE_POLL_JOBS)
        del data.outputs.issue_failed_targets
        data.outputs.host_conf_data = legacy_marker
        service = self._make_service()

        assert service._schedule(data, {}) is True
        assert data.outputs.phase == PHASE_RUN_DRS
        evaluate.assert_not_called()

        assert service._schedule(data, {}) is True
        _run_slice.assert_called_once()
        assert evaluate.call_args.args[1] == {**legacy_marker, **self.LOG_BLOCK}
        service.finish_schedule.assert_called_once()


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
        config = SimpleNamespace(
            bk_cloud_ids=[], customized={"storage_conf": {"bk_cloud_ids": [0]}}, cluster_types=None
        )
        filters = checker_query_filters(config, StorageConfChecker())
        assert filters["bk_cloud_ids"] == [0]

    def test_retired_role_override_applies_to_storage_conf(self):
        config = SimpleNamespace(
            bk_cloud_ids=[],
            bizs_ignored=[3],
            customized={"role": {"bk_cloud_ids": [0], "bizs_ignored": [5]}},
            cluster_types=None,
        )
        filters = checker_query_filters(config, StorageConfChecker())
        assert filters["bk_cloud_ids"] == [0]
        assert filters["bizs_ignored"] == [5]

    def test_storage_conf_override_wins_over_retired_role(self):
        config = SimpleNamespace(
            bk_cloud_ids=[],
            customized={"role": {"bk_cloud_ids": [0]}, "storage_conf": {"bk_cloud_ids": [1]}},
            cluster_types=None,
        )
        filters = checker_query_filters(config, StorageConfChecker())
        assert filters["bk_cloud_ids"] == [1]

    def test_role_override_does_not_leak_to_other_checkers(self):
        config = SimpleNamespace(bk_cloud_ids=[], customized={"role": {"bk_cloud_ids": [0]}}, cluster_types=None)
        assert checker_query_filters(config, PredixyServersChecker())["bk_cloud_ids"] == []

    @patch(COMPONENTS + "._collapse_conf_check_report_rows", side_effect=lambda rows: rows)
    @patch(COMPONENTS + ".ingest_daily_cluster_rows")
    @patch(COMPONENTS + ".RedisReportWriter")
    def test_evaluate_passes_retired_role_override_as_checker_config(self, _writer, _ingest, _collapse):
        checker = MagicMock()
        checker.name = "storage_conf"
        checker.drs_request.return_value = None
        checker.evaluate.return_value = []
        target_info = {
            "cluster_id": 1,
            "cluster": "cache.test.db",
            "cluster_type": ClusterType.TendisPredixyRedisCluster.value,
            "bk_biz_id": 1,
            "bk_cloud_id": 0,
            "checker": "storage_conf",
            "ip": "1.1.1.1",
            "port": 30000,
            "extra": {},
        }
        with patch(COMPONENTS + "._checker_by_name", return_value=checker):
            _evaluate_and_report(
                [], {}, "system", target_infos=[target_info], checker_customized={"role": {"foo": "bar"}}
            )
        assert checker.evaluate.call_args.kwargs["checker_config"] == {"foo": "bar"}

    @patch("backend.flow.plugins.components.collections.redis.conf_check.candidate_selection.Cluster")
    def test_customized_excludes_checker_by_cloud(self, cluster_model):
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
            if types == set(StorageConfChecker().cluster_types):
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
            customized={"storage_conf": {"bk_cloud_ids": [0]}, "predixy_servers": {"bk_cloud_ids": [1]}},
        )
        result = get_candidate_cluster_tuples(config)
        assert (0, 1) in result
        assert (1, 2) in result
        assert len(result) == 2
