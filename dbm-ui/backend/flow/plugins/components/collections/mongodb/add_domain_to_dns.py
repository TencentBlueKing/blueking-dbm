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

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils import dns_manage

logger = logging.getLogger("json")


class ExecAddDomainToDnsOperation(BaseService):
    """
    NameServiceCreate服务
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行创建名字服务功能的函数
        global_data 单据全局变量，格式字典
        kwargs 私有变量
        """

        # 从流程节点中获取变量
        kwargs = data.get_one_of_inputs("kwargs")

        # 写入dns
        for domain in kwargs["domains"]:
            result = dns_manage.DnsManage(
                bk_biz_id=kwargs["bk_biz_id"], bk_cloud_id=kwargs["bk_cloud_id"]
            ).create_domain(instance_list=domain["instance_list"], add_domain_name=domain["domain"])
            if not result:
                self.log_error(
                    "add domain:{} with instance:{} to dns fail".format(domain["domain"], domain["instance_list"])
                )
                return False
        self.log_info("add domain to dns successfully")
        return True

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExecAddDomainToDnsOperationComponent(Component):
    """
    ExecAddDomainToDnsOperation组件
    """

    name = __name__
    code = "add_domain_to_dns_operation"
    bound_service = ExecAddDomainToDnsOperation
