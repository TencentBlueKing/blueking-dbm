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
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.components.sql_import.client import SQLSimulationApi
from backend.db_meta.models import Cluster
from backend.flow.consts import SYSTEM_DBS
from backend.flow.engine.bamboo.scene.mysql.common.dbconsole_util import get_dbconsole_read_instance
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator

logger = logging.getLogger("root")

# mysqldump --where 只需条件表达式；若用户再带 WHERE 关键字，下层会拼成 WHERE WHERE 报错
_WHERE_PREFIX_RE = re.compile(r"^\s*where\s+", re.IGNORECASE)


class DbConsoleDumpFlowValidator(MysqlBaseValidator):
    """
    DbConsoleDumpSqlFlow 对应的 validate：
    仅在 where 非空时，先做一次 inject 检查，再对导出目标表全量并发 EXPLAIN。
    """

    EXPLAIN_BATCH_SIZE = 20
    MAX_WORKERS = 5
    # 注入预检只是一次轻量语法判断，服务不可用时应快速失败放行，
    # 避免命中 DataAPI 默认的 30s 超时 + 3 次递归重试（最长约 180s）拖慢整个 where 校验。
    INJECT_CHECK_TIMEOUT = 5
    INJECT_CHECK_RETRY_TIMES = 1

    def __call__(self):
        where = self.data.get("where")
        if where is None or not str(where).strip():
            return None

        where = str(where).strip()
        precheck_err = self._precheck_where(where)
        if precheck_err:
            return [precheck_err]

        cluster_id = self.data.get("cluster_id")
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            address, bk_cloud_id = self._get_read_address(cluster)
        except Cluster.DoesNotExist:
            return [self._build_where_error(_("集群 {} 不存在").format(cluster_id))]
        except Exception as exc:  # noqa: BLE001
            return [self._build_where_error(_("集群 {} 无法获取只读实例进行 where 校验: {}").format(cluster_id, str(exc)))]

        targets, resolve_errors = self._resolve_targets(address, bk_cloud_id)
        if resolve_errors:
            return resolve_errors
        if not targets:
            return [self._build_where_error(_("未解析到可校验的导出表"))]

        inject_err = self._check_where_inject(where, targets[0])
        if inject_err:
            return [inject_err]

        error_msgs = self._explain_all(address, bk_cloud_id, where, targets)
        return error_msgs or None

    def _precheck_where(self, where: str) -> Optional[dict]:
        """拼进 EXPLAIN / mysqldump --where 前的轻量防护。"""
        if _WHERE_PREFIX_RE.match(where):
            return self._build_where_error(_("where 条件不能包含 WHERE 关键字，请直接填写条件表达式，例如: id > 1"))
        if ";" in where or "\x00" in where or "\n" in where or "\r" in where:
            return self._build_where_error(_("where 条件不允许包含分号或非法字符"))
        return None

    def _check_where_inject(self, where: str, target: Tuple[str, str]) -> Optional[dict]:
        """用第一张导出表拼一条 SQL，调用一次 inject 检查；服务不可用则失败放行。"""
        db, table = target
        sql = "SELECT * FROM {}.{} WHERE ({})".format(self._quote_ident(db), self._quote_ident(table), where)
        try:
            result = SQLSimulationApi.syntax_check_inject(
                params={"sql": sql, "judge_subquery_diff_table": True},
                timeout=self.INJECT_CHECK_TIMEOUT,
                retry_times=self.INJECT_CHECK_RETRY_TIMES,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(_("where 注入检查服务不可用，失败放行: {}").format(str(exc)))
            return None

        if isinstance(result, dict) and result.get("is_inject"):
            reason = result.get("reason") or _("未知注入风险")
            return self._build_where_error(_("where 条件存在注入风险: {}").format(reason))
        return None

    def _get_read_address(self, cluster: Cluster) -> Tuple[str, int]:
        """与 dump flow 共用 get_dbconsole_read_instance 选点。"""
        backend_info = get_dbconsole_read_instance(cluster)
        return backend_info.ip_port, cluster.bk_cloud_id

    def _resolve_targets(self, address: str, bk_cloud_id: int) -> Tuple[List[Tuple[str, str]], List[dict]]:
        """解析待校验的 (db, table) 列表。默认忽略系统库。"""
        raw_databases = self.data.get("databases") or []
        if not raw_databases:
            return [], [self._build_where_error(_("导出库列表不能为空"))]

        # 与 dbconsole dump 一致：忽略系统库，不对系统库表做 where EXPLAIN
        databases = [db for db in raw_databases if db not in SYSTEM_DBS]
        if not databases:
            return [], [self._build_where_error(_("过滤系统库后无可校验的导出库"))]

        tables = self.data.get("tables") or []
        tables_ignore = set(self.data.get("tables_ignore") or [])
        errors: List[dict] = []

        need_resolve_all = (not tables) or (tables == ["*"]) or (len(tables) == 1 and tables[0] == "*")
        if need_resolve_all:
            return self._resolve_all_base_tables(address, bk_cloud_id, databases, tables_ignore)

        targets: List[Tuple[str, str]] = []
        for db in databases:
            for table in tables:
                if table in tables_ignore or f"{db}.{table}" in tables_ignore:
                    continue
                targets.append((db, table))
        return targets, errors

    def _resolve_all_base_tables(
        self, address: str, bk_cloud_id: int, databases: List[str], tables_ignore: set
    ) -> Tuple[List[Tuple[str, str]], List[dict]]:
        """tables 为 * 时，从 information_schema 拉取 BASE TABLE（系统库已在上游过滤）。"""
        targets: List[Tuple[str, str]] = []
        errors: List[dict] = []
        for db in databases:
            sql = (
                "SELECT TABLE_NAME FROM information_schema.tables "
                "WHERE TABLE_SCHEMA = {} AND TABLE_TYPE = 'BASE TABLE'"
            ).format(self._quote_literal(db))
            try:
                res = DRSApi.rpc(
                    {
                        "addresses": [address],
                        "cmds": [sql],
                        "force": False,
                        "bk_cloud_id": bk_cloud_id,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(self._build_where_error(_("库 {} 解析导出表失败: {}").format(db, str(exc))))
                continue

            if not res or res[0].get("error_msg"):
                err = res[0].get("error_msg") if res else _("空响应")
                errors.append(self._build_where_error(_("库 {} 解析导出表失败: {}").format(db, err)))
                continue

            cmd_results = res[0].get("cmd_results") or []
            if not cmd_results or cmd_results[0].get("error_msg"):
                err = cmd_results[0].get("error_msg") if cmd_results else _("空结果")
                errors.append(self._build_where_error(_("库 {} 解析导出表失败: {}").format(db, err)))
                continue

            for row in cmd_results[0].get("table_data") or []:
                table = row.get("TABLE_NAME") or row.get("table_name")
                if not table:
                    continue
                if table in tables_ignore or f"{db}.{table}" in tables_ignore:
                    continue
                targets.append((db, table))
        return targets, errors

    def _explain_all(self, address: str, bk_cloud_id: int, where: str, targets: List[Tuple[str, str]]) -> List[dict]:
        """分批并发 EXPLAIN，汇总全部失败表。"""
        batches = [targets[i : i + self.EXPLAIN_BATCH_SIZE] for i in range(0, len(targets), self.EXPLAIN_BATCH_SIZE)]
        error_msgs: List[dict] = []
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = [executor.submit(self._explain_batch, address, bk_cloud_id, where, batch) for batch in batches]
            for future in as_completed(futures):
                try:
                    error_msgs.extend(future.result())
                except Exception as exc:  # noqa: BLE001
                    error_msgs.append(self._build_where_error(_("where 条件校验异常: {}").format(str(exc))))
        return error_msgs

    def _explain_batch(self, address: str, bk_cloud_id: int, where: str, batch: List[Tuple[str, str]]) -> List[dict]:
        """单批 DRS EXPLAIN。"""
        cmds = [
            "EXPLAIN SELECT * FROM {}.{} WHERE {}".format(self._quote_ident(db), self._quote_ident(table), where)
            for db, table in batch
        ]
        try:
            res = DRSApi.rpc(
                {
                    "addresses": [address],
                    "cmds": cmds,
                    "force": True,
                    "bk_cloud_id": bk_cloud_id,
                }
            )
        except Exception as exc:  # noqa: BLE001
            return [self._build_where_error(_("where 条件校验失败: {}").format(str(exc)))]

        if not res:
            return [self._build_where_error(_("where 条件校验失败: {}").format(_("DRS 空响应")))]

        address_res = res[0]
        if address_res.get("error_msg"):
            return [self._build_where_error(_("where 条件校验失败: {}").format(address_res["error_msg"]))]

        return self._collect_batch_errors(batch, address_res.get("cmd_results") or [])

    def _collect_batch_errors(self, batch: List[Tuple[str, str]], cmd_results: List[dict]) -> List[dict]:
        """将批次内每条 EXPLAIN 的失败映射为可定位对象的错误。"""
        errors: List[dict] = []
        for index, (db, table) in enumerate(batch):
            if index >= len(cmd_results):
                errors.append(
                    self._build_where_error(_("表 {}.{} 的 where 条件不合法: {}").format(db, table, _("无 EXPLAIN 结果")))
                )
                continue
            cmd_err = cmd_results[index].get("error_msg")
            if cmd_err:
                errors.append(self._build_where_error(_("表 {}.{} 的 where 条件不合法: {}").format(db, table, cmd_err)))
        return errors

    @staticmethod
    def _quote_ident(name: str) -> str:
        return "`{}`".format(name.replace("`", "``"))

    @staticmethod
    def _quote_literal(value: str) -> str:
        return "'{}'".format(value.replace("\\", "\\\\").replace("'", "''"))

    @staticmethod
    def _build_where_error(message: str) -> Dict:
        return {"field": "where", "index": 0, "row_key": "", "errors": message}
