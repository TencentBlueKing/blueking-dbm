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
import uuid
from datetime import date, datetime
from typing import Dict, Union

from django.forms import model_to_dict
from django.utils.translation import gettext as _

from backend.db_meta.exceptions import ClusterExclusiveOperateException
from backend.db_meta.models import Cluster
from backend.flow.models import FlowTree
from backend.ticket import constants
from backend.ticket.constants import BAMBOO_STATE__TICKET_STATE_MAP, FlowCallbackType
from backend.ticket.flow_manager.base import BaseTicketFlow
from backend.ticket.models import ClusterOperateRecord, Flow, InstanceOperateRecord
from backend.utils.basic import get_target_items_from_details
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
            _flow_tree = FlowTree.objects.get(root_id=self.root_id)
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
        return _("任务{status_display}").format(status_display=constants.TicketStatus.get_choice_label(self.status))

    @property
    def _status(self) -> str:
        # 如果当前还未创建出flow tree，则认为单据正在运行
        if not self.flow_tree:
            self.flow_obj.update_status(constants.TicketFlowStatus.RUNNING)
            return constants.TicketStatus.RUNNING

        status = BAMBOO_STATE__TICKET_STATE_MAP.get(self.flow_tree.status, constants.TicketStatus.RUNNING)
        self.flow_obj.update_status(status)
        return status

    @property
    def _url(self) -> str:
        return f"/database/{self.ticket.bk_biz_id}/mission-details/{self.root_id}/"

    def create_cluster_operate_records(self):
        """
        写入集群操作记录
        """
        cluster_ids = get_target_items_from_details(self.flow_obj.details, match_keys=["cluster_id", "cluster_ids"])
        records = [
            ClusterOperateRecord(
                cluster_id=cluster_id, flow=self.flow_obj, ticket=self.ticket, creator=self.ticket.creator
            )
            for cluster_id in cluster_ids
        ]

        # 如果当前记录已经被创建过了，则不重复创建(这里主要是防止重试inner节点造成重复的记录)
        if records and ClusterOperateRecord.objects.filter(**model_to_dict(records[0])).exists():
            return

        ClusterOperateRecord.objects.bulk_create(records)

    def create_instance_operate_records(self):
        """
        写入实例的操作记录
        """
        # TODO 这个函数暂时只考虑StorageInstance，后续应该会将StorageInstance和ProxyInstance合并
        instance_ids = get_target_items_from_details(self.flow_obj.details, match_keys=["instance_id", "instance_ids"])
        records = [
            InstanceOperateRecord(
                instance_id=instance_id, flow=self.flow_obj, ticket=self.ticket, creator=self.ticket.creator
            )
            for instance_id in instance_ids
        ]

        # 如果当前已经被创建过了，则不重复创建
        if records and InstanceOperateRecord.objects.filter(**model_to_dict(records[0])).exists():
            return

        InstanceOperateRecord.objects.bulk_create(records)

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
        cluster_ids = get_target_items_from_details(obj=self.ticket.details, match_keys=["cluster_id", "cluster_ids"])
        Cluster.handle_exclusive_operations(cluster_ids=cluster_ids, ticket_type=ticket_type)

    def handle_exclusive_error(self):
        """处理执行互斥后重试的逻辑"""
        pass

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
        root_id = self.flow_obj.flow_obj_id or f"{date.today()}{uuid.uuid1().hex[:6]}".replace("-", "")
        try:
            # 判断执行互斥
            self.check_exclusive_operations()
            # flow回调前置钩子函数
            self.callback(callback_type=FlowCallbackType.PRE_CALLBACK.value)
            # 由于 _run 执行后可能会触发信号，导致 current_flow 的误判，因此需提前写入 flow_obj_id
            self.run_status_handler(root_id)
            self._run()
        except (Exception, ClusterExclusiveOperateException) as err:  # pylint: disable=broad-except
            # 处理互斥异常和非预期的异常
            self.run_error_status_handler(err)
            return
        else:
            # 记录inner flow的集群动作和实例动作
            self.create_cluster_operate_records()
            self.create_instance_operate_records()

    def _run(self) -> None:
        # 创建并执行后台任务流程
        root_id = self.flow_obj.flow_obj_id
        flow_details = self.flow_obj.details
        controller_info = flow_details["controller_info"]
        controller_module = importlib.import_module(controller_info["module"])
        controller_class = getattr(controller_module, controller_info["class_name"])
        controller_inst = controller_class(root_id=root_id, ticket_data=flow_details["ticket_data"])
        return getattr(controller_inst, controller_info["func_name"])()


class QuickInnerFlow(InnerFlow):
    """
    内置快速任务流程
    只需要执行，不需要等待任务结果就可以进入下一个flow
    """

    @property
    def _status(self) -> str:
        return constants.TicketStatus.SUCCEEDED

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
            status_display=constants.TicketStatus.get_choice_label(self._raw_status)
        )

    @property
    def _raw_status(self) -> str:
        return super(IgnoreResultInnerFlow, self)._status

    @property
    def _status(self) -> str:
        status = self._raw_status
        if status in [constants.TicketStatus.SUCCEEDED, constants.TicketStatus.REVOKED, constants.TicketStatus.FAILED]:
            return constants.TicketStatus.SUCCEEDED

        return status
