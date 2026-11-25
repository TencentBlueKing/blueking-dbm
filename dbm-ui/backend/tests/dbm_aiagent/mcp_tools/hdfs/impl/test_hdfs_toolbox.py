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

import os
import subprocess
from types import SimpleNamespace

import pytest

from backend.dbm_aiagent.mcp_tools.hdfs.impl import hdfs_toolbox as mod

ROOT = mod.ICEBERG_WAREHOUSE_ROOT
DB_A = ROOT + "/db_a.db"
DB_B = ROOT + "/db_b.db"
DOMAIN = "hdfs.test.db"
TARGET = {"cluster_id": 12, "cluster_name": "hdfs-test", "datanode_ip": "127.0.0.1", "bk_cloud_id": 0}
LOCK_KEY = "dbm_aiagent:hdfs_toolbox_lock:12_hdfs-test"
JOB_ID = 1001
TASK_KEY = "dbm_aiagent:hdfs_toolbox_task:{}".format(JOB_ID)
# 用 shell 函数顶替 hdfs 命令，脚本其余部分（含 awk）原样在本机 bash 中执行
_HDFS_STUB = 'hdfs() { printf \'%s\\n\' "$FAKE_HDFS_OUTPUT"; return "${FAKE_HDFS_RC:-0}"; }\n'


def _ls_line(path, is_dir=True):
    flag = "drwxr-xr-x" if is_dir else "-rw-r--r--"
    return "{}   - hdfs supergroup          0 2026-11-10 10:00 {}".format(flag, path)


def _raw_ls(dirs, files=()):
    lines = ["SLF4J: Class path contains multiple SLF4J bindings.", "Found {} items".format(len(dirs) + len(files))]
    lines += [_ls_line(path) for path in dirs]
    lines += [_ls_line(path, is_dir=False) for path in files]
    return "\n".join(lines)


def _run_script(script, hdfs_output, rc=0):
    env = {"PATH": os.environ["PATH"], "FAKE_HDFS_OUTPUT": hdfs_output, "FAKE_HDFS_RC": str(rc)}
    proc = subprocess.run(["bash"], input=_HDFS_STUB + script, text=True, capture_output=True, check=True, env=env)
    return proc.stdout


def _run_and_parse(task, hdfs_output, rc=0):
    return task.parse(mod.parse_marked_output(_run_script(task.build_script(), hdfs_output, rc)))


# du 专用替身：hdfs dfs -du -s <path> 的 path 是第 4 个参数；命中 FAKE_FAIL_PATH（* 表示全部）时失败
_DU_STUB = (
    "hdfs() {\n"
    '  if [ "$FAKE_FAIL_PATH" = "*" ] || [ "$4" = "$FAKE_FAIL_PATH" ]; then\n'
    '    for i in $(seq "$FAKE_ERROR_LINES"); do echo "du: $4: No such file or directory"; done\n'
    "    return 1\n"
    "  fi\n"
    '  echo "10 30 $4"\n'
    "}\n"
)


def _run_du_script(task, fail_path="", error_lines=1):
    env = {"PATH": os.environ["PATH"], "FAKE_FAIL_PATH": fail_path, "FAKE_ERROR_LINES": str(error_lines)}
    script = task.build_script().replace("sleep {}".format(mod.DU_GAP_SECONDS), ":")
    proc = subprocess.run(["bash"], input=_DU_STUB + script, text=True, capture_output=True, check=True, env=env)
    return proc.stdout


class _FakeCache:
    """内存版 cache，只实现用到的 add / set / get / delete，不依赖 Redis。"""

    def __init__(self):
        self.store = {}
        self.timeouts = {}

    def add(self, key, value, timeout=None):
        if key in self.store:
            return False
        self.store[key] = value
        self.timeouts[key] = timeout
        return True

    def set(self, key, value, timeout=None):
        self.store[key] = value
        self.timeouts[key] = timeout

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)


class _BrokenCache:
    def add(self, *args, **kwargs):
        raise ConnectionError("redis down")

    def get(self, *args, **kwargs):
        raise ConnectionError("redis down")


def _prepare(monkeypatch, submit=None):
    """替换缓存、执行机与 Job 提交，返回 (cache, 已提交的 Job 列表)。"""
    fake_cache = _FakeCache()
    submitted = []

    def fake_submit(target, script, task_name):
        submitted.append({"target": target, "script": script, "task_name": task_name})
        return JOB_ID

    monkeypatch.setattr(mod, "cache", fake_cache)
    monkeypatch.setattr(mod, "_resolve_execution_target", lambda *args, **kwargs: dict(TARGET))
    monkeypatch.setattr(mod, "_submit_job", submit or fake_submit)
    return fake_cache, submitted


