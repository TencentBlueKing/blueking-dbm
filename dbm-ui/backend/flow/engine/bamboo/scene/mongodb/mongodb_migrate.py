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
from backend.flow.engine.bamboo.scene.mongodb.sub_task.migrate_meta import cluster_migrate
from backend.flow.engine.bamboo.scene.mongodb.sub_task.multi_replicaset_migrate_meta import multi_replicaset_migrate
from backend.flow.utils.mongodb.mongodb_migrate_dataclass import MigrateActKwargs

logger = logging.getLogger("flow")


class MongoDBMigrateMetaFlow(object):
    """元数据迁移flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        self.root_id = root_id
        self.data = data
        self.get_kwargs = MigrateActKwargs()
        self.get_kwargs.payload = data
        self.get_kwargs.bk_biz_id = data.get("bk_biz_id")

    def multi_cluster_migrate_flow(self):
        """
        cluster migrate流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 副本集与分片集群并行
        # 副本集子流程串行
        sub_pipelines = []
        if self.data["MongoReplicaSet"]:
            self.get_kwargs.multi_replicaset_info = self.data["MongoReplicaSet"]
            sub_pipline = multi_replicaset_migrate(
                root_id=self.root_id,
                ticket_data=self.data,
                sub_kwargs=self.get_kwargs,
            )
            sub_pipelines.append(sub_pipline)
        # 分片集群并行
        for cluster_info in self.data["MongoShardedCluster"]:
            self.get_kwargs.source_cluster_info = cluster_info
            sub_pipline = cluster_migrate(
                root_id=self.root_id,
                ticket_data=self.data,
                sub_kwargs=self.get_kwargs,
                cluster=True,
            )
            sub_pipelines.append(sub_pipline)
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 运行流程
        pipeline.run_pipeline()
