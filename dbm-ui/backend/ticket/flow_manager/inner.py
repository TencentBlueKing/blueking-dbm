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
import importlib
import logging
from datetime import datetime
from typing import Any, Dict, Union

from django.utils.translation import gettext as _

from backend import env
from backend.db_dirty.handlers import DBDirtyMachineHandler
from backend.db_meta.exceptions import ClusterExclusiveOperateException
from backend.db_meta.models import Cluster
from backend.db_meta.models.sqlserver_dts import SqlserverDtsInfo
from backend.flow.consts import StateType
from backend.flow.models import FlowTree
from backend.ticket import constants
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.constants import (
    BAMBOO_STATE__TICKET_STATE_MAP,
    INNER_FLOW_TODO_STATUS_MAP,
    FlowCallbackType,
    FlowErrCode,
    FlowMsgType,
    TicketFlowStatus,
    TicketType,
    TodoStatus,
    TodoType,
)
from backend.ticket.flow_manager.base import BaseTicketFlow
from backend.ticket.models import Flow, Todo
from backend.ticket.todos import BaseTodoContext
from backend.utils.basic import generate_root_id
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


class InnerFlowDataClass:
    def __init__(self, func):
        self.func_name = func.__name__
        self.class_name = func.__qualname__.split(".")[0]
        self.module = func.__module__

    def to_dict(self) -> Dict[str, str]:
        return {"func_name": self.func_name, "class_name": self.class_name, "module": self.module}


