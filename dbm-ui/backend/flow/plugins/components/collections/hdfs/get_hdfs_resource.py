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

import backend.flow.utils.hdfs.hdfs_context_dataclass as flow_context
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class GetHdfsResourceService(BaseService):
    """
    根据HDFS单据获取DB资源,在资源池获取节点资源,并根据单据类型拼接对应的参数
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        if global_data["ticket_type"] == TicketType.HDFS_APPLY.value:
            trans_data.nn1_ip = global_data["nn1_ip"]
            trans_data.nn2_ip = global_data["nn2_ip"]
            trans_data.zk_ips = global_data["zk_ips"]
            trans_data.jn_ips = global_data["jn_ips"]
            trans_data.dn_ips = global_data["dn_ips"]
            trans_data.all_ips = global_data["all_ips"]
            trans_data.master_ips = global_data["master_ips"]
        elif global_data["ticket_type"] == TicketType.HDFS_SCALE_UP.value:
            trans_data.new_dn_ips = global_data["new_dn_ips"]
        elif global_data["ticket_type"] == TicketType.HDFS_REPLACE:
            trans_data.cur_nn1_ip = global_data["nn1_ip"]
            trans_data.cur_nn2_ip = global_data["nn2_ip"]
            trans_data.cur_zk_ips = global_data["zk_ips"]
            trans_data.cur_jn_ips = global_data["jn_ips"]
            trans_data.cur_dn_ips = global_data["dn_ips"]
            trans_data.cur_all_ips = global_data["all_ips"]
            trans_data.cur_all_ip_hosts = global_data["all_ip_hosts"]
            trans_data.master_ips = global_data["master_ips"]
            trans_data.new_dn_ips = global_data["new_dn_ips"]

        logger.info(_("获取机器资源成功。 {}").format(trans_data))
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class GetHdfsResourceComponent(Component):
    name = __name__
    code = "get_hdfs_resource"
    bound_service = GetHdfsResourceService
