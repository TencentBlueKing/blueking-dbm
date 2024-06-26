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

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.user import user
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

logger = logging.getLogger("flow")


class MongoUserFlow(object):
    """MongoDB创建业务用户flow"""

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

    def multi_cluster_user_flow(self, create: bool):
        """
        multi replicaset create/delete user流程
        create True：创建
        create False：删除
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 创建/删除用户子流程并行
        for info in self.data["infos"]:
            sub_pipelines = []
            for cluster_id in info["cluster_ids"]:
                sub_pipline = user(
                    root_id=self.root_id,
                    ticket_data=self.data,
                    sub_kwargs=self.get_kwargs,
                    cluster_id=cluster_id,
                    create=create,
                    info=info,
                )
                sub_pipelines.append(sub_pipline)
            pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 运行流程
        pipeline.run_pipeline()
