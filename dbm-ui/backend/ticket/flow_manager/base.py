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
import operator
import traceback
from abc import ABC, abstractmethod
from functools import reduce
from typing import Any, Optional, Union

from django.db.models import Q
from django.utils.translation import gettext as _

from backend.ticket import constants
from backend.ticket.builders.common.base import fetch_cluster_ids, fetch_instance_ids
from backend.ticket.constants import FLOW_FINISHED_STATUS, FLOW_NOT_EXECUTE_STATUS, FlowErrCode, TicketFlowStatus
from backend.ticket.models import ClusterOperateRecord, Flow, InstanceOperateRecord

logger = logging.getLogger("root")


class BaseTicketFlow(ABC):
    def __init__(self, flow_obj: Flow):
        self.ticket = flow_obj.ticket
        self.flow_obj = flow_obj

    @property
    def status(self) -> str:
        """查询对应流程的状态，并转化为统一的status状态返回"""

        if self.flow_obj.status in FLOW_FINISHED_STATUS:
            # 如果flow的状态已经处于跳过，成功，则直接返回
            return self.flow_obj.status

        if self.flow_obj.status in [TicketFlowStatus.REVOKED, TicketFlowStatus.TERMINATED]:
            # 如果flow的状态已经被撤销、终止，则直接返回
            return self.flow_obj.status

        if self.flow_obj.err_msg:
            # 如果flow的状态包含错误信息，则是saas侧出错，当前的flow流程直接返回失败
            # 注意：这里不能直接根据flow的状态为失败就进行返回，有可能是pipeline跳过失败的操作

            # 如果是自动重试互斥错误，则返回RUNNING状态
            if self.flow_obj.err_code == FlowErrCode.AUTO_EXCLUSIVE_ERROR:
                return TicketFlowStatus.RUNNING

            return TicketFlowStatus.FAILED

        if self.flow_obj.status in [TicketFlowStatus.RUNNING, TicketFlowStatus.FAILED]:
            # ticket flow 创建成功，查询对应状态
            # 1. 如果是running状态，则查询对应子flow的status
            # 2. 如果是failed状态，但不包含err_msg，说明是异步任务导致的(inner flow)，也要查询对应状态(因为存在重试可能)
            return self._status

        if not self.flow_obj.flow_obj_id:
            # 任务流程未创建时未PENDING状态
            return constants.TicketStatus.PENDING

        # 其他情况暂时认为在PENDING状态
        return TicketFlowStatus.PENDING

    @property
    def start_time(self) -> Optional[str]:
        """开始时间"""
        if self.flow_obj.status not in FLOW_NOT_EXECUTE_STATUS:
            return self._start_time

        return None

    @property
    def end_time(self) -> Optional[str]:
        """结束时间"""
        if self.flow_obj.status not in FLOW_NOT_EXECUTE_STATUS:
            return self._end_time

        return None

    @property
    def url(self) -> str:
        """查询对应流程的状态，并转化为统一的status状态返回"""

        # 如果有错误信息(saas侧失败)或者处于未执行状态，则默认不允许跳转
        if self.flow_obj.status not in FLOW_NOT_EXECUTE_STATUS and not self.flow_obj.err_msg:
            return self._url

        return ""

    @property
    def summary(self) -> str:
        if self.flow_obj.err_msg:
            return self.flow_obj.err_msg

        if self.flow_obj.status == TicketFlowStatus.SKIPPED:
            return _("{}流程已跳过").format(self.flow_obj.flow_alias)

        if self.flow_obj.status != TicketFlowStatus.PENDING:
            return self._summary

        return ""

    def run_error_status_handler(self, err: Exception):
        """run异常处理，更新失败状态和错误信息"""
        err_code = FlowErrCode.get_err_code(err, self.flow_obj.retry_type)
        self.flow_obj.err_msg = f"{err}, traceback: {traceback.format_exc()}"
        self.flow_obj.err_code = err_code
        # 更新flow和ticket的错误信息
        self.flow_obj.status = TicketFlowStatus.FAILED
        self.flow_obj.save(update_fields=["err_code", "err_msg", "status", "update_at"])

        # 如果是自动重试，则认为flow和ticket都在执行，否则打印异常的堆栈
        if err_code == FlowErrCode.AUTO_EXCLUSIVE_ERROR.value:
            self.run_status_handler(flow_obj_id=self.flow_obj.flow_obj_id)
        else:
            logger.error(traceback.format_exc())

    def run_status_handler(self, flow_obj_id: str):
        """run成功时，更新相关状态为RUNNING中"""
        self.flow_obj.flow_obj_id = flow_obj_id
        self.flow_obj.status = TicketFlowStatus.RUNNING
        self.flow_obj.save(update_fields=["flow_obj_id", "status", "update_at"])

    def flush_error_status_handler(self):
        """重试刷新错误节点，更新相关状态，剔除错误信息"""
        self.flow_obj.err_msg = self.flow_obj.err_code = None
        self.flow_obj.status = TicketFlowStatus.RUNNING
        self.flow_obj.save(update_fields=["err_msg", "status", "err_code", "update_at"])

    def create_operate_records(self, object_key, record_model, object_ids):
        """
        写入操作记录的通用方法
        每一轮flow在running时，需要更新当前集群的record.flow为当前flow，为新出现的集群增加record(如定点回档包含了新出现的集群)
        """
        if not object_ids:
            return

        record_filter = reduce(operator.or_, [Q(**{object_key: id, "ticket": self.ticket}) for id in object_ids])
        # 修改当前的flow引用，并批量更新
        to_update_records = record_model.objects.filter(record_filter)
        for record in to_update_records:
            record.flow = self.flow_obj
        record_model.objects.bulk_update(to_update_records, fields=["flow"])

        # 创建新加入的record，并批量创建
        object_ticket_tuples = list(to_update_records.values_list(object_key, "ticket"))
        to_create_records = [
            record_model(
                **{object_key: obj_id, "flow": self.flow_obj, "ticket": self.ticket, "creator": self.ticket.creator}
            )
            for obj_id in object_ids
            if (obj_id, self.ticket.id) not in object_ticket_tuples
        ]
        record_model.objects.bulk_create(to_create_records)

    def create_cluster_operate_records(self):
        """写入集群操作记录"""
        obj_ids = list(set(fetch_cluster_ids(self.flow_obj.details) + fetch_cluster_ids(self.ticket.details)))
        self.create_operate_records(object_key="cluster_id", record_model=ClusterOperateRecord, object_ids=obj_ids)

    def create_instance_operate_records(self):
        """写入示例的操作记录"""
        obj_ids = list(set(fetch_instance_ids(self.flow_obj.details) + fetch_instance_ids(self.ticket.details)))
        self.create_operate_records(object_key="instance_id", record_model=InstanceOperateRecord, object_ids=obj_ids)

    def run(self):
        """执行流程并记录流程对象ID"""
        try:
            flow_obj_id = self._run()
        except Exception as err:  # pylint: disable=broad-except
            self.run_error_status_handler(err)
            return
        try:
            self.create_cluster_operate_records()
            self.create_instance_operate_records()
        except Exception as err:  # pylint: disable=broad-except
            logger.warning("create operate record error, {}".format(err))

        self.run_status_handler(flow_obj_id)

    def retry(self):
        """重试当前的flow节点（默认只能重新执行错误节点）"""
        return self._retry()

    @property
    @abstractmethod
    def _status(self) -> str:
        pass

    @property
    @abstractmethod
    def _end_time(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def _url(self) -> str:
        pass

    @property
    @abstractmethod
    def _summary(self) -> str:
        pass

    @staticmethod
    @abstractmethod
    def _run() -> Union[int, str]:
        """创建对应流程，返回流程对象ID"""
        pass

    @property
    @abstractmethod
    def _start_time(self) -> str:
        pass

    def _retry(self) -> Any:
        # 清空错误信息, 默认重跑run
        self.flush_error_status_handler()
        self.run()

        # 更新单据信息
        from backend.ticket.flow_manager.manager import TicketFlowManager

        TicketFlowManager(self.ticket).update_ticket_status()
