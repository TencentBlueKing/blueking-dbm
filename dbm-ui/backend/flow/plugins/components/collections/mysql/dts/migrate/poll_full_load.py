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
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.components import MySQLDTSApi
from backend.components.mysqldtsapi.types import DumpStatus, LoadStatus, StartTaskRequest, TaskStatusItem
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.constants import (
    DTS_DUMP_GLOBAL_LOCK_MAX_ATTEMPTS,
    MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK,
    MYSQL_DTS_FULL_LOAD_POLL_INTERVAL,
)

logger = logging.getLogger("flow")

_FULL_LOAD_HARD_FAIL_STAGE_TOKENS = ("failed", "error", "paused")
_UNIT_SYNC = "Sync"
_STAGE_FINISHED = "Finished"
_PROGRESS_BAR_WIDTH = 10
_UNIT_DUMP = "dump"
_UNIT_LOAD = "load"
_STAGE_RUNNING = "running"


@dataclass(frozen=True)
class PollFullLoadTickResult:
    """单次全量完成轮询结果（便于单测，不依赖 Bamboo runtime）。"""

    finished: bool
    success: bool
    fail_streak: int
    reason: str = ""
    last_stage: str = ""
    last_unit: str = ""
    retry_dump_lock: bool = False
    lock_timeout_attempts: int = 0


def is_dump_global_lock_timeout(error_msg: str | None) -> bool:
    """识别引擎 Dump 全局锁超时（约 10s，错误码 32004）。"""
    text = (error_msg or "").strip()
    if not text:
        return False
    lower = text.lower()
    if "32004" in text:
        return True
    if "errdumpunitgloballock" in lower.replace("_", ""):
        return True
    if "flush tables lock acquisition timed out" in lower:
        return True
    if "flush table with read lock" in lower and "timeout" in lower:
        return True
    return False


def _dump_lock_timeout_error(items: list[TaskStatusItem]) -> str | None:
    for item in items:
        if is_dump_global_lock_timeout(item.error_msg):
            return (item.error_msg or "").strip()
    return None


def _source_label(item: TaskStatusItem) -> str:
    return item.source_name or item.name or _("未知")


def _task_hard_failed_full_load(items: list[TaskStatusItem]) -> str | None:
    """全量等待硬失败：error_msg / stage 含 Failed|Error|Paused。

    刻意不把 Stopped 当失败（Dump/Load 阶段 stage=Stopped 可继续轮询）。
    与 poll_catchup._task_hard_failed 分叉，禁止直接复用。
    """
    for item in items:
        error_msg = (item.error_msg or "").strip()
        if error_msg:
            return _("源 {} 任务报错: {}").format(_source_label(item), error_msg)
        stage_lower = (item.stage or "").lower()
        if any(token in stage_lower for token in _FULL_LOAD_HARD_FAIL_STAGE_TOKENS):
            return _("源 {} 任务阶段异常: stage={}").format(_source_label(item), item.stage)
    return None


def _item_full_load_done(item: TaskStatusItem, task_mode: str) -> bool:
    """单 source 是否已越过全量（稳态 Sync，或 full+Finished 兜底）。"""
    unit = (item.unit or "").strip()
    stage = (item.stage or "").strip()
    if unit == _UNIT_SYNC:
        return True
    if (task_mode or "").strip().lower() == "full" and stage == _STAGE_FINISHED:
        return True
    return False


def _all_sources_full_load_done(items: list[TaskStatusItem], task_mode: str) -> bool:
    if not items:
        return False
    return all(_item_full_load_done(item, task_mode) for item in items)


def _status_source_key(item: TaskStatusItem) -> str:
    return (item.source_name or item.name or "").strip()


def _expected_sources_mismatch(items: list[TaskStatusItem], expected_source_names: list[str] | None) -> str | None:
    """期望源未全部出现在本轮 status 时返回原因；禁止子集完成假成功。"""
    if not expected_source_names:
        return None
    want = {str(n).strip() for n in expected_source_names if n is not None and str(n).strip()}
    if not want:
        return None
    got = {_status_source_key(item) for item in items if _status_source_key(item)}
    missing = sorted(want - got)
    if not missing:
        return None
    return _("本轮 status 缺少期望源: {}（已返回: {}）").format(",".join(missing), ",".join(sorted(got)) or _("无"))


def _last_stage_unit(items: list[TaskStatusItem]) -> tuple[str, str]:
    if not items:
        return "", ""
    last = items[-1]
    return last.stage or "", last.unit or ""


def _as_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_count(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:g}"


def _percent(done: float, total: float) -> int | None:
    if total <= 0:
        return None
    return min(100, max(0, int((done / total) * 100)))


