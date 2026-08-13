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
from types import SimpleNamespace

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi, MySQLDTSApi
from backend.components.mysqldtsapi.types import PurgeRelayRequest
from backend.db_meta.models import MysqlDtsCluster
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.constants import FullLoadEngine, get_full_migrate_data_dir
from backend.flow.utils.mysql.dts.migrate_helper import (
    resolve_dts_cluster_id,
    resolve_purge_relay_binlog_name,
    task_mode_runs_incremental,
)
from backend.flow.utils.mysql.dts.script_template import render_clean_ticket_dump_script
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

logger = logging.getLogger("flow")


class MysqlDtsDeleteTaskSourceService(BaseService):
    """按本单显式名称列表删除 DTS task 与 source（串行：先 task 后 source）。

    成功路径可在两次 API 之间插入：增量则 purge_relay，builtin 则 rm 本单 dump 目录。

    与 DESTROY ``MysqlDtsStopTasksService`` 的差异：
      - 本组件只删除入参 ``task_names`` / ``source_names``，**禁止** ``list_tasks`` / ``list_sources`` 全量扫删
      - 用于迁移成功路径 dts-task-clean，不得挂到 DESTROY cleanup
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        master_addr = kwargs.get("master_addr") or ""
        bk_cloud_id = kwargs.get("bk_cloud_id")
        if trans_data is not None and hasattr(trans_data, "migrate_context"):
            if not master_addr:
                master_addr = getattr(trans_data.migrate_context, "master_addr", "") or ""
            if bk_cloud_id is None:
                bk_cloud_id = getattr(trans_data.migrate_context, "bk_cloud_id", None)
        task_names = [n for n in (kwargs.get("task_names") or []) if n]
        source_names = [n for n in (kwargs.get("source_names") or []) if n]
        # 默认不吞错：成功路径 dts-task-clean 必须感知 delete 失败；仅显式 True 时尽力清理
        ignore_errors = bool(kwargs.get("ignore_errors", False))

        if not task_names and not source_names:
            self.log_info(_("本单 task/source 名称列表为空，跳过 delete_task/delete_source"))
            return True
        if not master_addr:
            # 有待删名称却无 Master：配置/编排错误，不可当成功跳过
            self.log_error(_("master_addr 为空，无法删除本单 task/source：tasks={} sources={}").format(task_names, source_names))
            return False
        if bk_cloud_id is None:
            self.log_error(_("bk_cloud_id 为空，无法删除本单 task/source"))
            return False

        tasks_ok = self._delete_tasks(master_addr, int(bk_cloud_id), task_names, ignore_errors)
        purge_ok = True
        if "task_mode" in kwargs and task_mode_runs_incremental(kwargs.get("task_mode")):
            purge_ok = self._purge_relays(master_addr, int(bk_cloud_id), source_names, ignore_errors)
        dump_ok = True
        if self._should_clean_dump(kwargs):
            dump_ok = self._rm_ticket_dump_dirs(kwargs, trans_data, task_names, ignore_errors)
        sources_ok = self._delete_sources(master_addr, int(bk_cloud_id), source_names, ignore_errors)
        if ignore_errors:
            return True
        return tasks_ok and purge_ok and dump_ok and sources_ok

    @staticmethod
    def _should_clean_dump(kwargs: dict) -> bool:
        if "full_load_engine" not in kwargs:
            return False
        engine = (kwargs.get("full_load_engine") or "").strip().lower()
        return engine != FullLoadEngine.MYLOADER.value

    def _delete_tasks(self, master_addr: str, bk_cloud_id: int, task_names: list[str], ignore_errors: bool) -> bool:
        ok = True
        for task_name in task_names:
            try:
                MySQLDTSApi.delete_task(master_addr, task_name, force=True, bk_cloud_id=bk_cloud_id)
                self.log_info(_("删除本单 DTS 任务成功: {}").format(task_name))
            except Exception as exc:  # pylint: disable=broad-except
                if ignore_errors:
                    self.log_warning(_("尽力清理：删除本单任务 {} 失败: {}").format(task_name, exc))
                    continue
                self.log_error(_("删除本单 DTS 任务 {} 失败: {}").format(task_name, exc))
                ok = False
        return ok

    def _purge_relays(self, master_addr: str, bk_cloud_id: int, source_names: list[str], ignore_errors: bool) -> bool:
        ok = True
        for source_name in source_names:
            try:
                status_resp = MySQLDTSApi.get_source_status(master_addr, source_name, bk_cloud_id=bk_cloud_id)
            except Exception as exc:  # pylint: disable=broad-except
                if ignore_errors:
                    self.log_warning(_("尽力清理：查询 Source {} relay 状态失败: {}").format(source_name, exc))
                    continue
                self.log_error(_("查询 Source {} relay 状态失败: {}").format(source_name, exc))
                ok = False
                continue
            binlog_name = resolve_purge_relay_binlog_name(status_resp)
            if not binlog_name:
                self.log_warning(_("Source {} 无法解析 relay 位点，跳过 purge_relay").format(source_name))
                continue
            try:
                MySQLDTSApi.purge_relay(
                    master_addr,
                    source_name,
                    PurgeRelayRequest(relay_binlog_name=binlog_name),
                    bk_cloud_id=bk_cloud_id,
                )
                self.log_info(_("purge_relay 成功: source={} before={}").format(source_name, binlog_name))
            except Exception as exc:  # pylint: disable=broad-except
                if ignore_errors:
                    self.log_warning(_("尽力清理：purge_relay {} 失败: {}").format(source_name, exc))
                    continue
                self.log_error(_("purge_relay {} 失败: {}").format(source_name, exc))
                ok = False
        return ok

    def _rm_ticket_dump_dirs(self, kwargs: dict, trans_data, task_names: list[str], ignore_errors: bool) -> bool:
        plan_like = SimpleNamespace(dts_cluster_id=kwargs.get("dts_cluster_id"))
        migrate_context = getattr(trans_data, "migrate_context", None) if trans_data is not None else None
        dts_cluster_id = resolve_dts_cluster_id(plan_like, migrate_context)
        if not dts_cluster_id:
            self.log_error(_("DTS 集群 ID 为空，无法删除本单 dump 目录"))
            return bool(ignore_errors)
        cluster = MysqlDtsCluster.objects.filter(id=dts_cluster_id).first()
        if not cluster or not cluster.name:
            self.log_error(_("DTS 集群 {} 不存在或名称为空，无法删除本单 dump 目录").format(dts_cluster_id))
            return bool(ignore_errors)
        workers = [n for n in (cluster.worker_nodes or []) if n.get("ip")]
        if not workers:
            self.log_error(_("DTS Worker 为空，无法删除本单 dump 目录"))
            return bool(ignore_errors)
        dump_dirs = [get_full_migrate_data_dir(cluster.name, name) for name in task_names if name]
        if not dump_dirs:
            return True
        seen_ips: set[str] = set()
        exec_targets = []
        for node in workers:
            ip = node["ip"]
            if ip in seen_ips:
                continue
            seen_ips.add(ip)
            exec_targets.append({"ip": ip, "bk_cloud_id": int(node.get("bk_cloud_id") or 0)})
        script = render_clean_ticket_dump_script(dump_dirs)
        try:
            self._fast_execute_script(kwargs, exec_targets, script)
            self.log_info(_("删除本单 dump 目录: {}").format(dump_dirs))
        except Exception as exc:  # pylint: disable=broad-except
            if ignore_errors:
                self.log_warning(_("尽力清理：删除本单 dump 目录失败: {}").format(exc))
                return True
            self.log_error(_("删除本单 dump 目录失败: {}").format(exc))
            return False
        return True

    def _fast_execute_script(self, kwargs: dict, exec_targets: list[dict], shell_script: str) -> None:
        node_name = kwargs.get("node_name") or "mysql_dts_delete_task_source"
        node_id = kwargs.get("node_id") or "mysql_dts_delete_task_source"
        target_ip_info = [{"bk_cloud_id": t["bk_cloud_id"], "ip": t["ip"]} for t in exec_targets]
        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": base64_encode(shell_script),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
            "account_alias": kwargs.get("run_as_system_user", DBA_ROOT_USER),
        }
        JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)

    def _delete_sources(
        self, master_addr: str, bk_cloud_id: int, source_names: list[str], ignore_errors: bool
    ) -> bool:
        ok = True
        for source_name in source_names:
            try:
                MySQLDTSApi.delete_source(master_addr, source_name, force=True, bk_cloud_id=bk_cloud_id)
                self.log_info(_("删除本单 DTS Source 成功: {}").format(source_name))
            except Exception as exc:  # pylint: disable=broad-except
                if ignore_errors:
                    self.log_warning(_("尽力清理：删除本单 Source {} 失败: {}").format(source_name, exc))
                    continue
                self.log_error(_("删除本单 DTS Source {} 失败: {}").format(source_name, exc))
                ok = False
        return ok


class MysqlDtsDeleteTaskSourceComponent(Component):
    name = __name__
    code = "mysql_dts_delete_task_source"
    bound_service = MysqlDtsDeleteTaskSourceService
