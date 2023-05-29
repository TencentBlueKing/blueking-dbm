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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow import Service

import backend.flow.utils.pulsar.pulsar_context_dataclass as flow_context
from backend.flow.consts import PulsarRoleEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType


class GetPulsarResourceService(BaseService):
    """
    根据Pulsar单据获取DB资源,在资源池获取节点资源,并根据单据类型拼接对应的参数
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        if global_data["ticket_type"] == TicketType.PULSAR_APPLY:
            trans_data.new_zk_ips = []
            trans_data.new_bookie_ips = []
            trans_data.new_broker_ips = []
            for role in global_data["nodes"]:
                if role == PulsarRoleEnum.ZooKeeper:
                    trans_data.new_zk_ips = [node["ip"] for node in global_data["nodes"][PulsarRoleEnum.ZooKeeper]]
                elif role == PulsarRoleEnum.BookKeeper:
                    trans_data.new_bookie_ips = [
                        node["ip"] for node in global_data["nodes"][PulsarRoleEnum.BookKeeper]
                    ]
                elif role == PulsarRoleEnum.Broker:
                    trans_data.new_broker_ips = [node["ip"] for node in global_data["nodes"][PulsarRoleEnum.Broker]]

        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class GetPulsarResourceComponent(Component):
    name = __name__
    code = "get_pulsar_resource"
    bound_service = GetPulsarResourceService