def _ascii_progress_bar(done: float, total: float, width: int = _PROGRESS_BAR_WIDTH) -> str | None:
    if total <= 0:
        return None
    if done >= total:
        filled = width
    else:
        filled = min(width, max(0, int((done / total) * width)))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def _format_bytes(num: float) -> str:
    value = float(num)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for idx, unit in enumerate(units):
        if value < 1024.0 or idx == len(units) - 1:
            if unit == "B":
                return f"{int(value)}B"
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{value:.1f}TiB"


def _progress_with_bar(done: float | None, total: float | None) -> tuple[str, str]:
    """返回 (分子/分母文案, 可选「条 百分比」后缀)。"""
    unknown = _("未知")
    if done is None and total is None:
        return f"{unknown}/{unknown}", ""
    done_text = unknown if done is None else _format_count(done)
    total_text = unknown if total is None or total <= 0 else _format_count(total)
    ratio = f"{done_text}/{total_text}"
    if done is None or total is None or total <= 0:
        return ratio, ""
    bar = _ascii_progress_bar(done, total)
    pct = _percent(done, total)
    if bar is None or pct is None:
        return ratio, ""
    return ratio, f" {bar} {pct}%"


def _stage_prefix(stage: str | None) -> str:
    text = (stage or "").strip()
    if not text or text.lower() == _STAGE_RUNNING:
        return ""
    return _("stage={} ").format(text)


def _format_dump_progress(dump: DumpStatus | None) -> str:
    if dump is None:
        return _("表进度={}/{}").format(_("未知"), _("未知"))
    completed = _as_number(dump.completed_tables)
    total = _as_number(dump.total_tables)
    ratio, bar_pct = _progress_with_bar(completed, total)
    parts = [_("表进度={}{}").format(ratio, bar_pct)]
    finished_rows = _as_number(dump.finished_rows)
    estimate_rows = _as_number(dump.estimate_total_rows)
    if estimate_rows is not None and estimate_rows > 0:
        row_ratio, _bar = _progress_with_bar(
            0.0 if finished_rows is None else finished_rows,
            estimate_rows,
        )
        parts.append(_("行进度={}").format(row_ratio))
    return " ".join(parts)


def _format_load_progress(load: LoadStatus | None) -> str:
    if load is None:
        return _("字节进度={}/{}").format(_("未知"), _("未知"))
    finished = _as_number(load.finished_bytes)
    total = _as_number(load.total_bytes)
    unknown = _("未知")
    if finished is None and (total is None or total <= 0):
        ratio = f"{unknown}/{unknown}"
        bar_pct = ""
    elif total is None or total <= 0:
        done_text = unknown if finished is None else _format_bytes(finished)
        ratio = f"{done_text}/{unknown}"
        bar_pct = ""
    else:
        done_val = 0.0 if finished is None else finished
        ratio = f"{_format_bytes(done_val)}/{_format_bytes(total)}"
        bar = _ascii_progress_bar(done_val, total)
        pct = _percent(done_val, total)
        bar_pct = f" {bar} {pct}%" if bar is not None and pct is not None else ""
    parts = [_("字节进度={}{}").format(ratio, bar_pct)]
    progress = (load.progress or "").strip()
    if progress:
        parts.append(_("progress={}").format(progress))
    return " ".join(parts)


def _format_item_progress(item: TaskStatusItem) -> str:
    unit = (item.unit or "").strip().lower()
    if unit == _UNIT_DUMP:
        return _format_dump_progress(item.dump_status)
    if unit == _UNIT_LOAD:
        return _format_load_progress(item.load_status)
    return ""


def _format_item_waiting_body(item: TaskStatusItem) -> str:
    unit = (item.unit or "").strip() or _("未知")
    body = _("{}unit={}").format(_stage_prefix(item.stage), unit)
    progress = _format_item_progress(item)
    if progress:
        return f"{body} {progress}"
    return body


def _format_full_load_waiting_reason(items: list[TaskStatusItem]) -> str:
    if len(items) == 1:
        return _("等待 DTS 全量导入完成：{}").format(_format_item_waiting_body(items[0]))
    lines = [_("等待 DTS 全量导入完成：各源仍在全量导入")]
    for item in items:
        lines.append(_("  {} {}").format(_source_label(item), _format_item_waiting_body(item)))
    return "\n".join(lines)


