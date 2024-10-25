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
from backend.flow.consts import MongoDBClusterRole
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_monogs_autofix import mongos_autofix
from backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_shard_autofix import shard_autofix
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

logger = logging.getLogger("flow")


class MongoClusterAutofixFlow(object):
    """MongoDB分片集群自愈flow"""

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

    def cluster_autofix_flow(self):
        """
        分片集群自愈流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 获取mongos mongo_config mongodb自愈信息
        autofix_info = self.data["infos"][ClusterType.MongoShardedCluster.value][0]
        autofix_mongos = autofix_info["mongos"]
        autofix_mongo_config = autofix_info["mongo_config"]
        autofix_mongodb = autofix_info["mongodb"]

        # mongos自愈并行
        if autofix_mongos:
            sub_pipelines = []
            for mongos_info_by_ip in autofix_mongos:
                for mongos_instance in mongos_info_by_ip["instances"]:
                    self.get_kwargs.db_instance = mongos_instance
                    sub_pipeline = mongos_autofix(
                        root_id=self.root_id,
                        ticket_data=self.data,
                        sub_sub_kwargs=self.get_kwargs,
                        info=mongos_info_by_ip,
                    )
                    sub_pipelines.append(sub_pipeline)
            pipeline.add_parallel_sub_pipeline(sub_pipelines)

        # mongo_config mongodb自愈并行
        sub_pipelines = []
        # 替换config 以ip为维度
        for config_info_by_ip in autofix_mongo_config:
            sub_pipeline = shard_autofix(
                root_id=self.root_id,
                ticket_data=self.data,
                sub_kwargs=self.get_kwargs,
                info=config_info_by_ip,
                cluster_role=MongoDBClusterRole.ConfigSvr.value,
            )
            sub_pipelines.append(sub_pipeline)
            # 替换shard 以ip为维度
        for shard_info_by_ip in autofix_mongodb:
            sub_pipeline = shard_autofix(
                root_id=self.root_id,
                ticket_data=self.data,
                sub_kwargs=self.get_kwargs,
                info=shard_info_by_ip,
                cluster_role=MongoDBClusterRole.ShardSvr.value,
            )
            sub_pipelines.append(sub_pipeline)
        if sub_pipelines:
            pipeline.add_parallel_sub_pipeline(sub_pipelines)

        # 运行流程
        pipeline.run_pipeline()
