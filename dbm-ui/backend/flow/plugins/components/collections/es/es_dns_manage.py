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
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import DnsOpType, ESRoleEnum, InstanceStatus
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("flow")


class EsDnsManageService(BaseService):
    """
    定义es集群域名管理的活动节点,目前只支持添加域名、删除域名
    """

    def __init__(self, name=None):
        super(EsDnsManageService, self).__init__(name)
        self.order_list = [
            ESRoleEnum.CLIENT.value,
            ESRoleEnum.HOT.value,
            ESRoleEnum.COLD.value,
            ESRoleEnum.MASTER.value,
        ]
        self.es_role_to_instance_role_map = {
            ESRoleEnum.CLIENT.value: InstanceRole.ES_CLIENT.value,
            ESRoleEnum.HOT.value: InstanceRole.ES_DATANODE_HOT.value,
            ESRoleEnum.COLD.value: InstanceRole.ES_DATANODE_COLD.value,
            ESRoleEnum.MASTER.value: InstanceRole.ES_DATANODE_COLD.value,
        }

    def __get_exec_ips(self, global_data) -> list:
        """
        获取需要执行的ip list
        """
        exec_ips = []
        # 选为域名映射节点的优先级：client > hot > cold > master

        for role in self.order_list:
            if global_data["nodes"].get(role, []):
                for node in global_data["nodes"][role]:
                    exec_ips.append(node["ip"])
                break

        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))

        return exec_ips

    def __get_ips_by_es_role(self, global_data: dict, role: str) -> list:
        cluster = Cluster.objects.get(id=global_data["cluster_id"])
        instances = StorageInstance.objects.filter(
            cluster=cluster,
            status=InstanceStatus.RUNNING.value,
            instance_role=self.es_role_to_instance_role_map[role],
        )
        return [m.machine.ip for m in instances]

    def __get_all_ips_in_ticket(self, global_data: dict) -> list:
        return [node["ip"] for role_nodes in global_data["nodes"].values() for node in role_nodes]

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 传入调用结果
        dns_op_type = kwargs["dns_op_type"]
        dns_manage = DnsManage(bk_cloud_id=kwargs["bk_cloud_id"], bk_biz_id=global_data["bk_biz_id"])
        result = False
        if dns_op_type == DnsOpType.CREATE:
            # 添加域名映射,适配集群申请，单独添加域名的场景
            exec_ips = self.__get_exec_ips(global_data=global_data)
            if not exec_ips:
                return False

            add_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in exec_ips]
            result = dns_manage.create_domain(instance_list=add_instance_list, add_domain_name=global_data["domain"])
        elif dns_op_type == DnsOpType.UPDATE:
            # 更新域名
            cluster = Cluster.objects.get(id=global_data["cluster_id"])
            # 获取域名映射的IP
            dns_details = dns_manage.get_domain(domain_name=cluster.immute_domain)
            dns_ips = [item["ip"] for item in dns_details]
            # 先加入，后删除
            for role in self.order_list:
                role_ips = self.__get_ips_by_es_role(global_data, role)
                diff_set = set(role_ips) - set(dns_ips)
                # 将当前角色节点与域名的差集加入域名
                if diff_set:
                    add_instance_list = [f"{ip}#{global_data['http_port']}" for ip in diff_set]
                    dns_manage.create_domain(instance_list=add_instance_list, add_domain_name=cluster.immute_domain)
                # 将低优先级的节点(域名的IP与当前优先级节点IP的差集)从域名中剔除
                if role_ips:
                    del_set = set(dns_ips) - set(role_ips)
                    if del_set:
                        del_instance_list = [f"{ip}#{global_data['http_port']}" for ip in del_set]
                        dns_manage.remove_domain_ip(domain=cluster.immute_domain, del_instance_list=del_instance_list)
                    # 有高优先级角色的节点存在，退出，不需要把更低优先级角色的节点加入域名
                    break
            result = True
        elif dns_op_type == DnsOpType.CLUSTER_DELETE:
            # 清理域名
            result = dns_manage.delete_domain(cluster_id=global_data["cluster_id"])
        elif dns_op_type == DnsOpType.RECYCLE_RECORD:
            # 修改域名映射（如果某个角色的机器被全部下掉，要修改域名到更低优先级角色的机器上）
            dns_details = dns_manage.get_domain(domain_name=kwargs["domain_name"])
            # 域名映射的IP
            dns_ips = [item["ip"] for item in dns_details]
            # 下架的IP
            shrink_ips = self.__get_all_ips_in_ticket(global_data)
            # 差集为0，使用更低优先级角色的节点作为域名映射
            # 先加入域名，再剔除下架节点
            if len(set(dns_ips) - set(shrink_ips)) == 0:
                for role in self.order_list:
                    role_ips = self.__get_ips_by_es_role(global_data, role)
                    if len(set(role_ips) - set(shrink_ips)) > 0:
                        # 加入域名
                        add_dns_ips = set(role_ips) - set(shrink_ips)
                        add_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in add_dns_ips]
                        dns_manage.create_domain(
                            instance_list=add_instance_list, add_domain_name=kwargs["domain_name"]
                        )
                        break
            del_ips = list(set(dns_ips) & set(shrink_ips))
            del_instance_list = [f"{ip}#{kwargs['dns_op_exec_port']}" for ip in del_ips]
            if del_instance_list:
                result = dns_manage.remove_domain_ip(domain=kwargs["domain_name"], del_instance_list=del_instance_list)
            else:
                result = True
        else:
            self.log_error(_("无法适配到传入的域名处理类型,请联系系统管理员:{}").format(dns_op_type))
            return False

        self.log_info("DNS operation {} result: {}".format(dns_op_type, result))
        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class EsDnsManageComponent(Component):
    name = __name__
    code = "es_dns_manage"
    bound_service = EsDnsManageService
