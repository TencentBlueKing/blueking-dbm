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

import copy
import logging
import time
import traceback

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.components import JobApi
from backend.components.mysql_backup.client import RedisBackupApi
from backend.core import consts
from backend.db_services.redis.rollback import download_window
from backend.db_services.redis.rollback.constants import (
    DISK_USED_PLUS_NEED_RATIO_FAIL,
    DISK_USED_RATIO_FAIL,
    DOWNLOAD_BATCH_SIZE,
    DOWNLOAD_INFLIGHT_TASK_LIMIT,
    SSD_CLUSTER_TYPES,
)
from backend.flow.engine.bamboo.scene.redis.redis_rollback.plan import (
    RollbackPlan,
    host_disk_needs,
    memory_budget,
    rollback_manifest,
)
from backend.flow.plugins.components.collections.common.base_service import BaseService, BkJobService
from backend.utils.string import base64_encode, format_size

logger = logging.getLogger("flow")

_PROGRESS_LOG_INTERVAL_SEC = 60


def decode_df_line(disk_line: str) -> dict:
    parts = disk_line.split()
    return {
        "filesystem": parts[0],
        "total": int(parts[1]) * 1024,
        "used": int(parts[2]) * 1024,
        "avail": int(parts[3]) * 1024,
        "used_ratio": int(parts[4].replace("%", "")),
        "mount_on": parts[5],
    }


def same_filesystem(host_disk: dict, backup_disk: dict, data_disk: dict) -> bool:
    """Device numbers decide; hosts reported before they were collected fall back to mount points."""
    backup_dev, data_dev = host_disk.get("redis_backup_dir_dev"), host_disk.get("redis_data_dir_dev")
    if backup_dev and data_dev:
        return str(backup_dev) == str(data_dev)
    return backup_disk["mount_on"] == data_disk["mount_on"]


def disk_needs(backup_disk: dict, data_disk: dict, backup_bytes: int, data_bytes: int, same_fs: bool) -> list:
    """Peak usage per filesystem; a shared one holds both peaks."""
    if same_fs:
        return [(_("备份/数据"), backup_disk, backup_bytes + data_bytes)]
    return [
        (_("备份"), backup_disk, backup_bytes),
        (_("数据"), data_disk, data_bytes),
    ]


