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

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class GetRiakResourceService(BaseService):
    """
    根据Riak单据获取DB资源,在资源池获取节点资源,并根据单据类型拼接对应的参数
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if global_data["ip_source"] == "manual_input":
            ips = [node["ip"] for node in global_data["nodes"]]
            if global_data["ticket_type"] == TicketType.RIAK_CLUSTER_APPLY and len(ips) >= 3:
                trans_data.nodes = ips
                trans_data.base_node = ips[0]
                trans_data.operate_nodes = ips[1:]
            elif (
                global_data["ticket_type"] == TicketType.RIAK_CLUSTER_SCALE_OUT
                or global_data["ticket_type"] == TicketType.RIAK_CLUSTER_SCALE_IN
            ) and len(ips) >= 1:
                trans_data.operate_nodes = ips
            else:
                self.log_error(_("获取机器资源失败，新建集群至少选择3台机器，扩容或缩容至少选择1台机器"))
                return False
        elif self.data["ip_source"] == "resource_pool":
            pass

        self.log_info(_("获取机器资源成功。 {}").format(trans_data))
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
        ]


class GetRiakResourceComponent(Component):
    name = __name__
    code = "get_riak_resource"
    bound_service = GetRiakResourceService
