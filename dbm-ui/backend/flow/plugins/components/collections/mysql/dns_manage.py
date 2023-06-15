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
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("flow")


class MySQLDnsManageService(BaseService):
    """
    定义mysql集群域名管理的活动节点,目前只支持添加域名、删除域名
    同时支持ip从上下文中传入，或者从活动节点的私用变量传入来拼装参数
    同时支持跨云管理，根据传入的 kwargs["bk_cloud_id"]来执行
    """

    def __get_exec_ips(self, kwargs, trans_data) -> list:
        """
        获取需要执行的ip list
        """
        # 拼接节点执行ip所需要的信息，ip信息统一用list处理拼接
        if kwargs.get("get_trans_data_ip_var"):
            exec_ips = self.splice_exec_ips_list(pool_ips=getattr(trans_data, kwargs["get_trans_data_ip_var"]))
        else:
            exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])

        return exec_ips

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        # 传入调用结果
        dns_op_type = kwargs["dns_op_type"]
        dns_manage = DnsManage(bk_biz_id=global_data["bk_biz_id"], bk_cloud_id=kwargs["bk_cloud_id"])
        result = False
        if dns_op_type == DnsOpType.CREATE:
            # 添加域名映射,适配集群申请，单独添加域名的场景
            exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
            if not exec_ips:
                self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))
                return False

            add_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in exec_ips]
            result = dns_manage.create_domain(
                instance_list=add_instance_list, add_domain_name=kwargs["add_domain_name"]
            )

        elif dns_op_type == DnsOpType.RECYCLE_RECORD:
            # 回收实例对应的域名记录，适配实例下架场景
            exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
            if not exec_ips:
                self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))
                return False

            delete_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in exec_ips]
            result = dns_manage.recycle_domain_record(del_instance_list=delete_instance_list)

        elif dns_op_type == DnsOpType.CLUSTER_DELETE:
            # 回收集群所有的域名映射，适配集群回收场景
            result = dns_manage.delete_domain(
                cluster_id=kwargs["delete_cluster_id"],
                is_only_delete_slave_domain=kwargs["is_only_delete_slave_domain"],
            )

        elif dns_op_type == DnsOpType.UPDATE:
            # 更新域名方法
            # todo 后续添加变更域名映射的逻辑
            pass
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


class MySQLDnsManageComponent(Component):
    name = __name__
    code = "mysql_dns_manage"
    bound_service = MySQLDnsManageService
