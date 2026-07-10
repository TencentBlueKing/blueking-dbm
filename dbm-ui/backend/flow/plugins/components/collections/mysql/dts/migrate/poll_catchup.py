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
from typing import Any, Iterable

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.components import MySQLDTSApi
from backend.components.mysqldtsapi.types import SyncStatus, TaskStatusItem
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.constants import (
    MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK,
    MYSQL_DTS_CATCHUP_POLL_INTERVAL,
    MYSQL_DTS_CATCHUP_REQUIRED_CONSECUTIVE,
)

logger = logging.getLogger("flow")


@dataclass(frozen=True)
class PollCatchupTickResult:
    """单次轮询状态机结果（便于单测，不依赖 Bamboo runtime）。"""

    consecutive_catchup: int
    fail_streak: int
    finished: bool
    success: bool
    last_sbm: int | None = None
    last_master_file: str = ""
    last_syncer_file: str = ""
    reason: str = ""


def _first_sync_status(items: Iterable[TaskStatusItem]) -> SyncStatus | None:
    for item in items:
        if item.sync_status is not None:
            return item.sync_status
    return None


def _status_source_key(item: TaskStatusItem) -> str:
    return (item.source_name or item.name or "").strip()


def _expected_sources_mismatch(items: list[TaskStatusItem], expected_source_names: list[str] | None) -> str | None:
    """期望源未全部出现在本轮 status 时返回原因；禁止子集追平假成功。"""
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


def _all_sources_poll_caught_up(items: list[TaskStatusItem]) -> bool:
    """多 source 全部满足单次追平条件才算本轮追平。"""
    if not items:
        return False
    for item in items:
        sync = item.sync_status
        if sync is None or not sync.is_poll_caught_up():
            return False
    return True


def _task_hard_failed(items: list[TaskStatusItem]) -> str | None:
    """任务级明确失败：立刻结束节点（不计入偶发 API streak）。"""
    for item in items:
        error_msg = (item.error_msg or "").strip()
        if error_msg:
            return _("源 {} 任务报错: {}").format(item.source_name or item.name or _("未知"), error_msg)
        stage = (item.stage or "").lower()
        if any(token in stage for token in ("failed", "error", "paused", "stopped")):
            return _("源 {} 任务阶段异常: stage={}").format(item.source_name or item.name or _("未知"), item.stage)
    return None


def evaluate_poll_catchup_tick(
    *,
    items: list[TaskStatusItem] | None,
    consecutive_catchup: int,
    fail_streak: int,
    required_consecutive: int = MYSQL_DTS_CATCHUP_REQUIRED_CONSECUTIVE,
    max_fail_streak: int = MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK,
    api_error: str | None = None,
    expected_source_names: list[str] | None = None,
) -> PollCatchupTickResult:
    """根据本轮 get_task_status 结果推进 consecutive / fail_streak。

    - API 异常或空 data：fail_streak++，consecutive 不变；超阈值 → 失败结束
    - 任务硬失败：直接失败结束
    - 全部 source 追平：consecutive++；达阈值 → 成功结束
    - 未追平：consecutive 清零，fail_streak 清零
    """
    if api_error is not None:
        new_fail = fail_streak + 1
        if new_fail >= max_fail_streak:
            return PollCatchupTickResult(
                consecutive_catchup=consecutive_catchup,
                fail_streak=new_fail,
                finished=True,
                success=False,
                reason=_("连续查询 DTS 任务状态失败 {} 次，最近错误: {}").format(new_fail, api_error),
            )
        return PollCatchupTickResult(
            consecutive_catchup=consecutive_catchup,
            fail_streak=new_fail,
            finished=False,
            success=False,
            reason=_("查询 DTS 任务状态失败（{}/{}）: {}").format(new_fail, max_fail_streak, api_error),
        )

    if not items:
        new_fail = fail_streak + 1
        if new_fail >= max_fail_streak:
            return PollCatchupTickResult(
                consecutive_catchup=consecutive_catchup,
                fail_streak=new_fail,
                finished=True,
                success=False,
                reason=_("连续 {} 次未拿到 DTS 任务状态数据").format(new_fail),
            )
        return PollCatchupTickResult(
            consecutive_catchup=consecutive_catchup,
            fail_streak=new_fail,
            finished=False,
            success=False,
            reason=_("本轮任务状态为空（失败 streak {}/{}）").format(new_fail, max_fail_streak),
        )

    hard_fail = _task_hard_failed(items)
    sync = _first_sync_status(items)
    last_sbm = sync.seconds_behind_master if sync else None
    master_coord = sync.master_coord() if sync else None
    syncer_coord = sync.syncer_coord() if sync else None
    last_master_file = master_coord.file if master_coord else ""
    last_syncer_file = syncer_coord.file if syncer_coord else ""

    if hard_fail:
        return PollCatchupTickResult(
            consecutive_catchup=0,
            fail_streak=0,
            finished=True,
            success=False,
            last_sbm=last_sbm,
            last_master_file=last_master_file,
            last_syncer_file=last_syncer_file,
            reason=hard_fail,
        )

    mismatch = _expected_sources_mismatch(items, expected_source_names)
    if mismatch:
        return PollCatchupTickResult(
            consecutive_catchup=0,
            fail_streak=0,
            finished=False,
            success=False,
            last_sbm=last_sbm,
            last_master_file=last_master_file,
            last_syncer_file=last_syncer_file,
            reason=mismatch,
        )

    if _all_sources_poll_caught_up(items):
        new_consecutive = consecutive_catchup + 1
        if new_consecutive >= required_consecutive:
            return PollCatchupTickResult(
                consecutive_catchup=new_consecutive,
                fail_streak=0,
                finished=True,
                success=True,
                last_sbm=last_sbm,
                last_master_file=last_master_file,
                last_syncer_file=last_syncer_file,
                reason=_("已连续 {} 次确认追平（SBM=0 且同 binlog 文件）").format(new_consecutive),
            )
        return PollCatchupTickResult(
            consecutive_catchup=new_consecutive,
            fail_streak=0,
            finished=False,
            success=False,
            last_sbm=last_sbm,
            last_master_file=last_master_file,
            last_syncer_file=last_syncer_file,
            reason=_("本轮已追平，连续计数 {}/{}").format(new_consecutive, required_consecutive),
        )

    return PollCatchupTickResult(
        consecutive_catchup=0,
        fail_streak=0,
        finished=False,
        success=False,
        last_sbm=last_sbm,
        last_master_file=last_master_file,
        last_syncer_file=last_syncer_file,
        reason=_("本轮未追平，已重置连续计数。SBM={} master_file={} syncer_file={} master_ge_syncer={}").format(
            last_sbm if last_sbm is not None else _("未知"),
            last_master_file or _("未知"),
            last_syncer_file or _("未知"),
            sync.is_master_not_behind_syncer() if sync else False,
        ),
    )


