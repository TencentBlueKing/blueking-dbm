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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.consts import WriteContextOpType
from backend.flow.engine.bamboo.scene.common.atom_jobs.set_dns_sub_job import SetDnsAtomJob
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.check_resolv_conf import (
    CheckResolvConfComponent,
    ExecuteShellScriptComponent,
)
from backend.flow.plugins.components.collections.common.dns_server import DNSServerSetComponent
from backend.flow.plugins.components.collections.common.get_common_payload import GetCommonActPayloadComponent
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
        client_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = DNSContext.__name__
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {}
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

        sub_pipelines = []
        for ip in self.data["hosts"]:
            sub_build = SetDnsAtomJob(
                root_id=self.root_id,
                ticket_data=self.data,
                act_kwargs=act_kwargs,
                param={
                    "ip": ip,
                    "bk_cloud_id": self.data["bk_cloud_id"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "bk_city": self.data["bk_city"],
                    "force": self.data["force"],
                },
            )
            sub_pipelines.append(sub_build)
        client_pipeline.add_parallel_sub_pipeline(sub_pipelines)

        client_pipeline.run_pipeline()
