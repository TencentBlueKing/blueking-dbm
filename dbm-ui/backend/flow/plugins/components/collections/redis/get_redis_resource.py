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

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.flow.consts import MediumEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis.db_resource import RedisResource

logger = logging.getLogger("flow")


class GetRedisResourceService(BaseService):
    """
    根据Redis单据获取DB资源,在资源池获取节点资源,并根据单据类型拼接对应的参数
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        #  页面输入
        if global_data["ip_source"] == "manual_input":
            proxy = global_data["nodes"]["proxy"]
            master = global_data["nodes"]["master"]
            slave = global_data["nodes"]["slave"]

            trans_data.new_proxy_ips = []
            trans_data.new_master_ips = []
            trans_data.new_slave_ips = []
            for node in proxy:
                trans_data.new_proxy_ips.append(node["ip"])
            for node in master:
                trans_data.new_master_ips.append(node["ip"])
            for node in slave:
                trans_data.new_slave_ips.append(node["ip"])
        elif self.data["ip_source"] == "resource_pool":
            resource = RedisResource()
            post_details = resource.get_payload_params(
                city=global_data["city"],
                cross_switch=True,
                spec=global_data["spec"],
                group_count=global_data["group_num"],
                ticket_type=global_data["ticket_type"],
            )

            new_nodes = resource.get_nodes(post_details=post_details)
            if not new_nodes:
                return False

            for temp in new_nodes:
                # new Redis and proxy is list
                if temp["item"] == MediumEnum.Twemproxy:
                    for host in temp["data"]:
                        trans_data.new_proxy_ips.append(host["ip"])
                else:
                    trans_data.new_master_ips.append(temp["data"][0]["ip"])
                    trans_data.new_slave_ips.append(temp["data"][1]["ip"])
        trans_data.init_var(
            global_data["shard_num"], global_data["cluster_name"], cluster_type=global_data["cluster_type"]
        )

        self.log_info(_("获取机器资源成功成功。 {}").format(trans_data))
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class GetRedisResourceComponent(Component):
    name = __name__
    code = "get_redis_resource"
    bound_service = GetRedisResourceService
