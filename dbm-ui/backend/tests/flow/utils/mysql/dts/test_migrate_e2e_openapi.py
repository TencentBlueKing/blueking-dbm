# -*- coding: utf-8 -*-
"""DTS 迁移 L2 端到端验收：直连 Master OpenAPI + 真实 MySQL 源/目标。

门控：仅当环境变量 DTS_IT_ENABLED=1 时执行；否则整模块 skip。

必需环境变量：
  DTS_MASTER_ADDR   例 127.0.0.1:18301
  DTS_SRC_DSN       例 127.0.0.1:3306
  DTS_DST_DSN       例 127.0.0.1:3307
  DTS_MYSQL_USER / DTS_MYSQL_PASSWORD
可选：
  DTS_UT_REPORT_DIR
  DTS_IT_WAIT_SECONDS  默认 180
"""
from __future__ import annotations

import json
import os
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable

import pymysql

from backend.components.mysqldtsapi.types import (
    CreateSourceRequest,
    Source,
    SourceConfig,
    SourceConfItem,
    TargetConfig,
    Task,
)
from backend.flow.utils.mysql.dts.constants import DtsLifecycleMode, MigrateTopology, MigrateType
from backend.flow.utils.mysql.dts.migrate_helper import _build_table_migrate_rules, build_dts_task_request
from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan, DtsTaskConfig, DtsTaskSpec, SourceSpec, SyncScope
from backend.tests.flow.utils.mysql.dts.migrate_ut_report import MigrateUtReport, ScenarioResult

