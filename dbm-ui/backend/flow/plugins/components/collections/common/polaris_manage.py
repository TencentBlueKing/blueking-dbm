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

from backend.flow.consts import DnsOpType
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.polaris_manage import GetPolarisManageByName

logger = logging.getLogger("flow")


class RedisPolarisManageService(BaseService):
    """
    定义集群Polaris管理的活动节点
    """

    def __get_exec_ips(self, kwargs, trans_data) -> list:
        """
        获取需要执行的ip list
        """
        # 拼接节点执行ip所需要的信息，ip信息统一用list处理拼接
        if kwargs["get_trans_data_ip_var"]:
            exec_ips = self.splice_exec_ips_list(
                ticket_ips=kwargs["exec_ip"], pool_ips=getattr(trans_data, kwargs["get_trans_data_ip_var"])
            )
        else:
            exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])

        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))

        return exec_ips

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        # 传入调用结果
        dns_op_type = kwargs["polaris_op_type"]
        polaris_manager = GetPolarisManageByName(kwargs["servicename"])

        if dns_op_type == DnsOpType.CREATE:
            # 添加polaris映射,proxy扩容场景
            exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
            if not exec_ips:
                return False

            add_instance_list = [f"{ip}:{kwargs['polaris_op_exec_port']}" for ip in exec_ips]
            result = polaris_manager.add_polaris_rs(instance_list=add_instance_list)
        elif dns_op_type == DnsOpType.RECYCLE_RECORD:
            # 删除polaris映射,proxy缩容场景
            exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
            if not exec_ips:
                self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))
                return False

            delete_instance_list = [f"{ip}:{kwargs['polaris_op_exec_port']}" for ip in exec_ips]
            result = polaris_manager.del_polaris_rs(instance_list=delete_instance_list)
        elif dns_op_type == DnsOpType.CLUSTER_DELETE:
            # 删除polaris, 集群下架场景
            result = polaris_manager.deregiste_polaris()
        else:
            self.log_error(_("无法适配到传入的域名处理类型,请联系系统管理员:{}").format(dns_op_type))
            return False

        self.log_info("successfully")
        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="command result", key="result", type="str")]


class RedisPolarisManageComponent(Component):
    name = __name__
    code = "polaris_dns_manage"
    bound_service = RedisPolarisManageService
