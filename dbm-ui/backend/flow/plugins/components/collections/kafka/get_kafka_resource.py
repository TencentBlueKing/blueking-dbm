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
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.kafka.kafka_context_dataclass as flow_context
from backend.flow.consts import KafkaFlowEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class GetKafkaResourceService(BaseService):
    """
    根据Kafka单据获取DB资源,在资源池获取节点资源,并根据单据类型拼接对应的参数
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        if global_data["ticket_type"] == KafkaFlowEnum.KAFKA_REPLACE:
            if global_data["new_nodes"].get("broker"):
                trans_data.new_broker_ips = [node["ip"] for node in global_data["new_nodes"]["broker"]]
            if global_data["new_nodes"].get("zookeeper"):
                trans_data.new_zookeeper_ips = [node["ip"] for node in global_data["new_nodes"]["zookeeper"]]
        elif global_data["ticket_type"] == KafkaFlowEnum.KAFKA_SCALE_UP:
            trans_data.new_broker_ips = [node["ip"] for node in global_data["nodes"]["broker"]]
        else:
            trans_data.new_broker_ips = [node["ip"] for node in global_data["nodes"]["broker"]]
            trans_data.new_zookeeper_ips = [node["ip"] for node in global_data["nodes"]["zookeeper"]]

        self.log_info(_("获取机器资源成功成功。 {}").format(trans_data))
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class GetKafkaResourceComponent(Component):
    name = __name__
    code = "get_kafka_resource"
    bound_service = GetKafkaResourceService