def evaluate_poll_full_load_tick(
    *,
    items: list[TaskStatusItem] | None,
    fail_streak: int,
    task_mode: str = "all",
    max_fail_streak: int = MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK,
    api_error: str | None = None,
    expected_source_names: list[str] | None = None,
    lock_timeout_attempts: int = 0,
    max_lock_timeout_attempts: int = DTS_DUMP_GLOBAL_LOCK_MAX_ATTEMPTS,
) -> PollFullLoadTickResult:
    """根据本轮 get_task_status 判定全量是否完成。

    - API 异常或空 data：fail_streak++；超阈值 → 失败结束
    - Dump 全局锁超时（32004）：合计尝试未满则 retry_dump_lock；满则失败结束
    - 其它任务硬失败（error_msg / Failed|Error|Paused；不含 Dump/Load 下 Stopped）→ 失败结束
    - 全部 source 已越过全量（unit=Sync，或 full+Finished）→ 成功结束（单次即可）
    - 否则 continue；不记忆 Dump→Load 中间态
    """
    if api_error is not None:
        new_fail = fail_streak + 1
        if new_fail >= max_fail_streak:
            return PollFullLoadTickResult(
                finished=True,
                success=False,
                fail_streak=new_fail,
                reason=_("连续查询 DTS 任务状态失败 {} 次，最近错误: {}").format(new_fail, api_error),
                lock_timeout_attempts=lock_timeout_attempts,
            )
        return PollFullLoadTickResult(
            finished=False,
            success=False,
            fail_streak=new_fail,
            reason=_("查询 DTS 任务状态失败（{}/{}）: {}").format(new_fail, max_fail_streak, api_error),
            lock_timeout_attempts=lock_timeout_attempts,
        )

    if not items:
        new_fail = fail_streak + 1
        if new_fail >= max_fail_streak:
            return PollFullLoadTickResult(
                finished=True,
                success=False,
                fail_streak=new_fail,
                reason=_("连续 {} 次未拿到 DTS 任务状态数据").format(new_fail),
                lock_timeout_attempts=lock_timeout_attempts,
            )
        return PollFullLoadTickResult(
            finished=False,
            success=False,
            fail_streak=new_fail,
            reason=_("本轮任务状态为空（失败 streak {}/{}）").format(new_fail, max_fail_streak),
            lock_timeout_attempts=lock_timeout_attempts,
        )

    last_stage, last_unit = _last_stage_unit(items)
    lock_err = _dump_lock_timeout_error(items)
    if lock_err:
        new_attempts = lock_timeout_attempts + 1
        if new_attempts >= max_lock_timeout_attempts:
            return PollFullLoadTickResult(
                finished=True,
                success=False,
                fail_streak=0,
                reason=_("Dump 拿全局锁超时（约 10 秒）已尝试 {} 次，请清理源端长事务后重试节点: {}").format(new_attempts, lock_err),
                last_stage=last_stage,
                last_unit=last_unit,
                lock_timeout_attempts=new_attempts,
            )
        return PollFullLoadTickResult(
            finished=False,
            success=False,
            fail_streak=0,
            reason=_("Dump 全局锁超时，准备重试启动（{}/{}）: {}").format(new_attempts, max_lock_timeout_attempts, lock_err),
            last_stage=last_stage,
            last_unit=last_unit,
            retry_dump_lock=True,
            lock_timeout_attempts=new_attempts,
        )

    hard_fail = _task_hard_failed_full_load(items)
    if hard_fail:
        return PollFullLoadTickResult(
            finished=True,
            success=False,
            fail_streak=0,
            reason=hard_fail,
            last_stage=last_stage,
            last_unit=last_unit,
            lock_timeout_attempts=lock_timeout_attempts,
        )

    mismatch = _expected_sources_mismatch(items, expected_source_names)
    if mismatch:
        return PollFullLoadTickResult(
            finished=False,
            success=False,
            fail_streak=0,
            reason=mismatch,
            last_stage=last_stage,
            last_unit=last_unit,
            lock_timeout_attempts=lock_timeout_attempts,
        )

    if _all_sources_full_load_done(items, task_mode):
        return PollFullLoadTickResult(
            finished=True,
            success=True,
            fail_streak=0,
            reason=_("DTS 全量导入已完成（stage={} unit={} task_mode={}）").format(
                last_stage or _("未知"), last_unit or _("未知"), task_mode or "all"
            ),
            last_stage=last_stage,
            last_unit=last_unit,
            lock_timeout_attempts=lock_timeout_attempts,
        )

    return PollFullLoadTickResult(
        finished=False,
        success=False,
        fail_streak=0,
        reason=_format_full_load_waiting_reason(items),
        last_stage=last_stage,
        last_unit=last_unit,
        lock_timeout_attempts=lock_timeout_attempts,
    )


