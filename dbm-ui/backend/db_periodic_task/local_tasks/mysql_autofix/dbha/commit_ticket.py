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
import threading
import traceback
from typing import List

from backend.components.bkmonitorv3.client import BKMonitorV3EventApi
from backend.db_monitor.constants import MonitorEventType
from backend.db_monitor.dataclass import BaseEventBody, MonitorEvent
from backend.db_monitor.models import MySQLDBHAAutofixTicketStageQueue, TicketQueueCommitException
from backend.ticket.constants import TicketStatus
from backend.ticket.models import Ticket

logger = logging.getLogger("celery.mysql_dbha_autofix")

mysql_dbha_af_commiter_lock = threading.Lock()


# @transaction.atomic
def commit_ticket(uncommit_tickets: List[MySQLDBHAAutofixTicketStageQueue]):
    """
    这里拿到的输入, queue_uuid 可能会有重复的
    每一个 queue_uuid 只要随便拿一行来提单就行
    """
    if not uncommit_tickets:
        return

    with mysql_dbha_af_commiter_lock:
        logger.info("[commit_ticket] start, input queue_uuids=%s", [ut.queue_uuid for ut in uncommit_tickets])
        commited = []
        for ut in uncommit_tickets:
            if ut.queue_uuid in commited:
                continue

            try:
                ticket_param = ut.ticket_param
                tk = Ticket.create_ticket(**ticket_param)
                MySQLDBHAAutofixTicketStageQueue.objects.filter(queue_uuid=ut.queue_uuid).update(
                    ticket_id=tk.pk, status=TicketStatus.PENDING
                )
                commited.append(ut.queue_uuid)
                logger.info("[commit_ticket] created ticket_id=%d for queue_uuid=%s", tk.pk, ut.queue_uuid)
            except Exception:  # noqa
                err_msg = traceback.format_exc()
                logger.exception("[commit_ticket] failed to create ticket for queue_uuid=%s", ut.queue_uuid)
                MySQLDBHAAutofixTicketStageQueue.objects.filter(queue_uuid=ut.queue_uuid).update(
                    status=TicketQueueCommitException,
                    error_message=err_msg,
                )
                BKMonitorV3EventApi.send_event(
                    events=[
                        MonitorEvent(
                            event_name=MonitorEventType.MYSQL_DBHA_AUTOFIX_COMMIT_FAILED,
                            target=ut.queue_uuid,
                            event=BaseEventBody(
                                content=f"commit ticket failed for queue_uuid={ut.queue_uuid}, error: {err_msg[-256:]}"
                            ),
                            dimension={
                                "cluster_id": ut.cluster_id,
                                "machine_type": ut.machine_type,
                                "queue_uuid": ut.queue_uuid,
                            },
                            timestamp=0,
                        )
                    ]
                )

        logger.info("[commit_ticket] done, committed queue_uuids=%s", commited)
