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
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union

from django.utils.translation import gettext as _

from backend.ticket import constants
from backend.ticket.constants import FLOW_FINISHED_STATUS, FLOW_NOT_EXECUTE_STATUS, FlowErrCode, TicketFlowStatus
from backend.ticket.models import Flow

logger = logging.getLogger("root")


def _get_target_items_from_details(
    obj: Union[dict, list], match_keys: List[str], target_items: Optional[List[Any]] = None
) -> List[Any]:
    """
    递归获取单据参数中的所有目标对象(目标对象类型为: int, str, dict。如果有后续类型需求可扩展)
    以集群位例：所有集群 cluster_ids, cluster_id 字段的值的集合，如
    {
        "cluster_id": 1,
        ...
        "cluster_ids": [1, 2, 3]
        ...
        "rules": [{"cluster_id": 4, ...}, {"cluster_id": 5, ...}],
        ...
        "xxx_infos": [{"cluster_ids": [5, 6], ...}, {"cluster_ids": [6, 7], ...}],
    }
    得到的 cluster_ids = set([1, 2, 3, 4, 5, 6, 7])
    """

    def _union_target(_target_items: List[Any], target: Union[list, Any]):
        if isinstance(target, list):
            _target_items.extend(target)
        if isinstance(target, (int, str, dict)):
            _target_items.append(target)
        return _target_items

    target_items = target_items or []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in match_keys:
                target_items = _union_target(target_items, value)
            if isinstance(value, (dict, list)):
                target_items = _get_target_items_from_details(value, match_keys, target_items)

    if isinstance(obj, list):
        for _obj in obj:
            target_items = _get_target_items_from_details(_obj, match_keys, target_items)

    return target_items


def get_target_items_from_details(
    obj: Union[dict, list], match_keys: List[str], target_items: Optional[List[Any]] = None
) -> List[Any]:
    target_items = _get_target_items_from_details(obj, match_keys, target_items)
    target_items_type = set([type(item) for item in target_items])

    if len(target_items_type) != 1 or not target_items:
        return target_items

    if target_items and isinstance(target_items[0], (int, str)):
        return list(set(target_items))
    else:
        return target_items


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

        if self.flow_obj.status == TicketFlowStatus.REVOKED:
            # 如果flow的状态已经被撤销，则直接返回
            return TicketFlowStatus.REVOKED

        if self.flow_obj.err_msg:
            # 如果flow的状态包含错误信息，则是saas侧出错，当前的flow流程直接返回失败
            # 注意：这里不能直接根据flow的状态为失败就进行返回，有可能是pipeline跳过失败的操作

            # 如果是自动重试互斥错误，则返回RUNNING状态
            if self.flow_obj.err_code == FlowErrCode.AUTO_EXCLUSIVE_ERROR:
                return TicketFlowStatus.RUNNING

            return TicketFlowStatus.FAILED

        if self.flow_obj.flow_obj_id or self.flow_obj.status == TicketFlowStatus.RUNNING:
            # ticket flow 创建成功，查询对应状态
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
        logger.exception(f"fail to run flow: {err}")
        err_code = FlowErrCode.get_err_code(err, self.flow_obj.retry_type)
        self.flow_obj.err_msg = err
        self.flow_obj.err_code = err_code
        # 更新flow和ticket的错误信息
        self.flow_obj.status = TicketFlowStatus.FAILED
        self.flow_obj.save(update_fields=["err_code", "err_msg", "status", "update_at"])

        self.ticket.status = constants.TicketStatus.FAILED
        self.ticket.save(update_fields=["status", "update_at"])

        # 如果是自动重试，则认为flow和ticket都在执行
        if err_code == FlowErrCode.AUTO_EXCLUSIVE_ERROR.value:
            self.run_status_handler(flow_obj_id="")

    def run_status_handler(self, flow_obj_id: str):
        """run成功时，更新相关状态为RUNNING中"""
        self.flow_obj.flow_obj_id = flow_obj_id
        self.flow_obj.status = TicketFlowStatus.RUNNING
        self.flow_obj.save(update_fields=["flow_obj_id", "status", "update_at"])

        self.ticket.status = constants.TicketStatus.RUNNING
        self.ticket.save(update_fields=["status", "update_at"])

    def flush_error_status_handler(self):
        """重试刷新错误节点，更新相关状态，剔除错误信息"""
        self.flow_obj.err_msg = self.flow_obj.err_code = None
        self.flow_obj.status = TicketFlowStatus.RUNNING
        self.flow_obj.save(update_fields=["err_msg", "status", "err_code", "update_at"])

        self.ticket.status = constants.TicketStatus.RUNNING
        self.ticket.save(update_fields=["status", "update_at"])

    def run(self):
        """执行流程并记录流程对象ID"""
        try:
            flow_obj_id = self._run()
        except Exception as err:  # pylint: disable=broad-except
            self.run_error_status_handler(err)
            return

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
