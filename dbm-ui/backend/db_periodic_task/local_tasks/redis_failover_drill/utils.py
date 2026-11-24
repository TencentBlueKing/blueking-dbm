"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import datetime
import logging
import time
from typing import Dict, List, Optional, Set, Tuple

from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core.notify.handlers import CmsiHandler
from backend.db_meta.models import AppCache
from backend.db_monitor.constants import MonitorShieldType
from backend.db_monitor.utils import format_shield_description
from backend.db_services.redis.autofix.enums import MsgPriority
from backend.db_services.redis.autofix.message import load_chat_ids_by_priority
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.models import Ticket
from backend.utils.time import date2str

logger = logging.getLogger("celery")


def log_with_context(level, city, message, **kwargs):
    extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
    full_message = f"City: {city} {message}"
    if extra_info:
        full_message += f" {extra_info}"
    getattr(logger, level)(full_message)


def create_drill_alarm_shield(
    bk_biz_id: int,
    immute_domain: str,
    ips: List[str],
    duration_seconds: int = 7200,
) -> Optional[int]:
    """
    为容灾演练目标主机创建监控告警屏蔽（fail-open，失败不阻断演练）。
    """
    ip_list = sorted({ip for ip in (ips or []) if ip})
    if not ip_list:
        return None

    now = datetime.datetime.now()
    begin_time = now.strftime("%Y-%m-%d %H:%M:%S")
    end_time = (now + datetime.timedelta(seconds=max(int(duration_seconds), 60))).strftime("%Y-%m-%d %H:%M:%S")

    dimension_conditions = [
        {"condition": "and", "key": "appid", "method": "eq", "value": [str(bk_biz_id)], "name": "appid"},
    ]
    if immute_domain:
        dimension_conditions.append(
            {
                "condition": "and",
                "key": "cluster_domain",
                "method": "eq",
                "value": [immute_domain],
                "name": "cluster_domain",
            }
        )
    dimension_conditions.append(
        {"condition": "and", "key": "bk_target_ip", "method": "eq", "value": ip_list, "name": "bk_target_ip"}
    )

    shield_param = {
        "category": "dimension",
        "begin_time": begin_time,
        "end_time": end_time,
        "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
        "cycle_config": {"begin_time": "", "end_time": "", "day_list": [], "week_list": [], "type": 1},
        "shield_notice": False,
        "notice_config": {},
        "description": format_shield_description(
            bk_biz_id, description=_("Redis容灾演练-屏蔽告警-{}").format(immute_domain or ",".join(ip_list))
        ),
        "dimension_config": {"dimension_conditions": dimension_conditions},
    }

    try:
        res = BKMonitorV3Api.add_shield(shield_param)
        shield_id = res.get("id")
        logger.info(_("Redis容灾演练创建告警屏蔽成功: shield_id={}, domain={}, ips={}").format(shield_id, immute_domain, ip_list))
        return shield_id
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(_("Redis容灾演练创建告警屏蔽失败(忽略继续演练): domain={}, ips={}, err={}").format(immute_domain, ip_list, e))
        return None


