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

import backend.flow.utils.surrealdb.surrealdb_context_dataclass as flow_context
from backend.flow.consts import DnsOpType
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("flow")


class SurrealDBDnsManageService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        result = False
        clb_detail = trans_data.clb_detail
        trans_data.domain = kwargs["domain_name"]
        dns_op_type = kwargs["dns_op_type"]
        dns_manage = DnsManage(bk_biz_id=global_data["bk_biz_id"], bk_cloud_id=kwargs["bk_cloud_id"])

        if dns_op_type == DnsOpType.CREATE:
            vip = clb_detail.get("LoadBalancerVips")
            if not vip:
                self.log_error(_("CLB详情缺少LoadBalancerVips"))
                return False
            add_instance_list = [f"{vip}#{kwargs['dns_op_exec_port']}"]
            result = dns_manage.create_domain(instance_list=add_instance_list, add_domain_name=kwargs["domain_name"])
            data.outputs["trans_data"] = trans_data
        elif dns_op_type == DnsOpType.CLUSTER_DELETE:
            result = dns_manage.delete_domain(cluster_id=global_data["cluster_id"])
        else:
            self.log_error(_("无法适配到传入的域名处理类型,请联系系统管理员:{}").format(dns_op_type))
            return result
        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class SurrealDBDnsManageComponent(Component):
    name = __name__
    code = "surrealdb_dns_manage"
    bound_service = SurrealDBDnsManageService