def _job_status(monkeypatch, finished, log=""):
    resp = {"finished": finished, "job_log_resp": [{"log_content": log}] if finished else []}
    monkeypatch.setattr(mod, "get_job_exec_status", lambda job_instance_id: resp)


class TestPathValidation:
    def test_rejects_shell_metacharacters_and_parent_segments(self):
        with pytest.raises(ValueError):
            mod.validate_hdfs_path("/data/db;rm")
        with pytest.raises(ValueError):
            mod.validate_hdfs_path("/data/db/../../etc")

    def test_db_dir_must_be_first_level_under_warehouse(self):
        assert mod.validate_iceberg_db_dir(DB_A + "/") == DB_A
        for path in (ROOT, DB_A + "/t1", "/data/hive/warehouse/db.db", "/data/iceberg/warehouse_bak/db.db"):
            with pytest.raises(ValueError):
                mod.validate_iceberg_db_dir(path)

    def test_table_dir_must_be_second_level_under_warehouse(self):
        assert mod.validate_iceberg_table_dir(DB_A + "/t1/") == DB_A + "/t1"
        for path in (DB_A, DB_A + "/t1/data", "/data/hive/warehouse/db.db/t1"):
            with pytest.raises(ValueError):
                mod.validate_iceberg_table_dir(path)


class TestListDbsTask:
    def test_only_directories_are_dbs(self):
        result = _run_and_parse(mod.ListIcebergDbsTask(), _raw_ls([DB_B, DB_A], files=[ROOT + "/README"]))
        assert result["db_dirs"] == [DB_A, DB_B]
        assert result["db_count"] == 2
        assert result["truncated"] is False
        assert result["message"] == ""

    def test_over_max_returns_first_max_and_total(self):
        dbs = ["{}/db_{:03d}.db".format(ROOT, index) for index in range(mod.DB_COUNT_MAX + 1)]
        result = _run_and_parse(mod.ListIcebergDbsTask(), _raw_ls(dbs))
        assert result["db_count"] == mod.DB_COUNT_MAX + 1
        assert result["db_dirs"] == dbs[: mod.DB_COUNT_MAX]
        assert result["truncated"] is True
        assert result["message"]

    def test_lists_warehouse_root(self):
        assert "hdfs dfs -ls '{}'".format(ROOT) in mod.ListIcebergDbsTask().build_script()


class TestListTablesTask:
    def test_lists_only_the_given_db(self):
        task = mod.ListIcebergTablesTask(DB_A + "/")
        assert task.params() == {"db_dir": DB_A}
        assert "hdfs dfs -ls '{}'".format(DB_A) in task.build_script()

    def test_files_under_db_are_not_tables(self):
        task = mod.ListIcebergTablesTask(DB_A)
        result = _run_and_parse(task, _raw_ls([DB_A + "/t2", DB_A + "/t1"], files=[DB_A + "/_SUCCESS"]))
        assert result == {
            "db_dir": DB_A,
            "table_count": 2,
            "truncated": False,
            "message": "",
            "table_dirs": [DB_A + "/t1", DB_A + "/t2"],
        }

    def test_over_max_returns_first_max_and_total(self):
        tables = ["{}/t{:03d}".format(DB_A, index) for index in range(mod.TABLE_COUNT_MAX + 1)]
        result = _run_and_parse(mod.ListIcebergTablesTask(DB_A), _raw_ls(tables))
        assert result["table_count"] == mod.TABLE_COUNT_MAX + 1
        assert result["table_dirs"] == tables[: mod.TABLE_COUNT_MAX]
        assert result["truncated"] is True

    @pytest.mark.parametrize("path", [ROOT, DB_A + "/t1", "/data/hive/warehouse/db.db", "/data/a b"])
    def test_rejects_non_db_dir(self, path):
        with pytest.raises(mod.DBMMcpBaseException):
            mod.ListIcebergTablesTask(path)

    def test_ls_failure_is_an_error(self):
        task = mod.ListIcebergTablesTask(DB_A)
        with pytest.raises(mod.DBMMcpBaseException):
            _run_and_parse(task, "ls: `{}': No such file or directory".format(DB_A), rc=1)

    def test_dir_name_with_space_is_parsed_in_full(self):
        spaced = DB_A + "/my table"
        result = _run_and_parse(mod.ListIcebergTablesTask(DB_A), _raw_ls([DB_A + "/t1", spaced]))
        assert result["table_dirs"] == [spaced, DB_A + "/t1"]
        assert result["table_count"] == 2