def disable_drill_alarm_shield(shield_id: Optional[int], delay_minutes: int = 15) -> None:
    """
    收敛并解除容灾演练告警屏蔽（fail-open，失败不阻断演练收尾）。
    """
    if not shield_id:
        return

    try:
        detail = BKMonitorV3Api.get_shield({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "id": shield_id})
        edit_param = {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "description": detail["description"],
            "begin_time": detail["begin_time"],
            "end_time": (datetime.datetime.now() + datetime.timedelta(minutes=delay_minutes)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "cycle_config": detail["cycle_config"],
            "shield_notice": detail["shield_notice"],
            "notice_config": detail["notice_config"],
            "id": shield_id,
        }
        if detail.get("category") == MonitorShieldType.STRATEGY.value:
            edit_param["level"] = detail["dimension_config"]["level"]
        BKMonitorV3Api.edit_shield(edit_param)
        logger.info(_("Redis容灾演练收敛告警屏蔽成功: shield_id={}, delay_minutes={}").format(shield_id, delay_minutes))
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(_("Redis容灾演练解除告警屏蔽失败(忽略): shield_id={}, err={}").format(shield_id, e))


def autofix_done_polling(ticket_id, max_retries, interval) -> bool:
    """
    轮询单张自愈单据状态直到完成
    @return: True表示自愈成功完成，False表示失败或超时
    """
    return autofix_tickets_done_polling([ticket_id], max_retries, interval)


def autofix_tickets_done_polling(ticket_ids: List[int], max_retries: int, interval: int) -> bool:
    """
    轮询多张关联自愈单据状态直到全部成功完成（共享总超时预算）
    @return: True表示全部自愈单据均成功完成，False表示任一失败/取消/不存在或超时
    """
    unique_ids = list(dict.fromkeys(tid for tid in (ticket_ids or []) if tid and tid > 0))
    if not unique_ids:
        return False

    start_time = time.time()
    timeout = interval * (max_retries - 1) * 60
    pending_ids = list(unique_ids)

    for n in range(max_retries):
        next_pending: List[int] = []
        for ticket_id in pending_ids:
            try:
                logger.info(_("查询自愈单据状态，轮询第 {}/{} 次，单据ID: {}").format(n + 1, max_retries, ticket_id))
                ticket = Ticket.objects.get(id=ticket_id)

                match ticket.status:
                    case TicketStatus.SUCCEEDED.value:
                        logger.info(_("自愈单据执行成功，单据ID: {}".format(ticket_id)))
                    case TicketStatus.FAILED.value | TicketStatus.REVOKED.value | TicketStatus.TERMINATED.value:
                        logger.warning(_("自愈单据执行失败或被取消，状态: {}，单据ID: {}".format(ticket.status, ticket_id)))
                        return False
                    case _:
                        logger.info(_("自愈单据状态: {}，继续轮询，单据ID: {}".format(ticket.status, ticket_id)))
                        next_pending.append(ticket_id)
            except Ticket.DoesNotExist:
                logger.error(_("自愈单据不存在，单据ID: {}".format(ticket_id)))
                return False
            except Exception as e:
                logger.exception(_("查询自愈单据状态异常: {}".format(str(e))))
                next_pending.append(ticket_id)

        if not next_pending:
            return True
        pending_ids = next_pending

        if timeout < time.time() - start_time:
            logger.warning(_("自愈单据状态轮询超时，未完成单据IDs: {}".format(pending_ids)))
            break

        if n < max_retries - 1:
            time.sleep(interval * 60)

    logger.warning(_("自愈单据轮询结束，未全部获得成功状态，未完成单据IDs: {}".format(pending_ids)))
    return False


def _extract_ticket_fault_ips(ticket: Ticket) -> Set[str]:
    ips: Set[str] = set()
    for info in (ticket.details or {}).get("infos") or []:
        for role_key in ("proxy", "redis_slave"):
            for host in info.get(role_key) or []:
                ip = host.get("ip")
                if ip:
                    ips.add(ip)
    return ips


def _collect_covering_tickets(
    tickets: List[Ticket], target_ips: Set[str], earliest_create_allowed
) -> Tuple[bool, List[int]]:
    covered_ips: Set[str] = set()
    matched_ids: List[int] = []
    for ticket in tickets:
        if ticket.create_at < earliest_create_allowed:
            continue
        ticket_ips = _extract_ticket_fault_ips(ticket)
        overlap = ticket_ips & target_ips
        if overlap and (overlap - covered_ips):
            matched_ids.append(ticket.id)
            covered_ips |= overlap
            if target_ips <= covered_ips:
                logger.info(_("找到覆盖全部演练目标的自愈单据: {}").format(matched_ids))
                return True, matched_ids
    return False, matched_ids


def autofix_tickets_polling(restriction: Dict, max_retries: int, interval: int) -> Tuple[bool, List[int]]:
    """
    轮询直到目标 IP 集合全部出现关联的自愈单据（兼容单张合并单据与按角色拆分的多张单据）。
    restriction: {
        "bk_biz_id": int,
        "ips": Iterable[str] (或单目标 "ip": str),
        "earliest_create_allowed": datetime,
    }
    """
    target_ips: Set[str] = {ip for ip in (restriction.get("ips") or []) if ip}
    if not target_ips and restriction.get("ip"):
        target_ips = {restriction["ip"]}
    if not target_ips:
        return False, []

    start_time = time.time()
    timeout = interval * (max_retries - 1) * 60
    last_matched_ids: List[int] = []

    for n in range(max_retries):
        try:
            logger.info(_("查询最近自愈单据，轮询第 {}/{} 次，目标IPs: {}").format(n + 1, max_retries, sorted(target_ips)))
            tickets = list(
                Ticket.objects.filter(
                    bk_biz_id=restriction["bk_biz_id"],
                    ticket_type=TicketType.REDIS_CLUSTER_AUTOFIX.value,
                ).order_by("-create_at")
            )
            all_covered, last_matched_ids = _collect_covering_tickets(
                tickets, target_ips, restriction["earliest_create_allowed"]
            )
            if all_covered:
                return True, last_matched_ids

        except Exception as e:
            logger.exception("Unexpected error when polling ticket {}, error: {}".format(restriction, e))

        if timeout < time.time() - start_time:
            break

        if n < max_retries - 1:
            time.sleep(interval * 60)

    return False, last_matched_ids


def autofix_ticket_polling(restriction, max_retries, interval) -> Tuple[bool, int]:
    """
    轮询是否出现自愈单据（单 IP 兼容入口）
    restriction: {
        "bk_biz_id": int,
        "ip": str,
        "earliest_create_allowed": datetime,
    }
    """
    all_covered, ticket_ids = autofix_tickets_polling(restriction, max_retries, interval)
    if all_covered and ticket_ids:
        return True, ticket_ids[0]
    return False, -1


def __has_target_ticket(tickets: List[Ticket], restriction) -> Tuple[bool, int]:
    for ticket in tickets:
        if __is_target_ticket(ticket, restriction):
            logger.info(_("找到目标自愈单据，停止轮询"))
            return True, ticket.id
    return False, -1


def __is_target_ticket(ticket: Ticket, restriction) -> bool:
    earliest_create_at = restriction["earliest_create_allowed"]
    if ticket.create_at < earliest_create_at:
        return False

    return restriction["ip"] in _extract_ticket_fault_ips(ticket)


def send_drill_alert_to_qywx(
    city: str,
    bk_biz_id: int,
    cluster_domain: str,
    instance_type: str,
    drill_ip: str,
    failure_reason: str,
    task_status: str,
    version: str = "v1",
):
    """
    发送容灾告警信息到群聊（同自愈配置）

    CHAT_IDS 新格式是 {"L0": [...], "L1": [...]}。演练异常走 L0；
    load_chat_ids_by_priority 同时兼容旧的纯数组。
    """
    msg_ids = load_chat_ids_by_priority(MsgPriority.L0.value)
    if not msg_ids:
        logger.warning(_("No chat IDs configured for drill alerts"))
        return

    try:
        app_info = AppCache.objects.get(bk_biz_id=bk_biz_id)

        redis_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.Redis.value)

        content = _("=>>   Redis容灾演练异常\n")
        content += _("业务信息 : {}(#{}, {})\n".format(app_info.bk_biz_name, app_info.bk_biz_id, app_info.db_app_abbr))
        content += _("业务DBA : @{}\n".format(redis_dba[0]))
        content += _("DBHA版本 : {}\n".format(version))
        content += _("演练城市 : {}\n".format(city))
        content += _("集群域名 : {}\n".format(cluster_domain))
        content += _("演练类型 : {} - {}\n".format(instance_type, drill_ip))
        content += _("演练状态 : {}\n".format(task_status))
        content += _("失败原因 : {}\n".format(failure_reason))
        content += _("消息时间 : {}".format(date2str(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")))

        CmsiHandler(_("Redis容灾演练"), content, msg_ids).send_wecom_robot()
        logger.info(
            _(
                "Drill alert sent successfully for city: {}, cluster: {}, content: {}".format(
                    city, cluster_domain, content
                )
            )
        )

    except Exception as e:
        logger.error(_("Failed to send drill alert: {}".format(str(e))))