class MysqlDtsPollFullLoadService(BaseService):
    """Flow 内嵌轮询：等待 builtin 全量导入越过 Dump/Load（见 Sync 或 full+Finished）。"""

    __need_schedule__ = True
    interval = StaticIntervalGenerator(MYSQL_DTS_FULL_LOAD_POLL_INTERVAL)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        data.outputs.task_name = kwargs.get("task_name") or ""
        data.outputs.is_full_load_done = False
        data.outputs.fail_streak = 0
        data.outputs.last_stage = ""
        data.outputs.last_unit = ""
        data.outputs.task_query_result = None
        data.outputs.lock_timeout_attempts = 0
        poll_interval = int(kwargs.get("poll_interval") or MYSQL_DTS_FULL_LOAD_POLL_INTERVAL)
        self.interval = StaticIntervalGenerator(poll_interval)
        self.log_info(
            _("开始轮询 DTS 全量导入完成：任务={}，task_mode={}，间隔={}s，API 失败阈值 {}").format(
                kwargs.get("task_name"),
                kwargs.get("task_mode") or "all",
                poll_interval,
                kwargs.get("max_fail_streak") or MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK,
            )
        )
        return True

    def _write_progress_outputs(self, data, *, task_name: str, tick: PollFullLoadTickResult) -> None:
        data.outputs.task_name = task_name
        data.outputs.is_full_load_done = bool(tick.success)
        data.outputs.fail_streak = tick.fail_streak
        data.outputs.last_stage = tick.last_stage
        data.outputs.last_unit = tick.last_unit
        data.outputs.lock_timeout_attempts = tick.lock_timeout_attempts

    def _write_final_outputs(
        self,
        data,
        *,
        task_name: str,
        task_query_result: dict[str, Any] | list | None,
        tick: PollFullLoadTickResult,
    ) -> None:
        data.outputs.task_query_result = task_query_result
        self._write_progress_outputs(data, task_name=task_name, tick=tick)
        if task_query_result is not None:
            self.log_info(_("DTS 任务查询结果: {}").format(json.dumps(task_query_result, ensure_ascii=False)))

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        master_addr = kwargs.get("master_addr")
        bk_cloud_id = kwargs.get("bk_cloud_id")
        if trans_data is not None and hasattr(trans_data, "migrate_context"):
            if not master_addr:
                master_addr = trans_data.migrate_context.master_addr
            if bk_cloud_id is None:
                bk_cloud_id = trans_data.migrate_context.bk_cloud_id
        task_name = kwargs.get("task_name")
        if not master_addr or not task_name:
            self.log_error(_("poll_full_load 缺少 master_addr 或 task_name"))
            self.finish_schedule()
            return False
        if bk_cloud_id is None:
            self.log_error(_("poll_full_load 缺少 bk_cloud_id"))
            self.finish_schedule()
            return False

        fail_streak = int(data.get_one_of_outputs("fail_streak") or 0)
        lock_timeout_attempts = int(data.get_one_of_outputs("lock_timeout_attempts") or 0)
        max_fail = int(kwargs.get("max_fail_streak") or MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK)
        max_lock_attempts = int(kwargs.get("max_lock_timeout_attempts") or DTS_DUMP_GLOBAL_LOCK_MAX_ATTEMPTS)
        task_mode = kwargs.get("task_mode") or "all"
        source_name_list = kwargs.get("source_name_list")

        items: list[TaskStatusItem] | None = None
        task_query_result: dict[str, Any] | list | None = None
        api_error: str | None = None
        try:
            resp = MySQLDTSApi.get_task_status(
                master_addr, task_name, source_name_list=source_name_list, bk_cloud_id=int(bk_cloud_id)
            )
            items = list(resp.data or [])
            task_query_result = resp.model_dump(mode="json")
        except Exception as exc:  # pylint: disable=broad-except
            api_error = str(exc)

        tick = evaluate_poll_full_load_tick(
            items=items,
            fail_streak=fail_streak,
            task_mode=task_mode,
            max_fail_streak=max_fail,
            api_error=api_error,
            expected_source_names=source_name_list,
            lock_timeout_attempts=lock_timeout_attempts,
            max_lock_timeout_attempts=max_lock_attempts,
        )
        if tick.finished:
            self._write_final_outputs(data, task_name=task_name, task_query_result=task_query_result, tick=tick)
        else:
            self._write_progress_outputs(data, task_name=task_name, tick=tick)

        if tick.finished and tick.success:
            self.log_info(tick.reason)
            self.finish_schedule()
            return True
        if tick.finished and not tick.success:
            self.log_error(tick.reason)
            self.finish_schedule()
            return False

        if tick.retry_dump_lock:
            try:
                MySQLDTSApi.start_task(
                    master_addr,
                    task_name,
                    StartTaskRequest(remove_meta=False, source_name_list=source_name_list),
                    bk_cloud_id=int(bk_cloud_id),
                )
                self.log_warning(tick.reason)
            except Exception as exc:  # pylint: disable=broad-except
                self.log_error(_("Dump 全局锁超时后重启任务失败: {}").format(exc))
                self.finish_schedule()
                return False
        else:
            self.log_info(tick.reason)
        return True


class MysqlDtsPollFullLoadComponent(Component):
    name = __name__
    code = "mysql_dts_poll_full_load"
    bound_service = MysqlDtsPollFullLoadService
