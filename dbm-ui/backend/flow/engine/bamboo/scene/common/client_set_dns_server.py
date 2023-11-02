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
import logging.config
import random
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.consts import WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.check_resolv_conf import (
    CheckResolvConfComponent,
    ExecuteShellScriptComponent,
)
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.utils.common_act_dataclass import DNSContext
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs

logger = logging.getLogger("flow")


class ClientSetDnsServerFlow(object):
    """
    配置dns
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

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
            details = dns_server.__dict__["details"]
            if not details["is_access"]:
                continue

            if details["bk_city"] == bk_city:
                same_city_dns_list.append(details["ip"])
            else:
                other_city_dns_list.append(details["ip"])

        same_city_dns_num = len(same_city_dns_list)
        other_city_dns_num = len(other_city_dns_list)
        if same_city_dns_num + other_city_dns_num < 3:
            raise Exception("all access dns < 3")

        if same_city_dns_num <= 2:
            choice_dns_list = same_city_dns_list
            other_city_dns_num = 3 - same_city_dns_num
        else:
            choice_dns_list = random.sample(same_city_dns_list, 2)
            other_city_dns_num = 1
        choice_dns_list = choice_dns_list + random.sample(other_city_dns_list, other_city_dns_num)
        result_str = "#DNS for GCS START"
        for dns_ip in choice_dns_list:
            result_str += "\r\nnameserver " + dns_ip
        result_str += "\r\noptions  timeout:1\r\n#DNS for GCS END"
        return result_str

    def client_set_dns_server_flow(self):
        """
        {
            "ticket_type": "SET_DNS_SERVER",
            "created_by":"admin"
            "bk_cloud_id":0,
            "bk_biz_id":xxx,
            "hosts":[],
            "bk_city": "深圳",
            "type": "qcloud",
            "force": 0
          }
                配置dns服务：
                    1、获取符合条件的dns列表
                    2、检查机器是否已配置dns服务
                    3、下发任务，配置dns
                    4、测试是否配置成功
        """
        dns_server_config = self.__get_dns_server_list(self.data["bk_cloud_id"], self.data["bk_city"])

        client_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = DNSContext.__name__
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {}
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

        client_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        sub_pipelines = []
        for ip in self.data["hosts"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            act_kwargs.exec_ip = ip
            act_kwargs.write_op = WriteContextOpType.APPEND.value
            act_kwargs.cluster[
                "shell_command"
            ] = """
               d=`cat /etc/resolv.conf | sed "/^$/d" | sed "/^#/d" |awk 1 ORS=' '`
               echo "<ctx>{\\\"data\\\":\\\"${d}\\\"}</ctx>"
            """
            sub_pipeline.add_act(
                act_name=_("获取/etc/resolv.conf: {}").format(ip),
                act_component_code=ExecuteShellScriptComponent.code,
                kwargs=asdict(act_kwargs),
                write_payload_var="resolv_content",
            )

            #  非强制情况下，需要检查配置
            if not self.data["force"]:
                sub_pipeline.add_act(
                    act_name=_("检查/etc/resolv.conf: {}").format(ip),
                    act_component_code=CheckResolvConfComponent.code,
                    kwargs=asdict(act_kwargs),
                    splice_payload_var="resolv_content",
                )

            # 执行job写入配置
            act_kwargs.cluster["shell_command"] = "echo '{}' > /etc/resolv.conf".format(dns_server_config)
            sub_pipeline.add_act(
                act_name=_("写入/etc/resolv.conf: {}").format(ip),
                act_component_code=ExecuteShellScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # TODO 检查是否能解析是否成功

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}配置dns服务器").format(ip)))
        client_pipeline.add_parallel_sub_pipeline(sub_pipelines)

        client_pipeline.run_pipeline()
