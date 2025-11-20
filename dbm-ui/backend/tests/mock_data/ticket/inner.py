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

import importlib
from typing import Any


def mock_inner_flow_run(self) -> Any:
    """
    Mock版本的InnerFlow._run方法
    参考原始_run逻辑，但使用execute_pipeline_test来执行测试验证
    """
    # 刷新数据库对象
    self.flow_obj.refresh_from_db()

    # 获取必要参数
    root_id = self.flow_obj.flow_obj_id
    flow_details = self.flow_obj.details

    # 从controller_info中提取流程信息
    controller_info = flow_details["controller_info"]

    # 动态导入controller模块和类
    controller_module = importlib.import_module(controller_info["module"])
    controller_class = getattr(controller_module, controller_info["class_name"])
    controller_inst = controller_class(root_id=root_id, ticket_data=flow_details["ticket_data"])
    return getattr(controller_inst, controller_info["func_name"])()