DTS_IT_ENABLED = os.environ.get("DTS_IT_ENABLED", "") == "1"
MASTER_ADDR = os.environ.get("DTS_MASTER_ADDR", "")
SRC_DSN = os.environ.get("DTS_SRC_DSN", "")
DST_DSN = os.environ.get("DTS_DST_DSN", "")
MYSQL_USER = os.environ.get("DTS_MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("DTS_MYSQL_PASSWORD", "make")
WAIT_SECONDS = int(os.environ.get("DTS_IT_WAIT_SECONDS", "180"))


def _parse_dsn(dsn: str) -> tuple[str, int]:
    host, port = dsn.rsplit(":", 1)
    return host, int(port)


def _log(scenario_id: str, stage: str, msg: str) -> None:
    print(f"[DTS-UT][{scenario_id}] {stage} {msg}")


def _strip_empty_str(value: Any) -> Any:
    """递归去掉空字符串，避免 OpenAPI 将 disk_quota='' 等解析为 invalid size。"""
    if isinstance(value, dict):
        return {k: _strip_empty_str(v) for k, v in value.items() if v != ""}
    if isinstance(value, list):
        return [_strip_empty_str(v) for v in value]
    return value


class DirectDtsOpenApi:
    """直连 DTS Master OpenAPI（不经 DRS）。"""

    def __init__(self, master_addr: str, timeout: int = 30):
        addr = master_addr.strip()
        if addr.startswith("http://") or addr.startswith("https://"):
            self.base = addr.rstrip("/")
        else:
            self.base = f"http://{addr}"

        self.timeout = timeout

    def call(self, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
        url = f"{self.base}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                payload = json.loads(raw) if raw else {}
                return resp.status, payload
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {"error": raw}
            except json.JSONDecodeError:
                payload = {"error": raw}
            return exc.code, payload


@dataclass
class ScenarioDef:
    scenario_id: str
    title: str
    sync_scope: SyncScope
    seed: Callable[[pymysql.connections.Connection], str]
    expect: Callable[[pymysql.connections.Connection], str]
    record_only: bool = False  # S7：只记录引擎行为，不强制 PASS


def _conn(dsn: str):
    host, port = _parse_dsn(dsn)
    return pymysql.connect(
        host=host,
        port=port,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=10,
    )


def _exec(conn, sql: str, args=None):
    with conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def _drop_db(conn, db: str):
    _exec(conn, f"DROP DATABASE IF EXISTS `{db}`")


def _create_db_table(conn, db: str, table: str, rows: list[tuple[int, str]]):
    _exec(conn, f"CREATE DATABASE IF NOT EXISTS `{db}`")
    _exec(conn, f"DROP TABLE IF EXISTS `{db}`.`{table}`")
    _exec(
        conn,
        f"CREATE TABLE `{db}`.`{table}` (id INT PRIMARY KEY, name VARCHAR(64)) ENGINE=InnoDB",
    )
    for row in rows:
        _exec(conn, f"INSERT INTO `{db}`.`{table}` (id, name) VALUES (%s, %s)", row)


def _table_exists(conn, db: str, table: str) -> bool:
    rows = _exec(
        conn,
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
        (db, table),
    )
    return bool(rows and rows[0][0])


def _db_exists(conn, db: str) -> bool:
    rows = _exec(conn, "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name=%s", (db,))
    return bool(rows and rows[0][0])


def _count(conn, db: str, table: str) -> int:
    if not _table_exists(conn, db, table):
        return -1
    rows = _exec(conn, f"SELECT COUNT(*) FROM `{db}`.`{table}`")
    return int(rows[0][0])


def _show_tables(conn, db: str) -> list[str]:
    if not _db_exists(conn, db):
        return []
    rows = _exec(conn, f"SHOW TABLES FROM `{db}`")
    return [r[0] for r in rows]


def _seed_s1(conn) -> str:
    for db in ("dts_ut_db_a", "dts_ut_db_b"):
        _drop_db(conn, db)
        _create_db_table(conn, db, "t1", [(1, f"{db}-r1"), (2, f"{db}-r2")])
    return "dbs=dts_ut_db_a,dts_ut_db_b tables=t1 rows=2 each"


def _expect_s1(conn) -> str:
    ok_a = _count(conn, "dts_ut_db_a", "t1") == 2
    no_b = not _db_exists(conn, "dts_ut_db_b")
    detail = f"dst a.t1={_count(conn,'dts_ut_db_a','t1')} b_exists={_db_exists(conn,'dts_ut_db_b')}"
    if not (ok_a and no_b):
        raise AssertionError(detail)
    return detail


def _seed_s2(conn) -> str:
    _drop_db(conn, "dts_ut_db_c")
    _create_db_table(conn, "dts_ut_db_c", "t1", [(1, "t1")])
    _create_db_table(conn, "dts_ut_db_c", "t2", [(1, "t2"), (2, "t2")])
    return "db=dts_ut_db_c t1=1row t2=2rows"


def _expect_s2(conn) -> str:
    ok = _count(conn, "dts_ut_db_c", "t1") == 1 and not _table_exists(conn, "dts_ut_db_c", "t2")
    detail = f"t1={_count(conn,'dts_ut_db_c','t1')} t2_exists={_table_exists(conn,'dts_ut_db_c','t2')}"
    if not ok:
        raise AssertionError(detail)
    return detail


def _seed_s3(conn) -> str:
    _drop_db(conn, "dts_ut_db_full")
    _create_db_table(conn, "dts_ut_db_full", "t1", [(1, "a"), (2, "b"), (3, "c")])
    _create_db_table(conn, "dts_ut_db_full", "t2", [(10, "x")])
    return "db=dts_ut_db_full t1=3 t2=1"


def _expect_s3(conn) -> str:
    ok = _count(conn, "dts_ut_db_full", "t1") == 3 and _count(conn, "dts_ut_db_full", "t2") == 1
    detail = f"t1={_count(conn,'dts_ut_db_full','t1')} t2={_count(conn,'dts_ut_db_full','t2')}"
    if not ok:
        raise AssertionError(detail)
    return detail


def _seed_s4(conn) -> str:
    _drop_db(conn, "dts_ut_db_r")
    _create_db_table(conn, "dts_ut_db_r", "t_old", [(1, "old")])
    return "db=dts_ut_db_r t_old=1"


def _expect_s4(conn) -> str:
    ok = _table_exists(conn, "dts_ut_db_r", "t_new") and not _table_exists(conn, "dts_ut_db_r", "t_old")
    ok = ok and _count(conn, "dts_ut_db_r", "t_new") == 1
    detail = (
        f"t_new_exists={_table_exists(conn,'dts_ut_db_r','t_new')} "
        f"t_old_exists={_table_exists(conn,'dts_ut_db_r','t_old')} "
        f"t_new_rows={_count(conn,'dts_ut_db_r','t_new')}"
    )
    if not ok:
        raise AssertionError(detail)
    return detail


def _seed_s5(conn) -> str:
    _drop_db(conn, "dts_ut_src")
    _create_db_table(conn, "dts_ut_src", "t1", [(1, "s5")])
    return "db=dts_ut_src t1=1"


def _expect_s5(conn) -> str:
    # rename 库：数据应落在 target_db；源库名是否在目标残留取决于引擎实现，只作记录
    ok = _db_exists(conn, "dts_ut_dst") and _count(conn, "dts_ut_dst", "t1") == 1
    detail = (
        f"dst_exists={_db_exists(conn,'dts_ut_dst')} dst.t1={_count(conn,'dts_ut_dst','t1')} "
        f"src_name_on_dst={_db_exists(conn,'dts_ut_src')}"
    )
    if not ok:
        raise AssertionError(detail)
    return detail


def _seed_s6(conn) -> str:
    for db in ("dts_ut_db_a", "dts_ut_db_b"):
        _drop_db(conn, db)
        _create_db_table(conn, db, "t1", [(1, db)])
    return "do=a,b ignore=b"


def _expect_s6(conn) -> str:
    ok = _count(conn, "dts_ut_db_a", "t1") == 1 and not _db_exists(conn, "dts_ut_db_b")
    detail = f"a.t1={_count(conn,'dts_ut_db_a','t1')} b_exists={_db_exists(conn,'dts_ut_db_b')}"
    if not ok:
        raise AssertionError(detail)
    return detail


def _seed_s7(conn) -> str:
    _drop_db(conn, "dts_ut_empty_scope")
    _create_db_table(conn, "dts_ut_empty_scope", "t1", [(1, "s7")])
    return "db=dts_ut_empty_scope t1=1 (empty sync_scope)"


def _expect_s7(conn) -> str:
    # 空 scope → rules=[]：记录目标是否被迁移，不做硬断言失败
    detail = (
        f"dst_db_exists={_db_exists(conn,'dts_ut_empty_scope')} " f"tables={_show_tables(conn,'dts_ut_empty_scope')}"
    )
    return detail


SCENARIOS: list[ScenarioDef] = [
    ScenarioDef(
        "S1",
        "部分库",
        SyncScope(do_dbs=["dts_ut_db_a"]),
        _seed_s1,
        _expect_s1,
    ),
    ScenarioDef(
        "S2",
        "部分表",
        SyncScope(do_tables=[{"db": "dts_ut_db_c", "table": "t1"}]),
        _seed_s2,
        _expect_s2,
    ),
    ScenarioDef(
        "S3",
        "全库表通配",
        SyncScope(table_routes=[{"source_db": "dts_ut_db_full", "source_table": "*"}]),
        _seed_s3,
        _expect_s3,
    ),
    ScenarioDef(
        "S4",
        "rename 表",
        SyncScope(
            table_routes=[
                {
                    "source_db": "dts_ut_db_r",
                    "source_table": "t_old",
                    "target_db": "dts_ut_db_r",
                    "target_table": "t_new",
                }
            ]
        ),
        _seed_s4,
        _expect_s4,
    ),
    ScenarioDef(
        "S5",
        "rename 库",
        SyncScope(
            table_routes=[
                {
                    "source_db": "dts_ut_src",
                    "source_table": "t1",
                    "target_db": "dts_ut_dst",
                    "target_table": "t1",
                }
            ]
        ),
        _seed_s5,
        _expect_s5,
    ),
    ScenarioDef(
        "S6",
        "ignore 白名单减法",
        SyncScope(do_dbs=["dts_ut_db_a", "dts_ut_db_b"], ignore_dbs=["dts_ut_db_b"]),
        _seed_s6,
        _expect_s6,
    ),
    ScenarioDef(
        "S7",
        "空 scope",
        SyncScope(),
        _seed_s7,
        _expect_s7,
        record_only=True,
    ),
]


@unittest.skipUnless(DTS_IT_ENABLED, "set DTS_IT_ENABLED=1 to run DTS OpenAPI e2e")
class DtsMigrateE2EOpenApiTest(unittest.TestCase):
    report: MigrateUtReport
    api: DirectDtsOpenApi
    src_host: str
    src_port: int
    dst_host: str
    dst_port: int

    @classmethod
    def setUpClass(cls):
        if not MASTER_ADDR:
            raise unittest.SkipTest("DTS_MASTER_ADDR is required when DTS_IT_ENABLED=1")
        if not SRC_DSN:
            raise unittest.SkipTest("DTS_SRC_DSN is required when DTS_IT_ENABLED=1")
        if not DST_DSN:
            raise unittest.SkipTest("DTS_DST_DSN is required when DTS_IT_ENABLED=1")
        cls.src_host, cls.src_port = _parse_dsn(SRC_DSN)
        cls.dst_host, cls.dst_port = _parse_dsn(DST_DSN)
        cls.api = DirectDtsOpenApi(MASTER_ADDR)
        status, info = cls.api.call("GET", "/api/v1/cluster/info")
        if status >= 400:
            raise unittest.SkipTest(f"DTS Master OpenAPI unavailable: HTTP {status} {info}")
        cls.report = MigrateUtReport(
            env_info={
                "源": SRC_DSN,
                "目标": DST_DSN,
                "Master": MASTER_ADDR,
                "cluster_info": json.dumps(info, ensure_ascii=False)[:500],
            }
        )
        print(f"[DTS-UT] START e2e master={MASTER_ADDR} src={SRC_DSN} dst={DST_DSN}")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "report", None):
            md_path, json_path = cls.report.write()
            print("[DTS-UT] OVERVIEW\n" + cls.report.overview_table())
            print(f"[DTS-UT] REPORT_PATH {md_path}")
            print(f"[DTS-UT] REPORT_JSON {json_path}")

    def _rules_payload(self, source_name: str, scope: SyncScope) -> list[dict]:
        rules = _build_table_migrate_rules(source_name, scope)
        return [
            {
                "source": r.source.model_dump(),
                "target": r.target.model_dump() if r.target else None,
            }
            for r in rules
        ]

    def _cleanup_dst_dbs(self, dbs: list[str]):
        with _conn(DST_DSN) as conn:
            for db in dbs:
                _drop_db(conn, db)

    def _wait_task(self, scenario_id: str, task_name: str) -> tuple[bool, str]:
        deadline = time.time() + WAIT_SECONDS
        last = ""
        while time.time() < deadline:
            code, payload = self.api.call("GET", f"/api/v1/tasks/{urllib.parse.quote(task_name)}/status")
            items = payload.get("data") or payload.get("status_list") or []
            if isinstance(payload, dict) and "data" not in payload and isinstance(payload.get("total"), int):
                items = payload.get("data") or []
            stages = []
            errors = []
            synced = False
            finished = False
            for item in items if isinstance(items, list) else []:
                stage = item.get("stage", "")
                unit = item.get("unit", "")
                stages.append(f"{stage}/{unit}")
                if item.get("error_msg"):
                    errors.append(item["error_msg"])
                sync = item.get("sync_status") or {}
                if sync.get("synced"):
                    synced = True
                if stage in ("Finished", "Paused", "Stopped") and unit in ("", "Sync", "Load"):
                    # full 模式结束后常见 Finished
                    if stage == "Finished":
                        finished = True
                if stage == "Running" and unit == "Sync":
                    # full 完成后进入增量同步也算数据已落目标
                    dump = item.get("dump_status") or {}
                    load = item.get("load_status") or {}
                    if dump or load or synced:
                        finished = True
            last = f"http={code} stages={stages} synced={synced} err={errors[:1]}"
            _log(scenario_id, "WAIT", last)
            if errors:
                return False, last
            if finished or synced:
                return True, last
            # task_mode=full：Finished
            if any(s.startswith("Finished") for s in stages):
                return True, last
            time.sleep(3)
        return False, f"timeout after {WAIT_SECONDS}s; last={last}"

    def _run_scenario(self, scenario: ScenarioDef):
        sid = scenario.scenario_id
        source_name = f"ut-src-{sid.lower()}-{int(time.time()) % 100000}"
        task_name = f"ut-task-{sid.lower()}-{int(time.time()) % 100000}"
        scope_dict = asdict(scenario.sync_scope)
        result = ScenarioResult(
            scenario_id=sid,
            title=scenario.title,
            sync_scope=scope_dict,
        )
        api_logs: list[str] = []
        created_source = False
        created_task = False

        _log(sid, "START", f"{scenario.title} sync_scope={json.dumps(scope_dict, ensure_ascii=False)}")
        rules = _build_table_migrate_rules(source_name, scenario.sync_scope)
        result.rules = self._rules_payload(source_name, scenario.sync_scope)
        result.l1_ok = True
        _log(sid, "RULES", json.dumps(result.rules, ensure_ascii=False))

        # 目标侧清理涉及库
        related_dbs = {
            "dts_ut_db_a",
            "dts_ut_db_b",
            "dts_ut_db_c",
            "dts_ut_db_full",
            "dts_ut_db_r",
            "dts_ut_src",
            "dts_ut_dst",
            "dts_ut_empty_scope",
            "dm_meta",
        }
        self._cleanup_dst_dbs(sorted(related_dbs))

        try:
            with _conn(SRC_DSN) as src:
                result.seed_summary = scenario.seed(src)
            _log(sid, "SEED", result.seed_summary)

            # S7：空 rules 在引擎侧会全库迁移；生产路径由 build_dts_task_request 拦截，此处只记录策略
            if scenario.record_only and not rules:
                blocked = False
                block_msg = ""
                try:
                    plan = DtsMigratePlan(
                        topology=MigrateTopology.ONE_TO_ONE.value,
                        migrate_type=MigrateType.MYSQL_TO_MYSQL.value,
                        dts_cluster_id=None,
                        dts_lifecycle=DtsLifecycleMode.USE_EXISTING.value,
                        auto_deploy_dts=False,
                        deploy_subflow_inp=None,
                        cleanup_after_migrate=False,
                        recycle_dts_hosts=False,
                        dts_task_config=DtsTaskConfig(),
                        task_specs=[],
                        worker_count_required=1,
                    )
                    task_spec = DtsTaskSpec(
                        task_name=task_name,
                        target_cluster_id=0,
                        sources=[
                            SourceSpec(
                                cluster_id=0,
                                source_name=source_name,
                                sync_scope=scenario.sync_scope,
                            )
                        ],
                        target_config=TargetConfig(
                            host=self.dst_host,
                            port=self.dst_port,
                            user=MYSQL_USER,
                            password=MYSQL_PASSWORD,
                            cluster_type="mysql",
                        ),
                    )
                    build_dts_task_request(plan, task_spec, user=MYSQL_USER, password=MYSQL_PASSWORD)
                except ValueError as exc:
                    blocked = True
                    block_msg = str(exc)
                result.check_summary = (
                    "空 table_migrate_rule 不调用 start；" f"helper 拦截={blocked}; msg={block_msg}; " "此前实测：引擎空 rules 会全库迁移"
                )
                result.result = "PASS" if blocked else "FAIL"
                result.l2_ok = None
                result.detail = result.check_summary
                _log(sid, "CHECK", result.check_summary)
                _log(sid, "RESULT", f"{result.result} {result.detail}")
                api_logs.append(f"helper_block_empty_rules={blocked}")
                return

            # create source
            # 验收环境源库可能未开 GTID；与引擎校验对齐，默认关闭（DTS_ENABLE_GTID=1 可强制开启）
            enable_gtid = os.environ.get("DTS_ENABLE_GTID", "0") == "1"
            src_req = CreateSourceRequest(
                source=Source(
                    source_name=source_name,
                    host=self.src_host,
                    port=self.src_port,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    enable_gtid=enable_gtid,
                    enable=True,
                    cluster_type="mysql",
                )
            )
            body = src_req.model_dump(exclude_none=True, by_alias=True)
            code, payload = self.api.call("POST", "/api/v1/sources", body)
            api_logs.append(f"create_source HTTP {code} body_keys={list(payload)[:8]}")
            _log(sid, "API", f"POST /api/v1/sources -> {code} {json.dumps(payload, ensure_ascii=False)[:400]}")
            if code >= 400:
                raise AssertionError(f"create_source failed: {code} {payload}")
            created_source = True

            task = Task(
                name=task_name,
                task_mode="full",
                on_duplicate="replace",
                meta_schema="dm_meta",
                target_config=TargetConfig(
                    host=self.dst_host,
                    port=self.dst_port,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    cluster_type="mysql",
                ),
                source_config=SourceConfig(
                    source_conf=[SourceConfItem(source_name=source_name)],
                ),
                table_migrate_rule=rules,
            )
            # dump like client: drop empty shard_mode；去掉空字符串以免 OpenAPI 解析 size 失败
            task_body = task.model_dump(exclude_none=True, by_alias=True)
            if not task_body.get("shard_mode"):
                task_body.pop("shard_mode", None)
            task_body = _strip_empty_str(task_body)
            code, payload = self.api.call("POST", "/api/v1/tasks", {"task": task_body})
            api_logs.append(f"create_task HTTP {code}")
            _log(sid, "API", f"POST /api/v1/tasks -> {code} {json.dumps(payload, ensure_ascii=False)[:500]}")
            if code >= 400:
                raise AssertionError(f"create_task failed: {code} {payload}")
            created_task = True

            code, payload = self.api.call("POST", f"/api/v1/tasks/{urllib.parse.quote(task_name)}/start", {})
            api_logs.append(f"start_task HTTP {code}")
            _log(sid, "API", f"POST /api/v1/tasks/.../start -> {code} {json.dumps(payload, ensure_ascii=False)[:300]}")
            if code >= 400:
                raise AssertionError(f"start_task failed: {code} {payload}")

            ok_wait, wait_detail = self._wait_task(sid, task_name)
            api_logs.append(f"wait {wait_detail}")
            if not ok_wait and not scenario.record_only:
                raise AssertionError(f"wait failed: {wait_detail}")

            with _conn(DST_DSN) as dst:
                check = scenario.expect(dst)
            result.check_summary = check
            _log(sid, "CHECK", check)

            if scenario.record_only:
                result.result = "PASS" if result.l1_ok else "FAIL"
                result.l2_ok = None
                result.detail = f"空 scope 引擎行为已记录; wait={wait_detail}; {check}"
            else:
                result.result = "PASS"
                result.l2_ok = True
                result.detail = "目标校验通过"
            _log(sid, "RESULT", f"{result.result} {result.detail}")
        except Exception as exc:  # pylint: disable=broad-except
            result.result = "FAIL"
            result.l2_ok = False if not scenario.record_only else None
            result.detail = str(exc)[:500]
            _log(sid, "RESULT", f"FAIL {result.detail}")
            try:
                with _conn(SRC_DSN) as src:
                    _log(sid, "RESULT", f"src_show_tables dts_ut_db_a={_show_tables(src, 'dts_ut_db_a')}")
                with _conn(DST_DSN) as dst:
                    _log(sid, "RESULT", f"dst_show_tables sample={_show_tables(dst, 'dts_ut_db_a')}")
            except Exception:  # pylint: disable=broad-except
                pass
        finally:
            try:
                if created_task:
                    code, _payload = self.api.call(
                        "DELETE",
                        f"/api/v1/tasks/{urllib.parse.quote(task_name)}?force=true",
                        {"force": True},
                    )
                    _log(sid, "CLEAN", f"delete_task {code}")
                    api_logs.append(f"delete_task HTTP {code}")
                if created_source:
                    code, _payload = self.api.call(
                        "DELETE",
                        f"/api/v1/sources/{urllib.parse.quote(source_name)}",
                    )
                    _log(sid, "CLEAN", f"delete_source {code}")
                    api_logs.append(f"delete_source HTTP {code}")
                self._cleanup_dst_dbs(sorted(related_dbs))
                with _conn(SRC_DSN) as src:
                    for db in sorted(related_dbs):
                        if db != "dm_meta":
                            _drop_db(src, db)
                _log(sid, "CLEAN", "dropped ut databases on src/dst")
            except Exception as clean_exc:  # pylint: disable=broad-except
                _log(sid, "CLEAN", f"cleanup error: {clean_exc}")
            result.api_logs = api_logs
            if result not in self.report.scenarios:
                self.report.add(result)

        if result.result == "FAIL" and not scenario.record_only:
            self.fail(result.detail)

    def test_s1_partial_db(self):
        self._run_scenario(SCENARIOS[0])

    def test_s2_partial_table(self):
        self._run_scenario(SCENARIOS[1])

    def test_s3_full_wildcard(self):
        self._run_scenario(SCENARIOS[2])

    def test_s4_rename_table(self):
        self._run_scenario(SCENARIOS[3])

    def test_s5_rename_db(self):
        self._run_scenario(SCENARIOS[4])

    def test_s6_ignore(self):
        self._run_scenario(SCENARIOS[5])

    def test_s7_empty_scope(self):
        self._run_scenario(SCENARIOS[6])
