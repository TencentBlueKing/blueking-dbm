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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

logger = logging.getLogger("flow")


class MongoReplaceFlow(object):
    """MongoDB整机替换flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        self.root_id = root_id
        self.data = data
        self.get_kwargs = ActKwargs()
        self.get_kwargs.payload = data
        self.get_kwargs.get_file_path()

    def multi_replace_flow(self):
        """
        multi replicaset execute script流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 获取所有的根据主机ip获取cluster信息
        self.get_kwargs.get_hosts_deinstall()

        # 创建整机替换——并行
        acts_list = []
        for cluster_id in self.data["cluster_ids"]:
            kwargs = self.get_kwargs.get_exec_script_kwargs(cluster_id=cluster_id)
            acts_list.append(
                {
                    "act_name": _("MongoDB-{}-整机替换".format(str(cluster_id))),
                    "act_component_code": ExecuteDBActuatorJobComponent.code,
                    "kwargs": kwargs,
                }
            )
        # 运行流程
        pipeline.run_pipeline()
