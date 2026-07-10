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
from backend.components.mysqldtsapi.types import TaskStatusItem
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.constants import (
    MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK,
    MYSQL_DTS_FULL_LOAD_POLL_INTERVAL,
)

logger = logging.getLogger("flow")

_FULL_LOAD_HARD_FAIL_STAGE_TOKENS = ("failed", "error", "paused")
_UNIT_SYNC = "Sync"
_STAGE_FINISHED = "Finished"


@dataclass(frozen=True)
class PollFullLoadTickResult:
    """单次全量完成轮询结果（便于单测，不依赖 Bamboo runtime）。"""

    finished: bool
    success: bool
    fail_streak: int
    reason: str = ""
    last_stage: str = ""
    last_unit: str = ""


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


def evaluate_poll_full_load_tick(
    *,
    items: list[TaskStatusItem] | None,
    fail_streak: int,
    task_mode: str = "all",
    max_fail_streak: int = MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK,
    api_error: str | None = None,
    expected_source_names: list[str] | None = None,
) -> PollFullLoadTickResult:
    """根据本轮 get_task_status 判定全量是否完成。

    - API 异常或空 data：fail_streak++；超阈值 → 失败结束
    - 任务硬失败（error_msg / Failed|Error|Paused；不含 Dump/Load 下 Stopped）→ 失败结束
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
            )
        return PollFullLoadTickResult(
            finished=False,
            success=False,
            fail_streak=new_fail,
            reason=_("查询 DTS 任务状态失败（{}/{}）: {}").format(new_fail, max_fail_streak, api_error),
        )

    if not items:
        new_fail = fail_streak + 1
        if new_fail >= max_fail_streak:
            return PollFullLoadTickResult(
                finished=True,
                success=False,
                fail_streak=new_fail,
                reason=_("连续 {} 次未拿到 DTS 任务状态数据").format(new_fail),
            )
        return PollFullLoadTickResult(
            finished=False,
            success=False,
            fail_streak=new_fail,
            reason=_("本轮任务状态为空（失败 streak {}/{}）").format(new_fail, max_fail_streak),
        )

    last_stage, last_unit = _last_stage_unit(items)
    hard_fail = _task_hard_failed_full_load(items)
    if hard_fail:
        return PollFullLoadTickResult(
            finished=True,
            success=False,
            fail_streak=0,
            reason=hard_fail,
            last_stage=last_stage,
            last_unit=last_unit,
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
        )

    return PollFullLoadTickResult(
        finished=False,
        success=False,
        fail_streak=0,
        reason=_("等待 DTS 全量导入完成：stage={} unit={}").format(last_stage or _("未知"), last_unit or _("未知")),
        last_stage=last_stage,
        last_unit=last_unit,
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
        if not master_addr and trans_data is not None and hasattr(trans_data, "migrate_context"):
            master_addr = trans_data.migrate_context.master_addr
        task_name = kwargs.get("task_name")
        if not master_addr or not task_name:
            self.log_error(_("poll_full_load 缺少 master_addr 或 task_name"))
            self.finish_schedule()
            return False

        fail_streak = int(data.get_one_of_outputs("fail_streak") or 0)
        max_fail = int(kwargs.get("max_fail_streak") or MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK)
        task_mode = kwargs.get("task_mode") or "all"
        source_name_list = kwargs.get("source_name_list")

        items: list[TaskStatusItem] | None = None
        task_query_result: dict[str, Any] | list | None = None
        api_error: str | None = None
        try:
            resp = MySQLDTSApi.get_task_status(master_addr, task_name, source_name_list=source_name_list)
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

        self.log_info(tick.reason)
        return True


class MysqlDtsPollFullLoadComponent(Component):
    name = __name__
    code = "mysql_dts_poll_full_load"
    bound_service = MysqlDtsPollFullLoadService
