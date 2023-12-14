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
import base64
import logging
import random
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import JobApi
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs

logger = logging.getLogger("flow")


class DNSServerSetService(BkJobService):
    """
    定义机器配置DNS服务的节点
    """

    @staticmethod
    def __get_dns_server_list(bk_cloud_id: int, bk_city: str) -> str:
        """
        获取符合条件的dns列表
        """
        choice_dns_list = []
        other_city_dns_list = []
        same_city_dns_list = []
        all_dns_server = DBExtension.get_extension_in_cloud(bk_cloud_id, ExtensionType.DNS)
        for dns_server in all_dns_server:
            details = dns_server.details
            if not details["is_access"]:
                continue

            if details["bk_city"] == bk_city:
                same_city_dns_list.append(details["ip"])
            else:
                other_city_dns_list.append(details["ip"])

        same_city_dns_num = len(same_city_dns_list)
        other_city_dns_num = len(other_city_dns_list)
        total_num = 3
        # 这里可能会存在same_city_dns_num+other_city_dns_num < 3的情况
        # 默认配置3个，如果不满足3个的场景，才减少配置DNS数量
        if same_city_dns_num + other_city_dns_num < 3:
            total_num = same_city_dns_num + other_city_dns_num

        # 如果当前城市DNS节点小于2个，剩下的从其他云区域中选取
        if same_city_dns_num <= 2:
            choice_dns_list = same_city_dns_list
            other_city_dns_num = total_num - same_city_dns_num
        # 如果当前城市DNS节点大于2个，优先选取2个同城的
        else:
            choice_dns_list = random.sample(same_city_dns_list, 2)
            other_city_dns_num = total_num - 2
        choice_dns_list = choice_dns_list + random.sample(other_city_dns_list, other_city_dns_num)
        result_str = "#DNS for GCS START"
        for dns_ip in choice_dns_list:
            result_str += "\r\nnameserver " + dns_ip
        result_str += "\r\noptions  timeout:1\r\n#DNS for GCS END"
        return result_str

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]
        cluster = kwargs["cluster"]

        exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))
            return False
        target_ip_info = [{"bk_cloud_id": cluster["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        self.log_info("{} exec {}".format(target_ip_info, node_name))

        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        dns_server_config = self.__get_dns_server_list(cluster["bk_cloud_id"], cluster["bk_city"])

        # 强制模式
        if cluster["force"]:
            shell_command = "echo '{}' > /etc/resolv.conf".format(dns_server_config)
        # 非强制模式
        else:
            shell_command = "{} && echo '{}' > /etc/resolv.conf || {} ".format(
                "[ `cat /etc/resolv.conf | grep nameserver | sed '/^$/d' | sed '/^#/d' | wc -l` == '0' ]",
                dns_server_config,
                "cat /etc/resolv.conf",
            )

        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": str(base64.b64encode(shell_command.encode("utf-8")), "utf-8"),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }

        self.log_info("[{}] ready start task with body {}".format(node_name, body))
        resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class DNSServerSetComponent(Component):
    name = __name__
    code = "dns_server_config"
    bound_service = DNSServerSetService