class RedisRollbackDiskPrecheckService(BaseService):
    """Gate E: fail before any download when dest host disk, or memory for Cache, is insufficient."""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        try:
            disk_used = getattr(trans_data, "disk_used", None) or {}
            exec_ip = kwargs["exec_ip"]
            host_disk = disk_used.get(exec_ip) or {}
            disks = {}
            for key in ("redis_backup_dir_data", "redis_data_dir_data"):
                raw = host_disk.get(key)
                if not raw:
                    self.log_error(_("{} 缺少磁盘信息: {}").format(exec_ip, key))
                    return False
                disks[key] = decode_df_line(raw)
            same_fs = same_filesystem(host_disk, disks["redis_backup_dir_data"], disks["redis_data_dir_data"])
            plan = RollbackPlan.load(kwargs["plan_id"])
            backup_bytes, data_bytes = host_disk_needs(
                [item for item in plan.items if item.dest_ip == exec_ip],
                plan.cluster_type in SSD_CLUSTER_TYPES,
                int(host_disk.get("cpu_count") or 0),
                plan.max_concurrency,
                is_plus=plan.is_plus,
            )
            needs = disk_needs(
                disks["redis_backup_dir_data"], disks["redis_data_dir_data"], backup_bytes, data_bytes, same_fs
            )
            for label, disk_info, needed_size in needs:
                if not self._check(exec_ip, label, disk_info, needed_size):
                    return False
            if not self._check_memory(exec_ip, host_disk, plan.dest_host(exec_ip).memory_bytes):
                return False
        except Exception as exc:  # pylint: disable=broad-except
            traceback.print_exc()
            self.log_error("redis rollback disk precheck failed:{}".format(exc))
            return False

        self.log_info("redis rollback disk precheck success")
        return True

    def _check_memory(self, exec_ip, host_disk, memory_bytes) -> bool:
        """The shards packed here must fit in memory once loaded; the ticket only checked the spec."""
        if not memory_bytes:
            return True
        available_kb = host_disk.get("mem_available_kb")
        if not available_kb:
            self.log_error(_("{} 缺少内存信息，无法复核内存").format(exec_ip))
            return False
        available, total = int(available_kb) * 1024, int(host_disk.get("mem_total_kb") or 0) * 1024
        budget = memory_budget(available)
        self.log_info(
            _("临时机 {} 内存: 需要 {} / 可用 {} (总量 {}，预留 10% 后可用于加载 {})").format(
                exec_ip, format_size(memory_bytes), format_size(available), format_size(total), format_size(budget)
            )
        )
        if memory_bytes > budget:
            self.log_error(
                _("{} 内存不足: 分到本机的分片加载后约需 {}，预留 10% 后可用 {}").format(
                    exec_ip, format_size(memory_bytes), format_size(budget)
                )
            )
            return False
        return True

    def _check(self, exec_ip, dir_label, disk_info, data_size) -> bool:
        self.log_info(
            _("临时机 {} [{}] {}: 需要 {} / 可用 {} (已用 {}%, 总量 {})").format(
                exec_ip,
                dir_label,
                disk_info["mount_on"],
                format_size(data_size),
                format_size(disk_info["avail"]),
                disk_info["used_ratio"],
                format_size(disk_info["total"]),
            )
        )
        if disk_info["used_ratio"] > DISK_USED_RATIO_FAIL:
            self.log_error(
                _("{} {} 已用 {}% > {}%").format(exec_ip, dir_label, disk_info["used_ratio"], DISK_USED_RATIO_FAIL)
            )
            return False
        if data_size > disk_info["avail"]:
            self.log_error(
                _("{} {} 需要 {} > 可用 {}").format(
                    exec_ip, dir_label, format_size(data_size), format_size(disk_info["avail"])
                )
            )
            return False
        used_plus_need_ratio = (disk_info["used"] + data_size) / disk_info["total"] if disk_info["total"] else 0
        if used_plus_need_ratio > DISK_USED_PLUS_NEED_RATIO_FAIL:
            self.log_error(_("{} {} (已用+需要) 将超过 90%").format(exec_ip, dir_label))
            return False
        return True


class RedisRollbackDiskPrecheckComponent(Component):
    name = __name__
    code = "redis_rollback_disk_precheck"
    bound_service = RedisRollbackDiskPrecheckService


