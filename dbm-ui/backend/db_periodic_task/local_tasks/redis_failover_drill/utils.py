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
import json
import logging
import time
from typing import List, Tuple

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core.notify.handlers import CmsiHandler
from backend.db_meta.models import AppCache
from backend.db_services.redis.autofix.enums import AutofixItem
from backend.db_services.redis.autofix.models import RedisAutofixCtl
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


def autofix_done_polling(ticket_id, max_retries, interval) -> bool:
    """
    轮询自愈单据状态直到完成
    @return: True表示自愈成功完成，False表示失败或超时
    """
    start_time = time.time()
    timeout = interval * (max_retries - 1) * 60

    for n in range(max_retries):
        try:
            logger.info(_("查询自愈单据状态，轮询第 {}/{} 次".format(n + 1, max_retries)))
            ticket = Ticket.objects.get(id=ticket_id)

            match ticket.status:
                case TicketStatus.SUCCEEDED.value:
                    logger.info(_("自愈单据执行成功，单据ID: {}".format(ticket_id)))
                    return True
                case TicketStatus.FAILED.value | TicketStatus.REVOKED.value | TicketStatus.TERMINATED.value:
                    logger.warning(_("自愈单据执行失败或被取消，状态: {}，单据ID: {}".format(ticket.status, ticket_id)))
                    return False
                case _:
                    # 其他状态(PENDING, APPROVE, RUNNING, TIMER等)继续轮询
                    logger.info(_("自愈单据状态: {}，继续轮询".format(ticket.status)))

        except Ticket.DoesNotExist:
            logger.error(_("自愈单据不存在，单据ID: {}".format(ticket_id)))
            return False
        except Exception as e:
            logger.exception(_("查询自愈单据状态异常: {}".format(str(e))))

        # 检查超时
        if timeout < time.time() - start_time:
            logger.warning(_("自愈单据状态轮询超时，单据ID: {}".format(ticket_id)))
            break

        # 如果不是最后一次轮询，则等待
        if n < max_retries - 1:
            time.sleep(interval * 60)

    logger.warning(_("自愈单据轮询结束，未获得成功状态，单据ID: {}".format(ticket_id)))
    return False


def autofix_ticket_polling(restriction, max_retries, interval) -> Tuple[bool, int]:
    """
    轮询是否出现自愈单据
    restriction: {
        "bk_biz_id": int,
        "ip": str,
        "earliest_create_allowed": datetime,
    }
    """
    start_time = time.time()
    timeout = interval * (max_retries - 1) * 60
    for n in range(max_retries):
        try:
            logger.info(_("查询最近自愈单据，轮询第 {}/{} 次".format(n + 1, max_retries)))
            tickets = Ticket.objects.filter(
                bk_biz_id=restriction["bk_biz_id"],
                ticket_type=TicketType.REDIS_CLUSTER_AUTOFIX.value,
            ).order_by("-create_at")
            result = __has_target_ticket(tickets, restriction)
            if result[0]:
                return result

        except Exception:
            logger.exception("Unexpected error when polling ticket {}".format(restriction))

        if timeout < time.time() - start_time:
            break

        if n < max_retries - 1:
            time.sleep(interval * 60)

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

    recycle_hosts = ticket.details["recycle_hosts"]
    contains_ip = any(ip == restriction["ip"] for ip in recycle_hosts["ip"])

    return contains_ip


def send_drill_alert_to_qywx(
    city: str,
    bk_biz_id: int,
    cluster_domain: str,
    instance_type: str,
    drill_ip: str,
    failure_reason: str,
    task_status: str,
):
    """
    发送容灾告警信息到群聊（同自愈配置）
    """
    msg_ids = []
    try:
        msg_item = RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.CHAT_IDS.value).get()
        if msg_item:
            msg_ids = json.loads(msg_item.ctl_value)
    except RedisAutofixCtl.DoesNotExist:
        RedisAutofixCtl.objects.create(
            bk_cloud_id=0, bk_biz_id=0, ctl_value=json.dumps("[]"), ctl_name=AutofixItem.CHAT_IDS.value
        ).save()

    if len(msg_ids) == 0:
        logger.warning(_("No chat IDs configured for drill alerts"))
        return

    try:
        app_info = AppCache.objects.get(bk_biz_id=bk_biz_id)

        redis_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.Redis.value)

        content = _("=>>   Redis容灾演练异常\n")
        content += _("业务信息 : {}(#{}, {})\n".format(app_info.bk_biz_name, app_info.bk_biz_id, app_info.db_app_abbr))
        content += _("业务DBA : @{}\n".format(redis_dba[0]))
        content += _("演练城市 : {}\n".format(city))
        content += _("集群域名 : {}\n".format(cluster_domain))
        content += _("演练类型 : {} - {}".format(instance_type, drill_ip))
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
