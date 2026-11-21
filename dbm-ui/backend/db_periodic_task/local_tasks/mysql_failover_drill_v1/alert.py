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

from celery.schedules import crontab
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.core.notify.handlers import CmsiHandler
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.mysql_failover_drill_v1.record import collect_today_summary

logger = logging.getLogger("celery")

# 推送先写好。改成 True 之后，15:00 才会把当天总结发到企微。
ALERT_ENABLED = False

_REASON_TEXT = {
    "done": _("完成"),
    "not_started": _("今天还没发起"),
    "running": _("还在执行"),
    "failed": _("执行失败"),
    "hosts_held": _("失败且机器未退回"),
    "attempt_limit": _("已到重试次数，仍未成功"),
    "switch_off": _("DBHA v2 总开关未打开"),
}


def _clip(message, limit=80) -> str:
    text = "{}".format(message or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def build_alert_body(rows) -> str:
    """用每个城市、每种集群类型的当天最新结果拼总结。"""
    done = sum(1 for row in rows if row.get("reason") == "done")
    running = sum(1 for row in rows if row.get("reason") == "running")
    not_started = sum(1 for row in rows if row.get("reason") == "not_started")
    switch_off = sum(1 for row in rows if row.get("reason") == "switch_off")
    failed = len(rows) - done - running - not_started - switch_off
    lines = [
        _("启用 {}，完成 {}，失败 {}，进行中 {}，未发起 {}，开关关闭 {}").format(len(rows), done, failed, running, not_started, switch_off),
        _("城市 集群类型 版本 阶段 流程结果 DBHA 次数 说明"),
    ]
    for row in rows:
        reason = _REASON_TEXT.get(row.get("reason"), row.get("reason") or "")
        detail = reason
        error_message = _clip(row.get("error_message"))
        if error_message:
            detail = "{} {}".format(reason, error_message)
        lines.append(
            "{} {} {} {} {} {} {} {}".format(
                row.get("city") or "",
                row.get("cluster_type") or "",
                row.get("version") or "-",
                row.get("phase") or "-",
                row.get("flow_result") or "-",
                row.get("dbha_result") or "-",
                row.get("attempts") or 0,
                detail,
            )
        )
    return "\n".join(lines)


def _cut_content(content: str):
    parts = content.split("\n")
    chunks = []
    current = ""
    for index, line in enumerate(parts):
        if line:
            current += line + "\n"
        if len(current) > 1024 or index == len(parts) - 1:
            chunks.append(current)
            current = ""
    return chunks


@register_periodic_task(run_every=crontab(minute=0, hour=15))
def mysql_failover_drill_v1_alert_task():
    """15:00 用当天每个城市、每种集群类型的最新结果发总结。开关关闭时只记日志。"""
    if not ALERT_ENABLED:
        logger.info("failover drill v1 alert is disabled")
        return
    rows = collect_today_summary()
    if env.MYSQL_CHATID == "" or env.WECOM_ROBOT == "":
        logger.error("failover drill v1 alert skipped: MYSQL_CHATID or WECOM_ROBOT is empty")
        return
    day_text = timezone.localdate().isoformat()
    title = _("【DBM】容灾演练当天总结")
    body = build_alert_body(rows) if rows else _("当天没有启用的演练城市")
    chat_ids = env.MYSQL_CHATID.split(",")
    for msg in _cut_content(body):
        content = _("【DBM】容灾演练当天总结 {}\n{}").format(day_text, msg)
        CmsiHandler(title, content, chat_ids).send_wecom_robot()