class InnerFlow(BaseTicketFlow):
    """内置任务流程，对应 backend.flow 中编排的任务"""

    def __init__(self, flow_obj: Flow):
        self.root_id = flow_obj.flow_obj_id
        super().__init__(flow_obj=flow_obj)

    @property
    def flow_tree(self) -> FlowTree:
        # 查询 bamboo pipeline 的状态树
        if getattr(self, "_flow_tree", None):
            return self._flow_tree

        try:
            _flow_tree = FlowTree.objects.get(root_id=self.root_id, is_expired=False)
        except FlowTree.DoesNotExist:
            _flow_tree = None

        setattr(self, "_flow_tree", _flow_tree)
        return _flow_tree

    @property
    def _start_time(self) -> Union[str, datetime]:
        # 如果存在flow tree则根据flow tree的时间为准，否则根据单据时间
        if self.flow_tree:
            return datetime2str(self.flow_tree.created_at)

        return self.flow_obj.create_at

    @property
    def _end_time(self) -> Union[str, datetime]:
        if self.flow_tree:
            return datetime2str(self.flow_tree.updated_at)

        return self.flow_obj.update_at

    @property
    def _summary(self) -> str:
        # TODO 可以给出具体失败的节点和原因
        return _("任务{status_display}").format(status_display=constants.TicketFlowStatus.get_choice_label(self.status))

    @property
    def _status(self) -> str:
        # 如果是自动重试互斥错误，则返回RUNNING状态
        if self.flow_obj.err_msg and self.flow_obj.err_code == FlowErrCode.AUTO_EXCLUSIVE_ERROR:
            return TicketFlowStatus.RUNNING

        # 查询流程树状态，如果未找到则直接取flow_obj的status
        if not self.flow_tree:
            status = self.flow_obj.status
        else:
            status = BAMBOO_STATE__TICKET_STATE_MAP.get(self.flow_tree.status, constants.TicketFlowStatus.RUNNING)

        # 根据流程状态映射todo的状态
        todo_status = INNER_FLOW_TODO_STATUS_MAP.get(status, TodoStatus.TODO)
        fail_todo = self.flow_obj.todo_of_flow.filter(type=TodoType.INNER_FAILED).first()
        # 如果任务失败，且不存在todo，则创建一条
        if not fail_todo and todo_status == TodoStatus.TODO:
            self.create_failed_todo()
        # 变更todo状态
        if fail_todo and fail_todo.status != todo_status:
            fail_todo.set_status(self.ticket.creator, todo_status)

        return self.flow_obj.update_status(status)

    @property
    def _url(self) -> str:
        return f"{env.BK_SAAS_HOST}/{self.ticket.bk_biz_id}/task-history/detail/{self.root_id}"

    def create_failed_todo(self):
        Todo.objects.create(
            name=_("【{}】单据任务执行失败，待处理").format(self.ticket.get_ticket_type_display()),
            flow=self.flow_obj,
            ticket=self.ticket,
            type=TodoType.INNER_FAILED,
            context=BaseTodoContext(self.flow_obj.id, self.ticket.id).to_dict(),
            status=TodoStatus.DONE_SUCCESS,
        )

    def check_exclusive_operations(self):
        """判断执行互斥"""
        # TODO: 目前来说，执行互斥对于同时提单或者同时重试的操作是防不住的。
        #  一种更好的实现机制是利用二阶段锁(利用select_for_update, 需要mysql 8.0后端)：
        #  1. 首先获取全局锁global key
        #  2. 然后获取与当前inner flow互斥操作的锁，具体格式为clusterid_ticket_key(在数据库落地记录)
        #  3. 然后释放全局锁
        #  4. 执行后台任务，后台任务执行完成以后，释放互斥锁(即在数据库删掉对应记录)
        #  考虑：如果单纯是为了防住同时操作，是不是设计一个全局锁就好了？
        ticket_type = self.ticket.ticket_type
        if ticket_type == TicketType.SQLSERVER_DISABLE.value or ticket_type in [
            TicketType.SQLSERVER_INCR_MIGRATE,
            TicketType.SQLSERVER_FULL_MIGRATE,
        ]:
            # 判断禁用、迁移集群跟迁移记录是否互斥
            SqlserverDtsInfo.dts_info_clusive(
                ticket_id=self.ticket.id, ticket_type=ticket_type, details=self.ticket.details
            )

        cluster_ids = fetch_cluster_ids(details=self.ticket.details)
        Cluster.handle_exclusive_operations(
            cluster_ids=cluster_ids, ticket_type=ticket_type, exclude_ticket_ids=[self.ticket.id]
        )

    def callback(self, callback_type: FlowCallbackType) -> None:
        """
        inner节点独有的钩子函数，执行前置/后继流程节点动作
        前置/后继动作可以被子流程继承重写，默认是调用ParamBuilder的前置/后继方法
        """
        callback_info = self.flow_obj.details["callback_info"]
        callback_module = importlib.import_module(callback_info[f"{callback_type}_callback_module"])
        callback_class = getattr(callback_module, callback_info[f"{callback_type}_callback_class"])
        getattr(callback_class(self.ticket), f"{callback_type}_callback")()

    def run(self) -> None:
        """inner flow执行流程"""
        # 获取or生成inner flow的root id
        root_id = self.flow_obj.flow_obj_id or generate_root_id()
        try:
            # 由于 _run 执行后可能会触发信号，导致 current_flow 的误判，因此需提前写入 flow_obj_id
            self.run_status_handler(root_id)
            # 判断执行互斥
            self.check_exclusive_operations()
            # flow回调前置钩子函数
            self.callback(callback_type=FlowCallbackType.PRE_CALLBACK.value)
            self._run()
        except (Exception, ClusterExclusiveOperateException) as err:  # pylint: disable=broad-except
            # pipeline构造异常，将新部署的机器挪到污点池
            DBDirtyMachineHandler.handle_dirty_machine(
                self.ticket.id, root_id, origin_tree_status=StateType.RUNNING, target_tree_status=StateType.FAILED
            )
            # 处理互斥异常和非预期的异常
            self.run_error_status_handler(err)
            # 发送创建任务失败通知
            from backend.ticket.tasks.ticket_tasks import send_msg_for_flow

            send_msg_for_flow.apply_async(
                kwargs={
                    "flow_id": self.flow_obj.id,
                    "flow_msg_type": FlowMsgType.DONE.value,
                    "flow_status": TicketFlowStatus.get_choice_label(self.flow_obj.status),
                    "processor": self.ticket.creator,
                    "receiver": self.ticket.creator,
                }
            )
            return
        else:
            # 记录inner flow的集群动作和实例动作
            self.create_cluster_operate_records()
            self.create_instance_operate_records()

    def _run(self) -> None:
        # 创建并执行后台任务流程
        self.flow_obj.refresh_from_db()
        root_id = self.flow_obj.flow_obj_id
        flow_details = self.flow_obj.details

        controller_info = flow_details["controller_info"]
        controller_module = importlib.import_module(controller_info["module"])
        controller_class = getattr(controller_module, controller_info["class_name"])
        controller_inst = controller_class(root_id=root_id, ticket_data=flow_details["ticket_data"])

        return getattr(controller_inst, controller_info["func_name"])()

    def _retry(self) -> Any:
        # 重试则将机器挪出污点池
        DBDirtyMachineHandler.handle_dirty_machine(
            self.ticket.id,
            self.flow_obj.flow_obj_id,
            origin_tree_status=StateType.FAILED,
            target_tree_status=StateType.RUNNING,
        )
        super()._retry()

    def _revoke(self, operator) -> Any:
        # 终止运行的pipeline
        from backend.db_services.taskflow.handlers import TaskFlowHandler

        if FlowTree.objects.filter(root_id=self.flow_obj.flow_obj_id).exists():
            TaskFlowHandler(self.flow_obj.flow_obj_id).revoke_pipeline()
        # 流转flow的终止状态
        super()._revoke(operator)


class QuickInnerFlow(InnerFlow):
    """
    内置快速任务流程
    只需要执行，不需要等待任务结果就可以进入下一个flow
    """

    @property
    def _status(self) -> str:
        return constants.TicketFlowStatus.SUCCEEDED

    @property
    def _summary(self) -> str:
        return _("该任务流程跳过，相关信息可在历史任务中查看")

    def run(self):
        # 执行任务
        super(QuickInnerFlow, self).run()

        # 跳过任务执行结果，直接进入下一流程
        from backend.ticket.flow_manager.manager import TicketFlowManager

        TicketFlowManager(ticket=self.ticket).run_next_flow()


class IgnoreResultInnerFlow(InnerFlow):
    """
    内置可忽略执行结果任务流程
    该任务流程只需要执行完毕，不需要关心执行结果便可以进入下一流程
    """

    @property
    def _summary(self) -> str:
        return _("(执行结果可忽略)任务状态: {status_display}").format(
            status_display=constants.TicketFlowStatus.get_choice_label(self._raw_status)
        )

    @property
    def _raw_status(self) -> str:
        return super(IgnoreResultInnerFlow, self)._status

    @property
    def _status(self) -> str:
        status = self._raw_status
        if status in [constants.TicketFlowStatus.SUCCEEDED, *constants.TICKET_FAILED_STATUS_SET]:
            return constants.TicketFlowStatus.SUCCEEDED

        return status