class TestTableSizesTask:
    def test_dedups_and_du_s_each_table_in_given_order(self):
        task = mod.IcebergTableSizesTask([DB_A + "/t1", DB_B + "/t1", DB_A + "/t1/"])
        assert task.params() == {"table_dirs": [DB_A + "/t1", DB_B + "/t1"]}
        script = task.build_script()
        assert script.count("hdfs dfs -du -s") == 2
        output = "\n".join(
            [
                "===DU===" + DB_A + "/t1",
                "1 3 " + DB_A + "/t1",
                "===DU===" + DB_B + "/t1",
                "5 15 " + DB_B + "/t1",
                "===EXIT:0===",
            ]
        )
        result = task.parse(mod.parse_marked_output(output))
        assert [row["path"] for row in result["tables"]] == [DB_A + "/t1", DB_B + "/t1"]
        assert result["tables"][1]["disk_bytes"] == 15
        assert result["tables"][1]["db_dir"] == DB_B
        assert result["table_count"] == 2

    def test_over_max_tables_rejected(self):
        with pytest.raises(mod.DBMMcpBaseException):
            mod.IcebergTableSizesTask(["{}/t{}".format(DB_A, index) for index in range(mod.NAMED_TABLE_MAX + 1)])

    def test_empty_rejected(self):
        with pytest.raises(mod.DBMMcpBaseException):
            mod.IcebergTableSizesTask([])

    def test_missing_du_result_is_an_error(self):
        task = mod.IcebergTableSizesTask([DB_A + "/t1", DB_A + "/t2"])
        output = "===DU===" + DB_A + "/t1\n1 3 " + DB_A + "/t1\n===EXIT:0===\n"
        with pytest.raises(mod.DBMMcpBaseException):
            task.parse(mod.parse_marked_output(output))

    def test_one_failed_table_does_not_drop_others(self):
        paths = [DB_A + "/t1", DB_A + "/t2", DB_B + "/t1"]
        task = mod.IcebergTableSizesTask(paths)
        result = task.parse(mod.parse_marked_output(_run_du_script(task, fail_path=DB_A + "/t2")))
        assert [row["path"] for row in result["tables"]] == [DB_A + "/t1", DB_B + "/t1"]
        assert result["table_count"] == 2
        assert result["failed_count"] == 1
        assert result["failed_tables"][0]["path"] == DB_A + "/t2"
        assert "No such file or directory" in result["failed_tables"][0]["error"]

    def test_all_failed_tables_still_parse(self):
        task = mod.IcebergTableSizesTask([DB_A + "/t1", DB_B + "/t1"])
        result = task.parse(mod.parse_marked_output(_run_du_script(task, fail_path="*")))
        assert result["tables"] == []
        assert [row["path"] for row in result["failed_tables"]] == [DB_A + "/t1", DB_B + "/t1"]

    def test_du_error_output_is_capped(self):
        task = mod.IcebergTableSizesTask([DB_A + "/t1"])
        error_lines = mod.DU_ERROR_MAX_LINES + 3
        output = _run_du_script(task, fail_path="*", error_lines=error_lines)
        result = task.parse(mod.parse_marked_output(output))
        assert len(result["failed_tables"][0]["error"].splitlines()) == mod.DU_ERROR_MAX_LINES


