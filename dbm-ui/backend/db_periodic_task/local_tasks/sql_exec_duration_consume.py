# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQL 执行耗时异步消费周期任务：
    每分钟原子 drain Redis Set (SQL_EXEC_DURATION_CONSUME_KEY) → 派发 Celery 异步任务消费。

事件源：backend.flow.signal.handlers.post_set_state_signal_handler
        在 inner flow 成功完成（FINISHED）且 tree.uid 非空时 sadd ticket_id。
消费器：backend.flow.tasks.consume_sql_exec_duration_by_ticket
        实际调用 record_sql_exec_durations_by_ticket 完成日志解析 + 入库。

设计要点：
    - Lua 脚本本地内联，故意不 import db_periodic_task.constants.GET_AND_DELETE_SET_LUA，
      避免与 dbm_aiagent.log_analysis 等其它消费链路在常量层面发生耦合。
    - 周期任务本身只做 "drain set + 派发 Celery task"，毫秒级返回；实际解析 IO
      由 Celery worker 池并行承担。
    - 重复消费天然安全：record_sql_exec_durations_by_ticket → _persist 已基于
      sql_checksum 唯一约束 + bulk_create(ignore_conflicts=True) 兜底幂等。
"""
import logging

from celery.schedules import crontab
from django.utils.translation import gettext as _

from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.flow.tasks import consume_sql_exec_duration_by_ticket
from backend.flow.utils.sql_exec_duration_recorder import SQL_EXEC_DURATION_CONSUME_KEY
from backend.utils.redis import RedisConn

logger = logging.getLogger("flow")

# 本地内联 Lua：原子地拿到 set 全部成员并清空。
# 故意不 import db_periodic_task.constants.GET_AND_DELETE_SET_LUA，
# 避免与其它业务线（dbm_aiagent.log_analysis 等）的消费链路在常量层面发生耦合。
_SQL_EXEC_DURATION_DRAIN_LUA = """
local elements = redis.call('SMEMBERS', KEYS[1])
redis.call('DEL', KEYS[1])
return elements
"""


@register_periodic_task(run_every=crontab(minute="*"))
def periodic_consume_sql_exec_duration():
    """周期任务：原子 drain Redis Set，逐 ticket 派发 SQL 执行耗时消费"""
    script = RedisConn.register_script(_SQL_EXEC_DURATION_DRAIN_LUA)
    ticket_ids = script(keys=[SQL_EXEC_DURATION_CONSUME_KEY])
    if not ticket_ids:
        return
    logger.info(_("SQL 执行耗时周期消费：本轮 drain 到 {} 个 ticket_id").format(len(ticket_ids)))
    for ticket_id in ticket_ids:
        try:
            consume_sql_exec_duration_by_ticket.apply_async(args=(int(ticket_id),))
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(_("派发 SQL 执行耗时消费任务失败 ticket_id={}: {}").format(ticket_id, e))