class RedisRollbackDownloadService(BaseService):
    """Download one host's files in fixed batches under the plan-wide window.

    Capacity is reserved on the plan row before a bill is submitted and released when it
    finishes. The persisted ledger lets a retry resume submitted batches instead of
    resubmitting them.
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(15)

    @staticmethod
    def _download_targets(kwargs, plan=None):
        """``(task_ids, bytes)`` from the persisted plan; nodes built before plans were persisted carry them."""
        if plan is not None:
            host = plan.dest_host(kwargs["dest_ip"])
            return host.task_ids, host.download_bytes
        return kwargs["task_ids"], kwargs.get("download_bytes")

    @staticmethod
    def _host_params(kwargs, backup_dir):
        return {
            "bk_cloud_id": kwargs["bk_cloud_id"],
            "dest_ip": kwargs["dest_ip"],
            "login_user": kwargs["login_user"],
            "login_passwd": kwargs["login_passwd"],
            "dest_dir": backup_dir.rstrip("/") + "/dbbak/recover_redis",
            "reason": kwargs.get("reason") or "redis rollback",
        }

    @staticmethod
    def _backup_dir(data, kwargs):
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        return ((getattr(trans_data, "disk_used", None) or {}).get(kwargs["dest_ip"]) or {}).get("backup_dir")

    def _init_window(self, data, kwargs):
        backup_dir = self._backup_dir(data, kwargs)
        if not backup_dir:
            self.log_error(_("{} 缺少备份目录信息，无法确定下载路径").format(kwargs["dest_ip"]))
            return False
        plan = RollbackPlan.load(kwargs["plan_id"])
        task_ids, total_bytes = self._download_targets(kwargs, plan)
        self._batches = [task_ids[i : i + DOWNLOAD_BATCH_SIZE] for i in range(0, len(task_ids), DOWNLOAD_BATCH_SIZE)]
        self._batch_sizes = [len(batch) for batch in self._batches]
        self._plan_id = int(kwargs["plan_id"])
        self._dest_ip = kwargs["dest_ip"]
        self._params = self._host_params(kwargs, backup_dir)
        self._total_bytes = total_bytes
        self._window_ready = True
        data.outputs.batch_sizes = self._batch_sizes
        return True

    def _restore_window(self, data, kwargs):
        """A new worker rebuilds the service instance; batch sizes come from outputs, so the
        plan is only loaded when a batch's task ids are actually needed for submission."""
        backup_dir = self._backup_dir(data, kwargs)
        if not backup_dir:
            self.log_error(_("{} 缺少备份目录信息，无法确定下载路径").format(kwargs["dest_ip"]))
            return False
        self._plan_id = int(kwargs["plan_id"])
        self._dest_ip = kwargs["dest_ip"]
        self._batches = None
        self._batch_sizes = [int(size) for size in (data.get_one_of_outputs("batch_sizes") or [])]
        self._params = self._host_params(kwargs, backup_dir)
        self._total_bytes = data.get_one_of_outputs("download_bytes")
        self._window_ready = True
        return True

    def _batch_at(self, index):
        """Load the plan once, only when a batch's task ids are needed for submission."""
        if self._batches is None:
            task_ids = RollbackPlan.load(self._plan_id).dest_host(self._dest_ip).task_ids
            self._batches = [
                task_ids[i : i + DOWNLOAD_BATCH_SIZE] for i in range(0, len(task_ids), DOWNLOAD_BATCH_SIZE)
            ]
        return self._batches[index]

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        if not kwargs.get("plan_id"):
            return self._execute_legacy(data, kwargs)
        if not self._init_window(data, kwargs):
            return False
        self.log_debug({k: v for k, v in self._params.items() if k != "login_passwd"})
        data.outputs.download_mode = "window"
        data.outputs.total = sum(self._batch_sizes)
        data.outputs.download_bytes = self._total_bytes
        data.outputs.failed = False
        data.outputs.first_submit_at = None
        data.outputs.last_progress_ts = 0
        self._unknown = set()
        data.outputs.unknown_batches = []
        if not self._batch_sizes:
            self.log_info(_("{} 没有需要下载的备份文件").format(self._dest_ip))
            return True
        self._reconcile(data)
        self._advance(data)
        self._log_progress(data, self._read_entries(), force=True)
        return True

    def _execute_legacy(self, data, kwargs) -> bool:
        """Nodes built before plans were persisted: submit everything at once, no window."""
        backup_dir = self._backup_dir(data, kwargs)
        if not backup_dir:
            self.log_error(_("{} 缺少备份目录信息，无法确定下载路径").format(kwargs["dest_ip"]))
            return False
        task_ids, total_bytes = self._download_targets(kwargs)
        params = self._host_params(kwargs, backup_dir)
        self.log_debug({k: v for k, v in params.items() if k != "login_passwd"})
        bill_ids = []
        for start in range(0, len(task_ids), DOWNLOAD_BATCH_SIZE):
            response = RedisBackupApi.download(
                params={**params, "taskid_list": task_ids[start : start + DOWNLOAD_BATCH_SIZE]}
            )
            bill_id = response.get("bill_id", -1)
            if bill_id <= 0:
                # A retry resubmits every batch: bamboo rebuilds outputs on each execute.
                self.log_error(_("提交下载失败: {}；已提交且仍在下载的单号: {}").format(response, bill_ids))
                return False
            bill_ids.append(bill_id)
        self.log_info(
            _("下载备份到 {dest_ip}: files={file_count}, size={total_size}, bills={bill_ids}").format(
                dest_ip=kwargs["dest_ip"],
                file_count=len(task_ids),
                total_size=format_size(total_bytes) if total_bytes is not None else _("未知"),
                bill_ids=bill_ids,
            )
        )
        data.outputs.backup_bill_ids = bill_ids
        data.outputs.download_started_at = time.time()
        data.outputs.download_bytes = total_bytes
        data.outputs.download_mode = "legacy"
        return True

    @staticmethod
    def _download_summary(started_at, total_bytes, now) -> str:
        """Elapsed time and throughput of a host's download; the restore node cannot tell them per port."""
        if not started_at:
            return ""
        elapsed = max(int(now - started_at), 1)
        summary = _("耗时 {}").format(f"{elapsed // 60}m{elapsed % 60}s")
        if total_bytes:
            summary += _("，大小 {}，吞吐 {}/s").format(format_size(total_bytes), format_size(total_bytes // elapsed))
        return summary

    def _execute_failed(self, data, message):
        self.log_error(message)
        data.outputs.failed = True

    def _mark_unknown(self, data, index):
        self._unknown.add(index)
        data.outputs.unknown_batches = sorted(self._unknown)

    def _clear_unknown(self, data, index):
        self._unknown.discard(index)
        data.outputs.unknown_batches = sorted(self._unknown)

    def _read_entries(self):
        return download_window.read_batches(self._plan_id, self._dest_ip)

    def _query_bill(self, bill_id):
        try:
            response = RedisBackupApi.download_result({"bill_id": bill_id})
        except Exception as exc:  # pylint: disable=broad-except
            self.log_error(_("查询下载结果异常: bill={}, {}").format(bill_id, exc))
            return None
        if response is None or "total" not in response:
            return None
        return response["total"]

    def _call_download(self, batch):
        try:
            response = RedisBackupApi.download(params={**self._params, "taskid_list": batch})
        except Exception as exc:  # pylint: disable=broad-except
            self.log_error(_("提交下载异常: {}").format(exc))
            return -1
        return int((response or {}).get("bill_id", -1))

    def _submitted_bills(self):
        return sorted(
            {int(entry["bill_id"]) for entry in self._read_entries().values() if entry.get("bill_id") is not None}
        )

    def _release(self, index, entry, state):
        left = download_window.release(self._plan_id, self._dest_ip, index, state)
        bill_id = entry.get("bill_id")
        self.log_info(
            _("{} 批次 {}/{} 释放: bill={}, state={}, window={}/{}").format(
                self._dest_ip,
                index + 1,
                len(self._batch_sizes),
                bill_id if bill_id is not None else "-",
                state,
                left,
                DOWNLOAD_INFLIGHT_TASK_LIMIT,
            )
        )
        return left

    def _mark_open(self, data, index, bill_id):
        opened = download_window.mark_open(self._plan_id, self._dest_ip, index, bill_id)
        if not opened:
            self._execute_failed(
                data,
                _("{} 批次 {}/{} 台账状态异常，无法标记 open: bill={}").format(
                    self._dest_ip, index + 1, len(self._batch_sizes), bill_id
                ),
            )
            return False
        if not data.get_one_of_outputs("first_submit_at"):
            data.outputs.first_submit_at = time.time()
        return True

    def _submit_reserved(self, data, index, entry):
        """Resubmit a batch whose reservation is still counted (submitting without a bill id)."""
        batch = self._batch_at(index)
        bill_id = self._call_download(batch)
        if bill_id <= 0:
            self._release(index, entry, download_window.DOWNLOAD_STATE_FAILED)
            self._mark_unknown(data, index)
            self._execute_failed(
                data,
                _("{} 批次 {}/{} 重新提交失败；已提交: {}").format(
                    self._dest_ip, index + 1, len(self._batch_sizes), self._submitted_bills()
                ),
            )
            return False
        if not self._mark_open(data, index, bill_id):
            self._mark_unknown(data, index)
            return False
        self.log_info(
            _("{} 批次 {}/{} 重新提交: files={}, bill={}").format(
                self._dest_ip, index + 1, len(self._batch_sizes), len(batch), bill_id
            )
        )
        return True

    def _reconcile(self, data):
        entries = self._read_entries()
        for index in sorted(entries):
            if index >= len(self._batch_sizes):
                self.log_error(_("{} 台账批次 {} 超出计划范围，已忽略").format(self._dest_ip, index))
                continue
            entry = entries[index]
            state = entry.get("state")
            if state in (download_window.DOWNLOAD_STATE_CLOSED, download_window.DOWNLOAD_STATE_FAILED):
                continue
            bill_id = entry.get("bill_id")
            if not bill_id and state in (
                download_window.DOWNLOAD_STATE_SUBMITTING,
                download_window.DOWNLOAD_STATE_OPEN,
            ):
                self.log_info(
                    _("{} 批次 {}/{} 上次提交结果未知，重新提交（可能重复下载）").format(self._dest_ip, index + 1, len(self._batch_sizes))
                )
                if not self._submit_reserved(data, index, entry):
                    break
                continue
            total = self._query_bill(bill_id)
            if total is None:
                self._mark_unknown(data, index)
                self._execute_failed(
                    data,
                    _("{} 批次 {}/{} 查询下载结果失败: bill={}").format(
                        self._dest_ip, index + 1, len(self._batch_sizes), bill_id
                    ),
                )
                continue
            if int(total.get("fail", 0)) > 0:
                self._release(index, entry, download_window.DOWNLOAD_STATE_FAILED)
                self._execute_failed(
                    data,
                    _("{} 批次 {}/{} 下载失败: bill={}；已提交: {}").format(
                        self._dest_ip,
                        index + 1,
                        len(self._batch_sizes),
                        bill_id,
                        self._submitted_bills(),
                    ),
                )
            elif not total.get("todo") and not total.get("doing"):
                self._release(index, entry, download_window.DOWNLOAD_STATE_CLOSED)

    def _advance(self, data):
        if data.get_one_of_outputs("failed"):
            return
        entries = self._read_entries()
        for index in range(len(self._batch_sizes)):
            entry = entries.get(index) or {}
            if entry.get("state") in (
                download_window.DOWNLOAD_STATE_OPEN,
                download_window.DOWNLOAD_STATE_SUBMITTING,
                download_window.DOWNLOAD_STATE_CLOSED,
            ):
                continue
            task_count = self._batch_sizes[index]
            result = download_window.reserve(
                self._plan_id, self._dest_ip, index, task_count, DOWNLOAD_INFLIGHT_TASK_LIMIT
            )
            if result == download_window.RESERVE_NO_WINDOW:
                return
            if result < 0:
                self._execute_failed(
                    data,
                    _("{} 批次 {}/{} 台账已被占用，无法提交").format(self._dest_ip, index + 1, len(self._batch_sizes)),
                )
                return
            batch = self._batch_at(index)
            bill_id = self._call_download(batch)
            if bill_id <= 0:
                download_window.release(self._plan_id, self._dest_ip, index, download_window.DOWNLOAD_STATE_FAILED)
                self._execute_failed(
                    data,
                    _("提交下载失败: 已提交: {}").format(self._submitted_bills()),
                )
                return
            if not self._mark_open(data, index, bill_id):
                self._mark_unknown(data, index)
                return
            self.log_info(
                _("{} 提交下载批次 {}/{}: files={}, bill={}, window={}/{}").format(
                    self._dest_ip,
                    index + 1,
                    len(self._batch_sizes),
                    task_count,
                    bill_id,
                    result,
                    DOWNLOAD_INFLIGHT_TASK_LIMIT,
                )
            )

    def _all_closed(self, entries):
        return all(
            entries.get(index, {}).get("state") == download_window.DOWNLOAD_STATE_CLOSED
            for index in range(len(self._batch_sizes))
        )

    def _finish_success(self, data, entries):
        bill_ids = sorted({int(entry["bill_id"]) for entry in entries.values() if entry.get("bill_id") is not None})
        summary = self._download_summary(
            data.get_one_of_outputs("first_submit_at"), data.get_one_of_outputs("download_bytes"), time.time()
        )
        self.log_info(_("{} 下载成功 {}").format(bill_ids, summary).rstrip())
        self.finish_schedule()

    def _log_progress(self, data, entries, totals=None, force=False):
        total = data.get_one_of_outputs("total") or 0
        if total <= 0:
            return
        now = time.time()
        started = data.get_one_of_outputs("first_submit_at")
        last = data.get_one_of_outputs("last_progress_ts") or 0
        if not force and now - last < download_window.progress_interval(total):
            return
        totals = totals or {}
        done = 0
        open_bills = []
        for index, entry in entries.items():
            count = int(entry.get("task_count") or 0)
            state = entry.get("state")
            if state == download_window.DOWNLOAD_STATE_CLOSED:
                done += count
            elif state == download_window.DOWNLOAD_STATE_OPEN:
                bill_total = totals.get(index)
                if bill_total is None:
                    # No poll result yet: the whole batch still counts as unfinished.
                    open_bills.append({"bill_id": entry.get("bill_id"), "doing": 0})
                    continue
                remaining = int(bill_total.get("todo", 0)) + int(bill_total.get("doing", 0))
                done += max(count - remaining, 0)
                open_bills.append({"bill_id": entry.get("bill_id"), "doing": int(bill_total.get("doing", 0))})
        elapsed = max(now - started, 0) if started else 0
        self.log_info(download_window.format_progress(total, done, open_bills, elapsed))
        data.outputs.last_progress_ts = now

    def _schedule(self, data, parent_data, callback_data=None):
        if data.get_one_of_outputs("download_mode") != "window":
            return self._schedule_legacy(data)
        return self._schedule_window(data)

    def _schedule_window(self, data):
        # A new worker rebuilds the service instance; keep the failed-query set across rounds.
        self._unknown = set(data.get_one_of_outputs("unknown_batches") or [])
        if not getattr(self, "_window_ready", False):
            kwargs = data.get_one_of_inputs("kwargs")
            if data.get_one_of_outputs("batch_sizes") is not None:
                if not self._restore_window(data, kwargs):
                    return False
            elif not self._init_window(data, kwargs):
                return False
        entries = self._read_entries()
        # A reservation without a bill id (process died between submit and ledger update) is
        # resubmitted here, still counted against the window.
        if not data.get_one_of_outputs("failed"):
            for index in sorted(entries):
                entry = entries[index]
                if (
                    index < len(self._batch_sizes)
                    and entry.get("state")
                    in (
                        download_window.DOWNLOAD_STATE_SUBMITTING,
                        download_window.DOWNLOAD_STATE_OPEN,
                    )
                    and not entry.get("bill_id")
                ):
                    if not self._submit_reserved(data, index, entry):
                        break
            entries = self._read_entries()
        totals = {}
        for index in sorted(entries):
            if index >= len(self._batch_sizes):
                continue
            entry = entries[index]
            if entry.get("state") != download_window.DOWNLOAD_STATE_OPEN or not entry.get("bill_id"):
                continue
            total = self._query_bill(entry["bill_id"])
            if total is None:
                self._mark_unknown(data, index)
                self._execute_failed(
                    data,
                    _("{} 批次 {}/{} 查询下载结果失败: bill={}").format(
                        self._dest_ip, index + 1, len(self._batch_sizes), entry.get("bill_id")
                    ),
                )
                continue
            self._clear_unknown(data, index)
            totals[index] = total
            if int(total.get("fail", 0)) > 0:
                self._release(index, entry, download_window.DOWNLOAD_STATE_FAILED)
                self._execute_failed(
                    data,
                    _("{} 批次 {}/{} 下载失败: bill={}；已提交: {}").format(
                        self._dest_ip,
                        index + 1,
                        len(self._batch_sizes),
                        entry.get("bill_id"),
                        self._submitted_bills(),
                    ),
                )
            elif not total.get("todo") and not total.get("doing"):
                self._release(index, entry, download_window.DOWNLOAD_STATE_CLOSED)

        entries = self._read_entries()
        self._log_progress(data, entries, totals)
        if self._all_closed(entries):
            self._log_progress(data, entries, totals, force=True)
            self._finish_success(data, entries)
            return True
        if data.get_one_of_outputs("failed"):
            running = [
                index
                for index, entry in entries.items()
                if entry.get("state")
                in (download_window.DOWNLOAD_STATE_OPEN, download_window.DOWNLOAD_STATE_SUBMITTING)
                and index not in self._unknown
            ]
            if not running:
                self.finish_schedule()
                return False
            return True
        self._advance(data)
        return True

    def _schedule_legacy(self, data):
        bill_ids = data.get_one_of_outputs("backup_bill_ids") or [data.get_one_of_outputs("backup_bill_id")]
        todo = doing = 0
        for bill_id in bill_ids:
            result_response = RedisBackupApi.download_result({"bill_id": bill_id})
            if result_response is None or "total" not in result_response:
                self.log_error(_("{} 查询下载结果失败").format(bill_id))
                self.finish_schedule()
                return False
            total = result_response["total"]
            if total["fail"] > 0:
                self.log_error(_("{} 下载失败").format(bill_id))
                self.finish_schedule()
                return False
            todo += total["todo"]
            doing += total["doing"]
        if todo == 0 and doing == 0:
            summary = self._download_summary(
                data.get_one_of_outputs("download_started_at"), data.get_one_of_outputs("download_bytes"), time.time()
            )
            self.log_info(_("{} 下载成功 {}").format(bill_ids, summary).rstrip())
            self.finish_schedule()
            return True
        last_todo = data.get_one_of_outputs("last_todo")
        last_doing = data.get_one_of_outputs("last_doing")
        last_log_ts = data.get_one_of_outputs("last_progress_log_ts") or 0
        now = time.time()
        if todo != last_todo or doing != last_doing or (now - last_log_ts) >= _PROGRESS_LOG_INTERVAL_SEC:
            self.log_info(_("{} 下载中: todo={} doing={}").format(bill_ids, todo, doing))
            data.outputs.last_todo = todo
            data.outputs.last_doing = doing
            data.outputs.last_progress_log_ts = now
        return True


class RedisRollbackDownloadComponent(Component):
    name = __name__
    code = "redis_rollback_download"
    bound_service = RedisRollbackDownloadService


class RedisRollbackPushManifestService(BkJobService):
    """Pushes the host's file manifest, rendered from the persisted plan, next to its downloads.

    The list never enters node kwargs, the actuator payload or a script body: it goes as a file
    through push_config_file, and only its name and sha256 reach the verify node.
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        dest_ip = kwargs["dest_ip"]
        backup_dir = ((getattr(trans_data, "disk_used", None) or {}).get(dest_ip) or {}).get("backup_dir")
        if not backup_dir:
            self.log_error(_("{} 缺少备份目录信息，无法确定清单路径").format(dest_ip))
            return False

        manifest = rollback_manifest(RollbackPlan.load(kwargs["plan_id"]), kwargs["plan_id"], dest_ip)
        target_dir = backup_dir.rstrip("/") + "/dbbak/recover_redis"
        payload = copy.deepcopy(consts.BK_PUSH_CONFIG_PAYLOAD)
        payload["task_name"] = "{}_{}".format(kwargs["node_name"], kwargs["node_id"])
        payload["file_target_path"] = target_dir
        payload["file_list"] = [{"file_name": manifest.file_name, "content": base64_encode(manifest.content)}]
        payload["target_server"]["ip_list"] = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": dest_ip}]
        self.log_info(
            _("下发文件清单 {}/{} 到 {}: {} 个文件, sha256={}").format(
                target_dir, manifest.file_name, dest_ip, manifest.count, manifest.fingerprint
            )
        )
        data.outputs.ext_result = JobApi.push_config_file(payload, raw=True)
        data.outputs.exec_ips = [dest_ip]
        return True


class RedisRollbackPushManifestComponent(Component):
    name = __name__
    code = "redis_rollback_push_manifest"
    bound_service = RedisRollbackPushManifestService