class TestSubmitTask:
    def test_submits_job_and_records_task(self, monkeypatch):
        fake_cache, submitted = _prepare(monkeypatch)
        result = mod.submit_task(DOMAIN, mod.ListIcebergTablesTask(DB_A))
        assert result["job_instance_id"] == JOB_ID
        assert result["task_type"] == mod.ListIcebergTablesTask.task_type
        assert result["poll_interval_seconds"] == mod.TOOLBOX_POLL_INTERVAL_SECONDS
        assert len(submitted) == 1
        record = fake_cache.store[TASK_KEY]
        assert record["task_type"] == mod.ListIcebergTablesTask.task_type
        assert record["params"] == {"db_dir": DB_A}
        assert record["cluster_domain"] == DOMAIN
        assert fake_cache.timeouts[TASK_KEY] == mod.TOOLBOX_TASK_TTL_SECONDS

    def test_lock_is_kept_after_submit_with_job_timeout_ttl(self, monkeypatch):
        fake_cache, _submitted = _prepare(monkeypatch)
        mod.submit_task(DOMAIN, mod.ListIcebergDbsTask())
        assert LOCK_KEY in fake_cache.store
        assert fake_cache.timeouts[LOCK_KEY] == mod.TOOLBOX_LOCK_TTL_SECONDS == mod.JOB_TIMEOUT_SECONDS

    def test_second_task_on_same_cluster_is_rejected(self, monkeypatch):
        _fake_cache, submitted = _prepare(monkeypatch)
        mod.submit_task(DOMAIN, mod.ListIcebergDbsTask())
        with pytest.raises(mod.DBMMcpBaseException):
            mod.submit_task(DOMAIN, mod.ListIcebergTablesTask(DB_A))
        assert len(submitted) == 1

    def test_other_cluster_is_not_blocked(self, monkeypatch):
        fake_cache, submitted = _prepare(monkeypatch)
        mod.submit_task(DOMAIN, mod.ListIcebergDbsTask())
        other = dict(TARGET, cluster_id=13, cluster_name="hdfs-other")
        monkeypatch.setattr(mod, "_resolve_execution_target", lambda *args, **kwargs: dict(other))
        mod.submit_task("hdfs.other.db", mod.ListIcebergDbsTask())
        assert len(submitted) == 2

    def test_lock_is_released_when_submit_fails(self, monkeypatch):
        def failing_submit(target, script, task_name):
            raise RuntimeError("job api down")

        fake_cache, _submitted = _prepare(monkeypatch, submit=failing_submit)
        with pytest.raises(RuntimeError):
            mod.submit_task(DOMAIN, mod.ListIcebergDbsTask())
        assert LOCK_KEY not in fake_cache.store
        assert TASK_KEY not in fake_cache.store

    def test_release_does_not_delete_lock_owned_by_another_request(self, monkeypatch):
        fake_cache, _submitted = _prepare(monkeypatch)

        def failing_submit(target, script, task_name):
            fake_cache.store[LOCK_KEY] = "other-token"
            raise RuntimeError("job api down")

        monkeypatch.setattr(mod, "_submit_job", failing_submit)
        with pytest.raises(RuntimeError):
            mod.submit_task(DOMAIN, mod.ListIcebergDbsTask())
        assert fake_cache.store[LOCK_KEY] == "other-token"

    def test_cache_unavailable_refuses_to_submit(self, monkeypatch):
        _fake_cache, submitted = _prepare(monkeypatch)
        monkeypatch.setattr(mod, "cache", _BrokenCache())
        with pytest.raises(mod.DBMMcpBaseException):
            mod.submit_task(DOMAIN, mod.ListIcebergDbsTask())
        assert submitted == []

    def test_job_body_uses_job_timeout(self, monkeypatch):
        captured = {}

        def fake_fast_execute_script(body, use_admin):
            captured["body"] = body
            return {"job_instance_id": JOB_ID}

        monkeypatch.setattr(mod, "JobApi", SimpleNamespace(fast_execute_script=fake_fast_execute_script))
        assert mod._submit_job(TARGET, "echo", "task") == JOB_ID
        assert captured["body"]["timeout"] == mod.JOB_TIMEOUT_SECONDS
        assert captured["body"]["target_server"]["ip_list"] == [{"ip": "127.0.0.1", "bk_cloud_id": 0}]


