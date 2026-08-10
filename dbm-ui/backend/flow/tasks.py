# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

flow 模块的 Celery 异步任务集合。

放在 backend.flow.tasks 而非 backend.flow.utils.sql_exec_duration_recorder，
是为了避免业务工具函数被 @shared_task 装饰器的副作用（celery 注册表写入）污染，
也方便 Celery 自动发现（与 db_monitor.tasks / db_services.ipchooser.tasks 风格一致）。
"""
import logging

from celery import shared_task
from django.utils.translation import gettext as _

from backend.flow.utils.sql_exec_duration_recorder import record_sql_exec_durations_by_ticket

logger = logging.getLogger("flow")


@shared_task
def consume_sql_exec_duration_by_ticket(ticket_id: int):
    """
    异步消费单个 ticket 的 SQL 执行耗时记录。

    由 db_periodic_task.local_tasks.sql_exec_duration_consume.periodic_consume_sql_exec_duration
    周期任务从 Redis Set (SQL_EXEC_DURATION_CONSUME_KEY) 原子 drain 后批量派发。

    捕获所有异常，确保单 ticket 失败不影响其他 worker task。
    实际入库逻辑（含日志解析、阈值过滤、checksum 去重）由 record_sql_exec_durations_by_ticket 完成。
    """
    try:
        result = record_sql_exec_durations_by_ticket(ticket_id=ticket_id)
        total_inserted = result.get("total_inserted", 0)
        scanned = result.get("scanned", 0)
        instance_count = result.get("instance_count", 0)
        failures = result.get("failures") or []
        if failures:
            logger.warning(
                _("消费 SQL 执行耗时记录部分失败 ticket={} inserted={} scanned={} " "instance_count={} failures={}").format(
                    ticket_id, total_inserted, scanned, instance_count, failures
                )
            )
        elif total_inserted == 0:
            # instance_count=0：无作业实例；scanned=0：实例存在但无可拉日志 IP；
            # scanned>0：已解析但均低于入库阈值
            logger.info(
                _("消费 SQL 执行耗时记录完成 ticket={} 无可入库记录 " "instance_count={} scanned={} result={}").format(
                    ticket_id, instance_count, scanned, result
                )
            )
        else:
            logger.info(
                _("消费 SQL 执行耗时记录完成 ticket={} inserted={} scanned={} instance_count={}").format(
                    ticket_id, total_inserted, scanned, instance_count
                )
            )
    except Exception as e:
        logger.exception(_("消费 SQL 执行耗时记录失败 ticket={}: {}").format(ticket_id, e))
