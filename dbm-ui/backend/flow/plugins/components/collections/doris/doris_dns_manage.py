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

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DnsOpType, DorisRoleEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("flow")


class DorisDnsManageService(BaseService):
    """
    定义doris集群域名管理的活动节点,目前只支持添加域名、删除域名
    """

    def __init__(self):
        super(DorisDnsManageService, self).__init__()
        self.order_list = [
            DorisRoleEnum.OBSERVER.value,
            DorisRoleEnum.FOLLOWER.value,
        ]
        self.es_role_to_instance_role_map = {
            DorisRoleEnum.OBSERVER.value: InstanceRole.DORIS_OBSERVER.value,
            DorisRoleEnum.FOLLOWER.value: InstanceRole.DORIS_FOLLOWER.value,
        }

    def __get_dns_exec_ips(self, global_data) -> list:
        """
        获取需要执行的ip list
        """
        exec_ips = []
        # 选为域名映射节点的优先级：observer > follower

        for role in self.order_list:
            if global_data["nodes"].get(role, []):
                for node in global_data["nodes"][role]:
                    exec_ips.append(node["ip"])
                break

        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))

        return exec_ips

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 传入调用结果
        dns_op_type = kwargs["dns_op_type"]
        dns_manage = DnsManage(bk_cloud_id=kwargs["bk_cloud_id"], bk_biz_id=global_data["bk_biz_id"])
        result = False
        if dns_op_type == DnsOpType.CREATE:
            # 添加域名映射,适配集群申请，单独添加域名的场景
            exec_ips = self.__get_dns_exec_ips(global_data=global_data)
            if not exec_ips:
                return False

            add_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in exec_ips]
            result = dns_manage.create_domain(instance_list=add_instance_list, add_domain_name=global_data["domain"])
        if dns_op_type == DnsOpType.UPDATE:
            # 更新域名
            cluster = Cluster.objects.get(id=global_data["cluster_id"])
            # 获取域名映射的IP
            dns_ips = [item["ip"] for item in dns_manage.get_domain(domain_name=cluster.immute_domain)]
            for role in self.order_list:
                role_ips = self.__get_ips_by_es_role(global_data, role)
                diff_set = set(role_ips) - set(dns_ips)
                if diff_set:
                    add_instance_list = [f"{ip}#{global_data['http_port']}" for ip in diff_set]
                    if add_instance_list:
                        dns_manage.create_domain(
                            instance_list=add_instance_list, add_domain_name=cluster.immute_domain
                        )
                # 将低优先级的节点(域名的IP与当前优先级节点IP的差集)从域名中剔除
                if role_ips:
                    del_set = set(dns_ips) - set(role_ips)
                    if del_set:
                        del_instance_list = [f"{ip}#{global_data['http_port']}" for ip in del_set]
                        dns_manage.remove_domain_ip(domain=cluster.immute_domain, del_instance_list=del_instance_list)
                    # 有高优先级角色的节点存在，退出，不需要把更低优先级角色的节点加入域名
                    break
        elif dns_op_type == DnsOpType.CLUSTER_DELETE:
            # 集群下架场景 清理域名
            result = dns_manage.delete_domain(cluster_id=global_data["cluster_id"])
        else:
            self.log_error(_("无法适配到传入的域名处理类型,请联系系统管理员:{}").format(dns_op_type))
            return result

        self.log_info("DNS operation {} result: {}".format(dns_op_type, result))
        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class DorisDnsManageComponent(Component):
    name = __name__
    code = "doris_dns_manage"
    bound_service = DorisDnsManageService
