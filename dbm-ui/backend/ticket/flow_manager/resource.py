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
import uuid
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Union

from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.models import Spec
from backend.db_meta.models.spec import ClusterDeployPlan
from backend.db_services.dbresource.exceptions import ResourceApplyException
from backend.ticket import constants
from backend.ticket.constants import FlowCallbackType, FlowType
from backend.ticket.flow_manager.base import BaseTicketFlow
from backend.ticket.flow_manager.delivery import DeliveryFlow
from backend.ticket.models import Flow
from backend.utils.batch_request import request_multi_thread
from backend.utils.time import datetime2str


class ResourceApplyFlow(BaseTicketFlow):
    """
    内置资源申请流程
    """

    def __init__(self, flow_obj: Flow):
        super().__init__(flow_obj=flow_obj)
        self.resource_apply_status = flow_obj.details.get("resource_apply_status", None)

    @property
    def _start_time(self) -> str:
        return datetime2str(self.flow_obj.create_at)

    @property
    def _end_time(self) -> Optional[str]:
        return datetime2str(self.flow_obj.update_at)

    @property
    def _summary(self) -> str:
        return _("资源申请状态{status_display}").format(status_display=constants.TicketStatus.get_choice_label(self.status))

    @property
    def _status(self) -> str:
        if self.resource_apply_status:
            return constants.TicketStatus.SUCCEEDED.value

        return constants.TicketStatus.RUNNING.value

    @property
    def _url(self) -> str:
        return ""

    def callback(self) -> None:
        """
        resource节点独有的钩子函数，执行后继流程节点动作，约定为后继节点的finner flow填充参数
        默认是调用ParamBuilder的后继方法
        """
        callback_info = self.flow_obj.details["callback_info"]
        callback_module = importlib.import_module(callback_info[f"{FlowCallbackType.POST_CALLBACK}_callback_module"])
        callback_class = getattr(callback_module, callback_info[f"{FlowCallbackType.POST_CALLBACK}_callback_class"])
        getattr(callback_class(self.ticket), f"{FlowCallbackType.POST_CALLBACK}_callback")()

    def _format_resource_hosts(self, hosts):
        return [
            {
                # 没有业务ID，认为是公共资源
                "bk_biz_id": host.get("bk_biz_id", 0),
                "ip": host["ip"],
                "bk_cloud_id": host["bk_cloud_id"],
                "bk_host_id": host["bk_host_id"],
                # 补充机器的内存，cpu和磁盘信息
                "bk_cpu": host["cpu_num"],
                "bk_disk": sum([storage["size"] for _, storage in host["storage_device"].items()]),
                "bk_mem": host["dram_cap"],
            }
            for host in hosts
        ]

    def run(self):
        """执行流程并记录流程对象ID"""
        try:
            resource_flow_id = f"{date.today()}{uuid.uuid1().hex[:6]}".replace("-", "")
            self.run_status_handler(resource_flow_id)
            self._run()
        except Exception as err:  # pylint: disable=broad-except
            self.run_error_status_handler(err)
            return

    def apply_resource(self, ticket_data):
        apply_params: Dict[str, Union[str, List]] = {
            "for_biz_id": ticket_data["bk_biz_id"],
            "bk_cloud_id": ticket_data["bk_cloud_id"],
            "resource_type": self.ticket.group,
            "details": [],
            "bill_id": str(ticket_data["uid"]),
            "task_id": self.flow_obj.flow_obj_id,
            "operator": ticket_data["created_by"],
        }

        # 根据规格来申请相应的机器
        if "resource_spec" in ticket_data:
            resource_spec = ticket_data["resource_spec"]
            for role, role_spec in resource_spec.items():
                apply_params["details"].append(
                    Spec.objects.get(spec_id=role_spec["spec_id"]).get_apply_params_detail(role, role_spec["count"])
                )

        # 根据部署方案来申请相应的机器
        if "resource_plan" in ticket_data:
            resource_plan = ticket_data["resource_plan"]
            deploy_plan = ClusterDeployPlan.objects.get(id=resource_plan["resource_plan_id"])
            apply_params["details"].extend(deploy_plan.get_apply_params_details())

        # 向资源池申请机器
        resp = DBResourceApi.resource_pre_apply(params=apply_params, raw=True)
        if resp["code"]:
            raise ResourceApplyException(_("资源申请失败，错误信息: {}").format(resp["message"]))

        resource_request_id, apply_data = resp["request_id"], resp["data"]

        # 将资源池申请的主机信息转换为单据参数
        node_infos: Dict[str, List] = defaultdict(list)
        for info in apply_data:
            role = info["item"]
            host_infos = self._format_resource_hosts(info["data"])
            node_infos[role] = host_infos

        # 针对批量申请的情况，获取当前index
        index = ticket_data.get("index", None)

        return resource_request_id, node_infos, index

    def _run(self) -> None:
        next_flow = self.ticket.next_flow()
        if next_flow.flow_type != FlowType.INNER_FLOW:
            raise ResourceApplyException(_("资源申请下一个节点不为部署节点，请重新编排"))

        # 资源申请
        resource_request_id, node_infos, __ = self.apply_resource(self.flow_obj.details)

        # 将机器信息写入ticket和inner flow
        next_flow.details["ticket_data"].update({"nodes": node_infos, "resource_request_id": resource_request_id})
        next_flow.save(update_fields=["details"])
        self.ticket.update_details(resource_request_id=resource_request_id, nodes=node_infos)
        self.flow_obj.update_details(resource_apply_status=True)

        # 调用后继函数
        self.callback()

        # 执行下一个流程
        from backend.ticket.flow_manager.manager import TicketFlowManager

        TicketFlowManager(ticket=self.ticket).run_next_flow()


