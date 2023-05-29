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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import Service

from backend.flow.consts import DnsOpType
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.dns_manage import DnsManage


class PulsarZkDnsManageService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        result = True
        # 传入调用结果
        dns_op_type = kwargs["dns_op_type"]
        dns_manage = DnsManage(bk_biz_id=global_data["bk_biz_id"], bk_cloud_id=global_data["bk_cloud_id"])
        if dns_op_type == DnsOpType.CREATE:
            for ip, domain in kwargs["zk_host_map"].items():
                instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}"]
                # 添加域名映射
                result = dns_manage.create_domain(instance_list=instance_list, add_domain_name=domain)

        elif dns_op_type == DnsOpType.UPDATE:
            # 集群替换场景
            domain = kwargs["zk_host_map"][kwargs["old_zk_ip"]]
            old_instance = f"{kwargs['old_zk_ip']}#{kwargs['dns_op_exec_port']}"
            new_instance = f"{kwargs['new_zk_ip']}#{kwargs['dns_op_exec_port']}"
            result = dns_manage.update_domain(
                old_instance=old_instance, new_instance=new_instance, update_domain_name=domain
            )

        elif dns_op_type == DnsOpType.CLUSTER_DELETE:
            # 集群下架场景 清理域名
            for ip, domain in kwargs["zk_host_map"].items():
                instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}"]
                result = dns_manage.remove_domain_ip(del_instance_list=instance_list, domain=domain)
        else:
            self.log_error(_("无法适配到传入的域名处理类型,请联系系统管理员:{}").format(dns_op_type))
            return False

        self.log_info(f"DNS operation {dns_op_type} successfully")
        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


# support multiple domains
class PulsarZkDnsManageComponent(Component):
    name = __name__
    code = "pulsar_zk_dns_manage"
    bound_service = PulsarZkDnsManageService
