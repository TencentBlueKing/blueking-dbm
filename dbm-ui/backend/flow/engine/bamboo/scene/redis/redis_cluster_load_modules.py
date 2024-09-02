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

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.db_services.redis.redis_modules.util import get_redis_moudles_detail
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ClusterLoadModulesAtomJob
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_proxy_util import (
    async_get_multi_cluster_info_by_cluster_ids,
    async_multi_clusters_precheck,
)

logger = logging.getLogger("flow")


class RedisClusterLoadModulesSceneFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        data={
            'infos':[
                {
                    "cluster_id":44,
                    "load_modules":["redisbloom","redisjson","rediscell"],
                },
                {
                    "cluster_id":45,
                    "load_modules":["redisbloom"],
                }
            ]
        }
        """
        self.root_id = root_id
        self.data = data
        self.precheck_all()

    @staticmethod
    def precheck_info_item(cluster_id: int, load_modules: list):
        cluster = Cluster.objects.get(id=cluster_id)
        major_version = cluster.major_version
        for load_module in load_modules:
            module_row = get_redis_moudles_detail(major_version=major_version, module_names=[load_module])
            if not module_row:
                raise Exception(
                    _("cluster:{} major_version:{}  redis module {}").format(
                        cluster.immute_domain, cluster.major_version, load_module
                    )
                )

    def precheck_all(self):
        """
        流程前置检查
        """
        to_precheck_cluster_ids = set()
        for info in self.data["infos"]:
            to_precheck_cluster_ids.add(info["cluster_id"])

        # 异步检查集群proxy redis实例状态
        async_multi_clusters_precheck(cluster_ids=to_precheck_cluster_ids)
        for info in self.data["infos"]:
            self.precheck_info_item(cluster_id=info["cluster_id"], load_modules=info["load_modules"])

    def batch_clusters_load_modules(self):
        """
        批量加载集群的模块
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)

        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_load_module()
        act_kwargs.is_update_trans_data = True

        unique_cluster_ids = set()
        for info in self.data["infos"]:
            unique_cluster_ids.add(info["cluster_id"])

        # 并发获取 cluster info
        clusters_info = async_get_multi_cluster_info_by_cluster_ids(cluster_ids=list(unique_cluster_ids))

        logger.info("clusters_info:{}".format(clusters_info))

        sub_pipelines = []
        for info in self.data["infos"]:
            params = {
                "cluster_id": info["cluster_id"],
                "load_modules": info["load_modules"],
                "cluster_info": clusters_info[info["cluster_id"]],
            }
            sub_builder = ClusterLoadModulesAtomJob(
                root_id=self.root_id, ticket_data=self.data, sub_kwargs=act_kwargs, param=params
            )
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
