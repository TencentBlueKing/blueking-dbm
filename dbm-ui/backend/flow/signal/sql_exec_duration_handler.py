# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQL 执行耗时入队 callback handler。

业务背景：
    用户提交 SQL 文件类单据（MySQL/TenDB Cluster 的 IMPORT_SQLFILE / FORCE_IMPORT_SQLFILE），
    inner flow 完成后由本 handler 把 ticket_id 推入 Redis Set
    （SQL_EXEC_DURATION_CONSUME_KEY），交由 db_periodic_task.local_tasks
    .sql_exec_duration_consume 周期任务 drain 后派发 Celery worker 解析作业日志、入库
    db_report.MysqlSqlExecDuration（≥60s 的长 SQL）。

设计要点：
    - 沿用 callback_map.create_ticket_handler 装饰器风格（与
      mysql_rollback_exercise_handler / tdbctl_upgrade_handler / sqlserver_dts_callback_handler
      保持一致），handlers.py 主回调链路无须知晓本业务白名单。
    - status 语义：call_ticket_handler 透传的是当前节点 to_state（节点级），
      而非 FlowTree 整体状态。同一 ticket 的多个节点 FINISHED 会触发多次 sadd，
      但 Redis Set 天然去重 + 消费函数 record_sql_exec_durations_by_ticket
      已基于 sql_checksum 唯一约束 + bulk_create(ignore_conflicts=True) 幂等，
      多次入队不会造成业务影响。
    - 任何异常仅 warning，绝不影响主回调链路。
    - 加载方式：通过 backend.flow.signal.__init__.py 的
      `from . import sql_exec_duration_handler` 触发模块加载，
      装饰器随之执行并把 handler 注册到 callback_map.TICKET_TYPE_HANDLERS。
      与同目录下 mysql_rollback_exercise_handler / tdbctl_upgrade_handler
      / redis_rollback_exercise_handler 的注册方式保持一致。
"""
import logging

from django.utils.translation import gettext as _

from backend.flow.consts import StateType
from backend.flow.signal.callback_map import create_ticket_handler
from backend.flow.utils.sql_exec_duration_recorder import SQL_EXEC_DURATION_CONSUME_KEY
from backend.ticket.constants import TicketType
from backend.utils.redis import RedisConn

logger = logging.getLogger("flow")


def _enqueue_sql_exec_duration(ticket_id, status):
    """
    SQL 执行耗时入队公共 helper：仅在节点 FINISHED 且 ticket_id 非空时 sadd。

    @param ticket_id: tree.uid，由 call_ticket_handler 透传，按 FlowTree 创建守卫
                      逻辑只可能是 ticket_id 数字字符串或 None
    @param status: 当前节点 to_state，仅 StateType.FINISHED 才触发入队
    """
    if status != StateType.FINISHED or not ticket_id:
        return
    try:
        RedisConn.sadd(SQL_EXEC_DURATION_CONSUME_KEY, ticket_id)
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(_("【SQL 执行耗时入队】sadd 失败 ticket_id={}: {}").format(ticket_id, e))


@create_ticket_handler(TicketType.MYSQL_IMPORT_SQLFILE)
def mysql_import_sqlfile_sql_exec_duration_handler(
    root_id: str, node_id: str, status: StateType, ticket_id=None, **kwargs
):
    """MySQL 变更 SQL 执行：节点 FINISHED 时把 ticket_id 推入 SQL 执行耗时消费队列。"""
    _enqueue_sql_exec_duration(ticket_id, status)


@create_ticket_handler(TicketType.MYSQL_FORCE_IMPORT_SQLFILE)
def mysql_force_import_sqlfile_sql_exec_duration_handler(
    root_id: str, node_id: str, status: StateType, ticket_id=None, **kwargs
):
    """MySQL 强制变更 SQL 执行：节点 FINISHED 时把 ticket_id 推入 SQL 执行耗时消费队列。"""
    _enqueue_sql_exec_duration(ticket_id, status)


@create_ticket_handler(TicketType.TENDBCLUSTER_IMPORT_SQLFILE)
def tendbcluster_import_sqlfile_sql_exec_duration_handler(
    root_id: str, node_id: str, status: StateType, ticket_id=None, **kwargs
):
    """TenDB Cluster 变更 SQL 执行：节点 FINISHED 时把 ticket_id 推入 SQL 执行耗时消费队列。"""
    _enqueue_sql_exec_duration(ticket_id, status)


@create_ticket_handler(TicketType.TENDBCLUSTER_FORCE_IMPORT_SQLFILE)
def tendbcluster_force_import_sqlfile_sql_exec_duration_handler(
    root_id: str, node_id: str, status: StateType, ticket_id=None, **kwargs
):
    """TenDB Cluster 强制变更 SQL 执行：节点 FINISHED 时把 ticket_id 推入 SQL 执行耗时消费队列。"""
    _enqueue_sql_exec_duration(ticket_id, status)
