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
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from backend.db_meta.enums import MachineType
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLDBHAAutofixTodo
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.group_todo import group_todo
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbcluster.spider_autofix import spider_autofix
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbha.proxy_autofix import proxy_autofix
from backend.db_periodic_task.local_tasks.mysql_autofix.exception import MySQLAutofixException
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.ticket.models import Ticket

logger = logging.getLogger("celery")


@transaction.atomic
@register_periodic_task(run_every=crontab(minute="*"))
def mysql_dbha_autofix():
    """
    查询未结束的dbha事件分类处理
    """
    for gtd in group_todo():
        if gtd.status in [MySQLAutofixTicketStatus.PENDING, MySQLAutofixTicketStatus.RUNNING]:
            tk = Ticket.objects.get(pk=gtd.ticket_id)
            MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(status=tk.status)
            continue

        try:
            if gtd.machine_type == MachineType.PROXY:
                proxy_autofix(gtd=gtd)
            elif gtd.machine_type == MachineType.SPIDER:
                spider_autofix(gtd=gtd)
            else:  # 未实现的全都跳过, 这是保护代码
                MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(
                    status=MySQLAutofixTicketStatus.SKIPPED
                )
        except MySQLAutofixException:
            # ToDo warning all
            MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(
                status=MySQLAutofixTicketStatus.TERMINATED
            )
            pass
        except ObjectDoesNotExist:
            # 集群没找到. 理论上概率很低的
            MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(
                status=MySQLAutofixTicketStatus.TERMINATED
            )
            pass
