# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

flow 模块通用装饰器集合
"""
import functools
import logging
from typing import Callable

from backend.ticket.constants import TicketStatus
from backend.ticket.models import Ticket

logger = logging.getLogger("json")


def is_ticket_inactive(uid) -> bool:
    """
    检查关联单据是否未运行
    - uid 非 int(无关联单据) 的自动化/巡检/旁路流程, 视为未运行, 直接放行
    """
    try:
        # 采用这种写法是考虑有些自定义发起的任务uid填不存在的
        uid = int(uid)
        return Ticket.objects.filter(id=uid).exclude(status=TicketStatus.RUNNING).exists()
    except ValueError:
        return False


def guard_ticket_revoked(func: Callable) -> Callable:
    """
    单据撤销保护装饰器: 在 pipeline 启动入口前后做"单据是否已撤销"的检查,
    解决 celery -P threads 下 revoke 无法真正打断已在执行的编排任务的问题.

    防线覆盖:
    - 前置: 入口预检, 单据已撤 -> 不再启动 pipeline, 写一条 REVOKED FlowTree, 返回 False
    - 后置: 启动后立刻补 check, 若期间被撤销 -> 主动 revoke 已启动的 pipeline

    使用方式:
        class Builder:
            @guard_ticket_revoked
            def run_pipeline(self, ...): ...
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        uid = self.data.get("uid")

        # 前置: 入口预检, 单据已撤则不再启动 pipeline
        if is_ticket_inactive(uid):
            logger.warning("ticket[%s] is not running, skip run pipeline", uid)
            return False

        result = func(self, *args, **kwargs)

        # 后置: 启动成功后立刻检测, 防住 build_tree 期间 / SDK 启动期间才被撤销的窗口
        if result and is_ticket_inactive(uid):
            from backend.db_services.taskflow.handlers import TaskFlowHandler

            root_id = Ticket.objects.get(id=uid).current_flow().flow_obj_id
            logger.warning("post-check ticket isn't running, root_id=%s uid=%s", root_id, uid)
            TaskFlowHandler(root_id=root_id).revoke_pipeline("admin", remark="post-check ticket isn't running")
            return False

        return result

    return wrapper
