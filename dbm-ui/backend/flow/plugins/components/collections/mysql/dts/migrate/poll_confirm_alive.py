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

from dataclasses import dataclass

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.components import MySQLDTSApi
from backend.components.mysqldtsapi.types import SyncStatus, TaskStatusItem
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.common.pause import resolve_pause_ticket
from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_catchup import _task_hard_failed
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK, MYSQL_DTS_CATCHUP_POLL_INTERVAL
from backend.ticket.todos.pipeline_todo import PipelineTodo


@dataclass(frozen=True)
class PollConfirmAliveTickResult:
    """确认节点存活轮询：只有继续等或失败结束，没有轮询成功结束。"""

    fail_streak: int
    finished: bool
    success: bool
    reason: str = ""


def _sync_status_position_text(sync: SyncStatus | None) -> str:
    if sync is None:
        return _("延迟=未知 上游位点=未知 已同步位点=未知")
    delay = sync.seconds_behind_master
    delay_text = _("未知") if delay is None else _("{}s").format(delay)
    master = sync.master_binlog or _("未知")
    syncer = sync.syncer_binlog or _("未知")
    return _("延迟={} 上游位点={} 已同步位点={}").format(delay_text, master, syncer)


def _format_confirm_alive_running_reason(items: list[TaskStatusItem]) -> str:
    if len(items) == 1:
        return _("DTS 任务仍在运行，继续等待人工确认。{}").format(_sync_status_position_text(items[0].sync_status))

    max_delay: int | None = None
    for item in items:
        sync = item.sync_status
        if sync is None or sync.seconds_behind_master is None:
            continue
        if max_delay is None or sync.seconds_behind_master > max_delay:
            max_delay = sync.seconds_behind_master
    max_delay_text = _("未知") if max_delay is None else _("{}s").format(max_delay)
    lines = [_("DTS 任务仍在运行，继续等待人工确认。最大延迟={}").format(max_delay_text)]
    for item in items:
        label = item.source_name or item.name or _("未知")
        lines.append(_("  {} {}").format(label, _sync_status_position_text(item.sync_status)))
    return "\n".join(lines)


def _confirm_alive_hard_failed(items: list[TaskStatusItem]) -> str | None:
    """硬失败对齐 poll_catchup，并额外把 Unscheduled（Worker 离线）当不健康。"""
    reason = _task_hard_failed(items)
    if reason:
        return reason
    for item in items:
        stage = (item.stage or "").lower()
        if "unscheduled" in stage:
            return _("源 {} 任务阶段异常: stage={}").format(item.source_name or item.name or _("未知"), item.stage)
    return None


def evaluate_poll_confirm_alive_tick(
    *,
    items: list[TaskStatusItem] | None,
    fail_streak: int,
    max_fail_streak: int = MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK,
    api_error: str | None = None,
) -> PollConfirmAliveTickResult:
    """根据本轮 get_task_status 判定确认节点是继续等还是失败。

    - API 异常或空 data：fail_streak++；超阈值 → 失败结束
    - 任务硬失败（含 Unscheduled）：直接失败结束
    - 其余（含 Running 但 unit 不是 Sync、lag>0）：继续等，fail_streak 清零
    """
    if api_error is not None:
        new_fail = fail_streak + 1
        if new_fail >= max_fail_streak:
            return PollConfirmAliveTickResult(
                fail_streak=new_fail,
                finished=True,
                success=False,
                reason=_("连续查询 DTS 任务状态失败 {} 次，最近错误: {}").format(new_fail, api_error),
            )
        return PollConfirmAliveTickResult(
            fail_streak=new_fail,
            finished=False,
            success=False,
            reason=_("查询 DTS 任务状态失败（{}/{}）: {}").format(new_fail, max_fail_streak, api_error),
        )

    if not items:
        new_fail = fail_streak + 1
        if new_fail >= max_fail_streak:
            return PollConfirmAliveTickResult(
                fail_streak=new_fail,
                finished=True,
                success=False,
                reason=_("连续 {} 次未拿到 DTS 任务状态数据").format(new_fail),
            )
        return PollConfirmAliveTickResult(
            fail_streak=new_fail,
            finished=False,
            success=False,
            reason=_("本轮任务状态为空（失败 streak {}/{}）").format(new_fail, max_fail_streak),
        )

    hard_fail = _confirm_alive_hard_failed(items)
    if hard_fail:
        return PollConfirmAliveTickResult(
            fail_streak=0,
            finished=True,
            success=False,
            reason=hard_fail,
        )

    return PollConfirmAliveTickResult(
        fail_streak=0,
        finished=False,
        success=False,
        reason=_format_confirm_alive_running_reason(items),
    )


