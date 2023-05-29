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
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class HdfsDnsManageService(BaseService):
    """
    定义HDFS集群域名管理的活动节点,目前只支持添加域名、删除域名
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        result = False

        # 传入调用结果
        dns_op_type = kwargs["dns_op_type"]
        dns_manage = DnsManage(bk_biz_id=global_data["bk_biz_id"], bk_cloud_id=kwargs["bk_cloud_id"])
        if dns_op_type == DnsOpType.CREATE:
            # 兼容 集群创建和扩容 场景
            if "new_dn_ips" not in global_data:
                exec_ips = global_data["dn_ips"]
            else:
                exec_ips = global_data["new_dn_ips"]
            # 添加域名映射,适配集群申请，单独添加域名的场景
            if not exec_ips:
                self.log_error(_("获取DNS操作IP为空"))
                return False

            add_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in exec_ips]
            result = dns_manage.create_domain(instance_list=add_instance_list, add_domain_name=global_data["domain"])

        elif dns_op_type == DnsOpType.UPDATE:
            # 兼容 缩容/替换场景
            if global_data["ticket_type"] == TicketType.HDFS_SCALE_UP.value:
                exec_ips = global_data["new_dn_ips"]
                add_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in exec_ips]
                result = dns_manage.create_domain(
                    instance_list=add_instance_list, add_domain_name=global_data["domain"]
                )
            if global_data["ticket_type"] == TicketType.HDFS_SHRINK.value:
                exec_ips = global_data["del_dn_ips"]
                del_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in exec_ips]
                result = dns_manage.remove_domain_ip(domain=global_data["domain"], del_instance_list=del_instance_list)

        elif dns_op_type == DnsOpType.CLUSTER_DELETE:
            # 清理域名
            result = dns_manage.delete_domain(cluster_id=global_data["cluster_id"])
        else:
            self.log_error(_("无法适配到传入的域名处理类型,请联系系统管理员:{}").format(dns_op_type))
            return False

        self.log_info("DNS operation {} successfully".format(dns_op_type))
        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class HdfsDnsManageComponent(Component):
    name = __name__
    code = "hdfs_dns_manage"
    bound_service = HdfsDnsManageService
