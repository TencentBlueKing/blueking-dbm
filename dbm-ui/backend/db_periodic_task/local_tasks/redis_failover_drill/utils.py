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
import time
from typing import List

from django.utils.translation import ugettext as _

from backend.db_meta.models import LogicalCity
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("celery")


def get_city_list() -> List:
    city_list = [city.name for city in LogicalCity.objects.all() if city.name != "default"]
    return city_list


def autofix_ticket_polling(restriction, max_retries, interval) -> bool:
    """
    轮询是否出现自愈单据
    restriction: {
        "bk_biz_id": int,
        "cluster_id": int,
        "ip": str,
        "earliest_create_allowed": datetime,
    }
    """
    start_time = time.time()
    timeout = interval * max_retries * 60
    for n in range(max_retries):
        try:
            logger.info(_("轮询第 {}/{} 次，查询最近自愈单据".format(n + 1, max_retries)))
            tickets = Ticket.objects.filter(
                bk_biz_id=restriction["bk_biz_id"],
                ticket_type=TicketType.REDIS_CLUSTER_AUTOFIX.value,
            ).order_by("-create_at")
            if __has_target_ticket(tickets, restriction):
                return True

        except Exception:
            logger.exception("Unexpected error when polling ticket {}".format(restriction))

        if timeout < time.time() - start_time:
            break

        if n < max_retries - 1:
            time.sleep(interval * 60)

    return False


def __has_target_ticket(tickets: List[Ticket], restriction) -> bool:
    for ticket in tickets:
        if __is_target_ticket(ticket, restriction):
            logger.info(_("找到目标自愈单据，停止轮询"))
            return True
    return False


def __is_target_ticket(ticket: Ticket, restriction) -> bool:
    earliest_create_at = restriction["earliest_create_allowed"]
    if ticket.create_at < earliest_create_at:
        return False

    infos = ticket.details["infos"]
    for info in infos:
        contains_cluster = any(cluster_id == restriction["cluster_id"] for cluster_id in info["cluster_ids"])
        contains_ip = any(slave["ip"] == restriction["ip"] for slave in info["redis_slave"])
        if contains_cluster and contains_ip:
            return True

    return False
