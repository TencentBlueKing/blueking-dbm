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
from backend.flow.utils.mongodb.mongodb_password import MongoDBPassword

logger = logging.getLogger("json")


class ExecGetPasswordOperation(BaseService):
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
        trans_data = data.get_one_of_inputs("trans_data")
        #
        # if trans_data is None or trans_data == "${trans_data}":
        #     # 表示没有加载上下文内容，则在此添加
        #     trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 从密码服务获取密码
        user_password = {}
        for user in kwargs["users"]:
            result = MongoDBPassword().create_user_password()
            if result["password"] is None:
                self.log_error("user:{} get password fail, error:{}".format(user, result["info"]))
                return False
            user_password[user] = result["password"]
        self.log_info("manager users get password successfully")
        if trans_data is None or trans_data == "${trans_data}":
            data.outputs["trans_data"] = {}
            if kwargs["set_name"]:
                data.outputs["trans_data"][kwargs["set_name"]] = user_password
            else:
                data.outputs["trans_data"] = user_password
        elif isinstance(trans_data, dict):
            if kwargs["set_name"]:
                # users_pwd_info[kwargs["set_name"]] = user_password
                data.outputs["trans_data"][kwargs["set_name"]] = user_password
            else:
                data.outputs["trans_data"] = user_password

        return True

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExecGetPasswordOperationComponent(Component):
    """
    ExecGetPasswordOperation组件
    """

    name = __name__
    code = "get_password_operation"
    bound_service = ExecGetPasswordOperation