class MysqlDtsPollCatchupService(BaseService):
    """Flow 内嵌轮询：连续 N 次「SBM==0 且同 binlog 文件」后通过。

    偶发 get_task_status 失败只累计 fail_streak，不立刻失败节点。
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(MYSQL_DTS_CATCHUP_POLL_INTERVAL)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        data.outputs.task_name = kwargs.get("task_name") or ""
        data.outputs.is_caught_up = False
        data.outputs.consecutive_catchup = 0
        data.outputs.fail_streak = 0
        data.outputs.last_sbm = None
        data.outputs.last_master_file = ""
        data.outputs.last_syncer_file = ""
        data.outputs.task_query_result = None
        poll_interval = int(kwargs.get("poll_interval") or MYSQL_DTS_CATCHUP_POLL_INTERVAL)
        self.interval = StaticIntervalGenerator(poll_interval)
        self.log_info(
            _("开始轮询 DTS 追平状态：任务={}，间隔={}s，需连续 {} 次，API 失败阈值 {}").format(
                kwargs.get("task_name"),
                poll_interval,
                kwargs.get("required_consecutive") or MYSQL_DTS_CATCHUP_REQUIRED_CONSECUTIVE,
                kwargs.get("max_fail_streak") or MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK,
            )
        )
        return True

    def _write_progress_outputs(self, data, *, task_name: str, tick: PollCatchupTickResult) -> None:
        """轮询过程中只更新轻量进度字段，避免每轮刷完整 task 响应。"""
        data.outputs.task_name = task_name
        data.outputs.is_caught_up = bool(tick.success)
        data.outputs.consecutive_catchup = tick.consecutive_catchup
        data.outputs.fail_streak = tick.fail_streak
        data.outputs.last_sbm = tick.last_sbm
        data.outputs.last_master_file = tick.last_master_file
        data.outputs.last_syncer_file = tick.last_syncer_file

    def _write_final_outputs(
        self,
        data,
        *,
        task_name: str,
        task_query_result: dict[str, Any] | list | None,
        tick: PollCatchupTickResult,
    ) -> None:
        """schedule 结束时写入 get_task_status 原始响应到节点 outputs。"""
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
            self.log_error(_("poll_catchup 缺少 master_addr 或 task_name"))
            self.finish_schedule()
            return False

        consecutive = int(data.get_one_of_outputs("consecutive_catchup") or 0)
        fail_streak = int(data.get_one_of_outputs("fail_streak") or 0)
        required = int(kwargs.get("required_consecutive") or MYSQL_DTS_CATCHUP_REQUIRED_CONSECUTIVE)
        max_fail = int(kwargs.get("max_fail_streak") or MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK)
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

        tick = evaluate_poll_catchup_tick(
            items=items,
            consecutive_catchup=consecutive,
            fail_streak=fail_streak,
            required_consecutive=required,
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


class MysqlDtsPollCatchupComponent(Component):
    name = __name__
    code = "mysql_dts_poll_catchup"
    bound_service = MysqlDtsPollCatchupService
