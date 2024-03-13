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
from collections import defaultdict
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.mongodb.mongodb_dataclass as flow_context
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mongodb.mongodb_repo import MongoNodeWithLabel

logger = logging.getLogger("json")


class ExecPrepareInstanceInfoOperation(BaseService):
    """
    PrepareInstanceInfo
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行创建名字服务功能的函数
        global_data 单据全局变量，格式字典
        kwargs 私有变量
        """

        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        ip_list = kwargs["host_list"]
        bk_cloud_id = int(kwargs["bk_cloud_id"])
        instances = MongoNodeWithLabel.from_hosts(ip_list, bk_cloud_id=bk_cloud_id)

        result = MongoNodeWithLabel.append_password(instances, "monitor")
        logger.debug("append_password result:{}".format(result))
        # group by ip
        instances_by_ip = defaultdict(list)
        for instance in instances:
            instances_by_ip[instance.ip].append(instance)

        trans_data.set("instances_by_ip", instances_by_ip)
        data.outputs["trans_data"] = trans_data
        self.log_info("get instances {}".format(instances_by_ip))
        return True

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExecPrepareInstanceInfoOperationComponent(Component):
    """
    ExecPrepareInstanceInfoOperation组件 从meta中获得相关ip的instance信息
    """

    name = __name__
    code = "prepare_instance_info_operation"
    bound_service = ExecPrepareInstanceInfoOperation
