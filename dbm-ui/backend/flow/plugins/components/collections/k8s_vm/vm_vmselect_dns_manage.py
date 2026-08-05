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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.k8s_vm.k8s_vm_context_dataclass as flow_context
from backend.flow.consts import DnsOpType
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.k8s_vm.consts import VMSELECT_PORT

logger = logging.getLogger("flow")


class VmVmselectDnsManageService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        if kwargs["dns_op_type"] != DnsOpType.CREATE:
            self.log_error(_("无法适配到传入的域名处理类型,请联系系统管理员:{}").format(kwargs["dns_op_type"]))
            return False

        clb_detail = trans_data.vmselect_clb_detail
        vip = clb_detail.get("LoadBalancerVips")
        if not vip:
            self.log_error(_("vmselect CLB详情缺少LoadBalancerVips"))
            return False

        trans_data.vmselect_domain = kwargs["domain_name"]
        dns_manage = DnsManage(bk_biz_id=global_data["bk_biz_id"], bk_cloud_id=kwargs["bk_cloud_id"])
        result = dns_manage.create_domain(
            instance_list=[f"{vip}#{VMSELECT_PORT}"], add_domain_name=kwargs["domain_name"]
        )
        data.outputs["trans_data"] = trans_data
        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class VmVmselectDnsManageComponent(Component):
    name = __name__
    code = "vm_vmselect_dns_manage"
    bound_service = VmVmselectDnsManageService
