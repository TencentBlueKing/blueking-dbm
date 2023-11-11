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
from celery.schedules import crontab

from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.ticket.tasks.ticket_tasks import TicketTask


@register_periodic_task(run_every=5)
def auto_retry_exclusive_inner_flow():
    TicketTask.retry_exclusive_inner_flow()


@register_periodic_task(run_every=crontab(minute=3, hour=2))
def auto_create_data_repair_ticket():
    TicketTask.auto_create_data_repair_ticket()
