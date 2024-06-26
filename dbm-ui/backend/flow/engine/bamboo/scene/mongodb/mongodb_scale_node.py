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

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_increase_node import cluster_increase_node
from backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_reduce_node import cluster_reduce_node
from backend.flow.engine.bamboo.scene.mongodb.sub_task.replicaset_reduce_node import replicaset_reduce_node
from backend.flow.engine.bamboo.scene.mongodb.sub_task.replicaset_set_increase_node import replicaset_set_increase_node
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

logger = logging.getLogger("flow")


class MongoScaleNodeFlow(object):
    """MongoDB变更shard节点数flow"""

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

    def multi_cluster_scale_node_flow(self, increase: bool):
        """
        multi cluster scale node流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines = []
        # 复制集增减节点——子流程并行
        if ClusterType.MongoReplicaSet.value in self.data["infos"]:
            for replicaset_set in self.data["infos"][ClusterType.MongoReplicaSet.value]:
                if increase:
                    sub_pipline = replicaset_set_increase_node(
                        root_id=self.root_id,
                        ticket_data=self.data,
                        sub_kwargs=self.get_kwargs,
                        info=replicaset_set,
                    )
                    sub_pipelines.append(sub_pipline)
                else:
                    sub_pipline = replicaset_reduce_node(
                        root_id=self.root_id,
                        ticket_data=self.data,
                        sub_kwargs=self.get_kwargs,
                        info=replicaset_set,
                        cluster=False,
                    )
                    sub_pipelines.append(sub_pipline)
        # cluster的shard增减节点——子流程并行
        if ClusterType.MongoShardedCluster.value in self.data["infos"]:
            for cluster in self.data["infos"][ClusterType.MongoShardedCluster.value]:
                if increase:
                    sub_pipline = cluster_increase_node(
                        root_id=self.root_id, ticket_data=self.data, sub_kwargs=self.get_kwargs, info=cluster
                    )
                else:
                    sub_pipline = cluster_reduce_node(
                        root_id=self.root_id, ticket_data=self.data, sub_kwargs=self.get_kwargs, info=cluster
                    )
                sub_pipelines.append(sub_pipline)

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 运行流程
        pipeline.run_pipeline()