class ResourceBatchApplyFlow(ResourceApplyFlow):
    """
    内置批量的资源申请，一般用于批量的添加从库，添加proxy等
    内置格式参考：
    "info": [
        {
            "cluster_id": [1, 2, 3, ...],
            "resource_spec": {
                "new_slave": {"spec_id"": 1, "count": 2}
            }
        }
    ]
    """

    def _run(self) -> None:
        next_flow = self.ticket.next_flow()
        if next_flow.flow_type != FlowType.INNER_FLOW:
            raise ResourceApplyException(_("资源申请下一个节点不为部署节点，请重新编排"))

        # 目前可能存在一个单据多个集群同时操作，但是集群的云区域不同，故当前考虑是批量请求资源池接口
        # TODO: 资源池申请暂不支持跨云查询
        infos = self.flow_obj.details["infos"]
        for index, apply_info in enumerate(infos):
            apply_info.update(index=index)

        params_list = [{"ticket_data": info} for info in infos]
        batch_apply_result = request_multi_thread(
            func=self.apply_resource,
            params_list=params_list,
            get_data=lambda args: {
                "resource_request_id": args[0],
                "nodes": args[1],
                "index": args[2],
            },
        )

        # 将获取的资源信息，序列化到inner flow中
        for apply_result in batch_apply_result:
            infos[apply_result["index"]].update(apply_result["nodes"])

        next_flow.details["ticket_data"].update(infos=infos)
        next_flow.save(update_fields=["details"])
        self.ticket.update_details(batch_apply_result=batch_apply_result)
        self.flow_obj.update_details(resource_apply_status=True)

        # 调用后继函数
        self.callback()

        # 执行下一个流程
        from backend.ticket.flow_manager.manager import TicketFlowManager

        TicketFlowManager(ticket=self.ticket).run_next_flow()


class ResourceDeliveryFlow(DeliveryFlow):
    """
    内置资源申请交付流程，主要是通知资源池机器使用成功
    """

    def confirm_resource(self, ticket_data):
        # 获取request_id和host_ids，资源池后台会校验这两个值是否合法
        resource_request_id: str = ticket_data["resource_request_id"]
        nodes: Dict[str, List] = ticket_data.get("nodes")
        host_ids: List[int] = []
        for __, role_info in nodes.items():
            host_ids.extend([host["bk_host_id"] for host in role_info])

        # 确认资源申请
        DBResourceApi.resource_confirm(params={"request_id": resource_request_id, "host_ids": host_ids})

    def _run(self) -> str:
        self.confirm_resource(self.ticket.details)
        return super()._run()


class ResourceBatchDeliveryFlow(ResourceDeliveryFlow):
    """
    内置资源申请批量交付流程，主要是通知资源池机器使用成功
    """

    def _run(self) -> str:
        confirm_params = self.ticket.details["batch_apply_result"]
        confirm_params_list = [{"ticket_data": info} for info in confirm_params]
        request_multi_thread(
            func=self.confirm_resource,
            params_list=confirm_params_list,
        )
        return "ok"
