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
from backend.flow.utils.clb_manage import get_clb_by_ip

logger = logging.getLogger("flow")


class RedisClbManageService(BaseService):
    """
    定义集群CLB管理的活动节点
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
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        # 传入调用结果
        dns_op_type = kwargs["clb_op_type"]
        clb_manager = get_clb_by_ip(kwargs["clb_ip"])

        if dns_op_type == DnsOpType.CREATE:
            # 添加CLB映射,proxy扩容场景
            exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
            if not exec_ips:
                self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))
                return False

            add_instance_list = [f"{ip}:{kwargs['clb_op_exec_port']}" for ip in exec_ips]
            result = clb_manager.add_clb_rs(instance_list=add_instance_list)
        elif dns_op_type == DnsOpType.RECYCLE_RECORD:
            # 删除CLB映射,proxy缩容场景
            exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
            if not exec_ips:
                self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))
                return False

            delete_instance_list = [f"{ip}:{kwargs['clb_op_exec_port']}" for ip in exec_ips]
            result = clb_manager.del_clb_rs(instance_list=delete_instance_list)
        elif dns_op_type == DnsOpType.CLUSTER_DELETE:
            # 删除CLB,集群下架场景
            result = clb_manager.deregiste_clb()
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


class RedisClbManageComponent(Component):
    name = __name__
    code = "clb_dns_manage"
    bound_service = RedisClbManageService