class MysqlDtsPollConfirmAliveService(BaseService):
    """人工确认待办 + 间隔存活轮询。点确认立刻成功结束，不再查 status。"""

    __need_schedule__ = True
    interval = StaticIntervalGenerator(MYSQL_DTS_CATCHUP_POLL_INTERVAL)

    def _execute(self, data, parent_data) -> bool:
        self._pass_without_ticket = False
        kwargs = data.get_one_of_inputs("kwargs") or {}
        global_data = data.get_one_of_inputs("global_data") or {}
        data.outputs.fail_streak = 0
        poll_interval = int(kwargs.get("poll_interval") or MYSQL_DTS_CATCHUP_POLL_INTERVAL)
        self.interval = StaticIntervalGenerator(poll_interval)

        ticket = resolve_pause_ticket(global_data.get("uid"))
        if not ticket:
            self._pass_without_ticket = True
            self.log_info(_("uid 非有效单据 ID，跳过确认节点直接放行: {}").format(global_data.get("uid")))
            return True

        flow = ticket.current_flow()
        PipelineTodo.create(ticket, flow, self.runtime_attrs.get("root_pipeline_id"), self.runtime_attrs.get("id"))
        self.log_info(
            _("开始确认节点存活轮询：任务={}，间隔={}s，API 失败阈值 {}").format(
                kwargs.get("task_name"),
                poll_interval,
                kwargs.get("max_fail_streak") or MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK,
            )
        )
        return True

    def need_schedule(self):
        if getattr(self, "_pass_without_ticket", False):
            return False
        return super().need_schedule()

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        if callback_data is not None:
            self.log_info("callback_data: {}".format(callback_data))
            data.outputs.callback_data = callback_data
            self.finish_schedule()
            return True

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
            self.log_error(_("poll_confirm_alive 缺少 master_addr 或 task_name"))
            self.finish_schedule()
            return False
        if bk_cloud_id is None:
            self.log_error(_("poll_confirm_alive 缺少 bk_cloud_id"))
            self.finish_schedule()
            return False

        fail_streak = int(data.get_one_of_outputs("fail_streak") or 0)
        max_fail = int(kwargs.get("max_fail_streak") or MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK)
        source_name_list = kwargs.get("source_name_list")

        items: list[TaskStatusItem] | None = None
        api_error: str | None = None
        try:
            resp = MySQLDTSApi.get_task_status(
                master_addr, task_name, source_name_list=source_name_list, bk_cloud_id=int(bk_cloud_id)
            )
            items = list(resp.data or [])
        except Exception as exc:  # pylint: disable=broad-except
            api_error = str(exc)

        tick = evaluate_poll_confirm_alive_tick(
            items=items,
            fail_streak=fail_streak,
            max_fail_streak=max_fail,
            api_error=api_error,
        )
        data.outputs.fail_streak = tick.fail_streak

        if tick.finished:
            self.log_error(tick.reason)
            self.finish_schedule()
            return False

        self.log_info(tick.reason)
        return True


class MysqlDtsPollConfirmAliveComponent(Component):
    name = _("增量同步确认并存活轮询")
    code = "mysql_dts_poll_confirm_alive"
    bound_service = MysqlDtsPollConfirmAliveService
