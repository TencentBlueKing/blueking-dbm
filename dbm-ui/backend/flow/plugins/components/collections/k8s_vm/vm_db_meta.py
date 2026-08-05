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

import logging.config
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.k8s_vm.k8s_vm_context_dataclass as flow_context
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.k8s_vm.k8s_vm_db_meta import VmDBMeta

logger = logging.getLogger("flow")


class VmDBMetaService(BaseService):
    """
    根据单据类型来更新cmdb
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        global_data["region"] = trans_data.region_name
        global_data["domain"] = trans_data.vminsert_domain
        global_data["vmselect_domain"] = trans_data.vmselect_domain
        vm_meta = VmDBMeta(ticket_data=global_data)
        result = vm_meta.write()
        trans_data.cluster_id = result["id"]
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class VmDBMetaComponent(Component):
    name = __name__
    code = "vm_db_meta"
    bound_service = VmDBMetaService
