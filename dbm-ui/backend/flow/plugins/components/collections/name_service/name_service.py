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

from backend.db_services.plugin.nameservice import clb, polaris
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("json")


class ExecNameServiceCreateService(BaseService):
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
        name_service_type = kwargs["name_service_type"]

        # 执行功能
        if name_service_type == "clb":
            res = clb.create_lb_and_register_target(kwargs["cluster_id"], kwargs["created_by"])
        elif name_service_type == "polaris":
            res = polaris.create_service_alias_bind_targets(kwargs["cluster_id"], kwargs["created_by"])
        else:
            self.log_error("name_service_type %s not support error!" % name_service_type)
            return False

        # 定义流程节点输出参数值
        data.outputs.result = res
        if res["status"] == 0:
            self.log_info("create %s successfully" % name_service_type)
            return True

        self.log_error("create %s fail, error:%s" % (name_service_type, res["message"]))
        return False

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    # 流程节点输出参数
    def outputs_format(self) -> List:
        return [Service.OutputItem(name="result", key="result", type="dict")]


class ExecNameServiceCreateComponent(Component):
    """
    ExecNameServiceCreate组件
    """

    name = __name__
    code = "name_service_create"
    bound_service = ExecNameServiceCreateService


class ExecNameServiceDeleteService(BaseService):
    """
    NameServiceDelete服务
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行删除名字服务功能的函数
        global_data 单据全局变量，格式字典
        kwargs 私有变量
        """

        # 从流程节点中获取变量
        kwargs = data.get_one_of_inputs("kwargs")
        name_service_type = kwargs["name_service_type"]

        # 执行功能
        if name_service_type == "clb":
            res = clb.deregister_target_and_delete_lb(kwargs["cluster_id"])
        elif name_service_type == "polaris":
            res = polaris.unbind_targets_delete_alias_service(kwargs["cluster_id"])
        else:
            self.log_error("name_service_type %s not support error!" % name_service_type)
            return False

        # 定义流程节点输出参数值
        data.outputs.result = res
        if res["status"] == 0:
            self.log_info("delete %s successfully" % name_service_type)
            return True

        self.log_error("delete %s fail, error:%s" % (name_service_type, res["message"]))
        return False

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    # 流程节点输出参数
    def outputs_format(self) -> List:
        return [Service.OutputItem(name="result", key="result", type="dict")]


class ExecNameServiceDeleteComponent(Component):
    """
    ExecNameServiceDelete组件
    """

    name = __name__
    code = "name_service_delete"
    bound_service = ExecNameServiceDeleteService
