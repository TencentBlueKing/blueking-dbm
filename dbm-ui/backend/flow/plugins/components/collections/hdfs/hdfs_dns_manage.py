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

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DnsOpType, HdfsRoleEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.hdfs.consts import V2_FLOW_VERSION_KEY
from backend.flow.utils.hdfs.hdfs_flow_data_initializer import get_node_ips_in_ticket_by_role
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
            # 兼容V2版本
            if V2_FLOW_VERSION_KEY in global_data["db_version"]:
                for ip, domain in global_data["nn_domain"].items():
                    nn_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}"]
                    nn_result = dns_manage.create_domain(instance_list=nn_instance_list, add_domain_name=domain)
                    if not nn_result:
                        self.log_error(_("添加NN域名失败, ip: {}, domain: {}").format(ip, domain))
            # 统一获取接入主域名的DN节点IP，尚未兼容替换单据
            exec_ips = get_node_ips_in_ticket_by_role(global_data, HdfsRoleEnum.DataNode.value)
            # 使用旧逻辑获取DN节点IP
            if not exec_ips:
                if "new_dn_ips" not in global_data:
                    exec_ips = global_data["dn_ips"]
                else:
                    exec_ips = global_data["new_dn_ips"]

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
            if V2_FLOW_VERSION_KEY in global_data["db_version"]:
                cluster = Cluster.objects.get(id=global_data["cluster_id"])
                nn_ips = list(
                    cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_NAME_NODE).values_list(
                        "machine__ip", flat=True
                    )
                )
                del_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in nn_ips]
                del_result = dns_manage.recycle_domain_record(del_instance_list=del_instance_list)
                if not del_result:
                    self.log_error(_("回收NN域名记录失败, del_instance_list: {}").format(del_instance_list))
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
