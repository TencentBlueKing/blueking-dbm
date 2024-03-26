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

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ClusterStoragesClientConnsKillAtomJob
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisStoragesClientConnsKillSceneFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        """
        self.root_id = root_id
        self.data = data

    def batch_clusters_storages_cli_conns_kill(self):
        """
        批量执行 集群存储节点 客户端连接 kill
        self.data (Dict):
        {
          "bk_biz_id":"",
          "cluster_ids":[1,2,3],
        }
        """

        # 先cluster_id去重
        cluster_ids_set = set()
        for cluster_id in self.data["cluster_ids"]:
            cluster_ids_set.add(cluster_id)
        clusters: list[Cluster] = []
        for cluster_id in cluster_ids_set:
            try:
                cluster = Cluster.objects.get(id=cluster_id)
                clusters.append(cluster)
            except Cluster.DoesNotExist:
                raise Exception("cluster_id {} not exist".format(cluster_id))

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

        sub_pipelines = []
        for cluster in clusters:
            params = {
                "cluster_id": cluster.id,
            }
            sub_builder = ClusterStoragesClientConnsKillAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
