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

import backend.flow.utils.es.es_context_dataclass as flow_context
from backend.flow.consts import ESRoleEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class GetEsResourceService(BaseService):
    """
    根据Es单据获取DB资源,在资源池获取节点资源,并根据单据类型拼接对应的参数
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        #  页面输入
        # 由于flow传参基本不变，无需判断 IP来源 属于 手动选择/资源池
        trans_data.new_hot_ips = []
        trans_data.new_cold_ips = []
        trans_data.new_master_ips = []
        trans_data.new_client_ips = []
        for role in global_data["nodes"]:
            if role == ESRoleEnum.HOT:
                trans_data.new_hot_ips = [node["ip"] for node in global_data["nodes"][role]]
            elif role == ESRoleEnum.COLD:
                trans_data.new_cold_ips = [node["ip"] for node in global_data["nodes"][role]]
            elif role == ESRoleEnum.MASTER:
                trans_data.new_master_ips = [node["ip"] for node in global_data["nodes"][role]]
            elif role == ESRoleEnum.CLIENT:
                trans_data.new_client_ips = [node["ip"] for node in global_data["nodes"][role]]

        self.log_info(_("获取机器资源成功成功。 {}").format(trans_data))
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class GetEsResourceComponent(Component):
    name = __name__
    code = "get_es_resource"
    bound_service = GetEsResourceService
