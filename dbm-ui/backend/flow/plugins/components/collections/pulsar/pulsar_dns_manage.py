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


class PulsarDnsManageService(BaseService):
    def __get_broker_ips(self, global_data) -> list:
        """
        获取需要添加域名的broker ip list
        """
        exec_ips = [broker["ip"] for broker in global_data["nodes"]["broker"]]
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))

        return exec_ips

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 传入调用结果
        dns_op_type = kwargs["dns_op_type"]
        dns_manage = DnsManage(bk_biz_id=global_data["bk_biz_id"], bk_cloud_id=global_data["bk_cloud_id"])
        if dns_op_type == DnsOpType.CREATE:
            # 兼容 集群创建和扩容 场景
            exec_ips = self.__get_broker_ips(global_data=global_data)
            if not exec_ips:
                return False
            add_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in exec_ips]
            # 添加域名映射
            result = dns_manage.create_domain(instance_list=add_instance_list, add_domain_name=kwargs["domain_name"])

        elif dns_op_type == DnsOpType.RECYCLE_RECORD:
            # 集群缩容场景
            exec_ips = self.__get_broker_ips(global_data=global_data)
            if not exec_ips:
                return False
            delete_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in exec_ips]
            result = dns_manage.remove_domain_ip(domain=global_data["domain"], del_instance_list=delete_instance_list)

        elif dns_op_type == DnsOpType.CLUSTER_DELETE:
            # 集群下架场景 清理域名
            result = dns_manage.delete_domain(cluster_id=global_data["cluster_id"])
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


class PulsarDnsManageComponent(Component):
    name = __name__
    code = "pulsar_dns_manage"
    bound_service = PulsarDnsManageService