class TestQueryTaskResult:
    def _submit(self, monkeypatch, task):
        fake_cache, _submitted = _prepare(monkeypatch)
        mod.submit_task(DOMAIN, task)
        return fake_cache

    def test_running_returns_immediately(self, monkeypatch):
        self._submit(monkeypatch, mod.ListIcebergDbsTask())
        _job_status(monkeypatch, finished=False)
        result = mod.query_task_result(DOMAIN, JOB_ID)
        assert result["status"] == mod.TASK_STATUS_RUNNING
        assert result["result"] is None

    def test_succeeded_is_parsed_by_task_type(self, monkeypatch):
        task = mod.ListIcebergTablesTask(DB_A)
        self._submit(monkeypatch, task)
        _job_status(monkeypatch, finished=True, log=_run_script(task.build_script(), _raw_ls([DB_A + "/t1"])))
        result = mod.query_task_result(DOMAIN, JOB_ID)
        assert result["status"] == mod.TASK_STATUS_SUCCEEDED
        assert result["task_type"] == mod.ListIcebergTablesTask.task_type
        assert result["result"]["table_dirs"] == [DB_A + "/t1"]

    def test_nonzero_exit_is_failed(self, monkeypatch):
        task = mod.ListIcebergTablesTask(DB_A)
        self._submit(monkeypatch, task)
        _job_status(monkeypatch, finished=True, log=_run_script(task.build_script(), "ls: No such file", rc=1))
        result = mod.query_task_result(DOMAIN, JOB_ID)
        assert result["status"] == mod.TASK_STATUS_FAILED
        assert "No such file" in result["message"]
        assert result["result"] is None

    def test_missing_exit_marker_is_failed(self, monkeypatch):
        self._submit(monkeypatch, mod.IcebergTableSizesTask([DB_A + "/t1"]))
        _job_status(monkeypatch, finished=True, log="===DU===" + DB_A + "/t1\n")
        result = mod.query_task_result(DOMAIN, JOB_ID)
        assert result["status"] == mod.TASK_STATUS_FAILED

    def test_unknown_job_is_rejected_without_calling_job_api(self, monkeypatch):
        _prepare(monkeypatch)
        called = []
        monkeypatch.setattr(mod, "get_job_exec_status", lambda job_instance_id: called.append(job_instance_id))
        with pytest.raises(mod.DBMMcpBaseException):
            mod.query_task_result(DOMAIN, JOB_ID)
        assert called == []

    def test_job_of_other_cluster_is_rejected(self, monkeypatch):
        self._submit(monkeypatch, mod.ListIcebergDbsTask())
        called = []
        monkeypatch.setattr(mod, "get_job_exec_status", lambda job_instance_id: called.append(job_instance_id))
        with pytest.raises(mod.DBMMcpBaseException):
            mod.query_task_result("hdfs.other.db", JOB_ID)
        assert called == []

    def test_cache_unavailable_is_an_error(self, monkeypatch):
        monkeypatch.setattr(mod, "cache", _BrokenCache())
        with pytest.raises(mod.DBMMcpBaseException):
            mod.query_task_result(DOMAIN, JOB_ID)

    def test_every_task_type_is_registered(self):
        assert set(mod.TOOLBOX_TASKS) == {
            mod.ListIcebergDbsTask.task_type,
            mod.ListIcebergTablesTask.task_type,
            mod.IcebergTableSizesTask.task_type,
        }


class TestScripts:
    def test_scripts_are_valid_shell(self):
        for script in (
            mod.ListIcebergDbsTask().build_script(),
            mod.ListIcebergTablesTask(DB_A).build_script(),
            mod.IcebergTableSizesTask([DB_A + "/t1", DB_B + "/t1"]).build_script(),
        ):
            subprocess.run(["bash", "-n"], input=script, text=True, check=True)

    def test_shell_quote_rejects_unvalidated_values(self):
        with pytest.raises(mod.DBMMcpBaseException):
            mod._shell_quote("/data/a b")

    def test_nonzero_exit_is_an_error(self):
        with pytest.raises(mod.DBMMcpBaseException):
            mod.parse_marked_output("ls: No such file\n===EXIT:1===\n")


class _FakeQuerySet:
    def __init__(self, rows):
        self.rows = rows
        self.filters = {}

    def filter(self, **kwargs):
        self.filters.update(kwargs)
        return self

    def select_related(self, *args):
        return self

    def first(self):
        return self.rows[0] if self.rows else None


def _fake_cluster(ips):
    rows = [SimpleNamespace(machine=SimpleNamespace(ip=ip)) for ip in ips]
    queryset = _FakeQuerySet(rows)
    cluster = SimpleNamespace(
        id=12, name="hdfs-test", bk_cloud_id=0, storageinstance_set=SimpleNamespace(filter=queryset.filter)
    )
    return cluster, queryset


class TestResolveExecutionTarget:
    def test_only_running_datanode_is_selected(self, monkeypatch):
        cluster, queryset = _fake_cluster(["127.0.0.1", "127.0.0.2"])
        monkeypatch.setattr(mod, "validate_hdfs_cluster", lambda domain: cluster)
        target = mod._resolve_execution_target(DOMAIN)
        assert queryset.filters == {
            "instance_role": mod.InstanceRole.HDFS_DATA_NODE.value,
            "status": mod.InstanceStatus.RUNNING.value,
        }
        assert target["datanode_ip"] == "127.0.0.1"

    def test_no_running_datanode_is_an_error(self, monkeypatch):
        cluster, _queryset = _fake_cluster([])
        monkeypatch.setattr(mod, "validate_hdfs_cluster", lambda domain: cluster)
        with pytest.raises(mod.DBMMcpBaseException):
            mod._resolve_execution_target(DOMAIN)
