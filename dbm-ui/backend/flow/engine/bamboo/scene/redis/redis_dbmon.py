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
from typing import Dict, List, Optional

from backend.configuration.constants import DBType
from backend.db_meta.api.cluster.apis import query_cluster_by_hosts
from backend.db_meta.models import Cluster, Machine
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ClusterDbmonInstallAtomJob, ClusterIPsDbmonInstallAtomJob
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisDbmonSceneFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_cluster_info(bk_biz_id: int, hosts: List) -> dict:
        """获取集群现有信息"""
        if len(hosts) == 0:
            hosts = [machine_obj.ip for machine_obj in Machine.objects.filter(bk_biz_id=bk_biz_id)]
        return query_cluster_by_hosts(hosts)

    def batch_ips_update_dbmon(self):
        """### 适用于 集群中Master 机房裁撤/迁移替换场景 (成对替换)

        步骤：   获取机器实例列表--> 按照机器重装dbmon
        self.data (Dict):
        {
          "bk_biz_id":"", # 必须有
          "bk_cloud_id":11, # 必须有
          "hosts":[1.1.a.1,2.2.2.b], # 可选， 不传就是app 下所有redis机器
          "ticket_type": "REDIS_INSTALL_DBMON"
        }
        """
        # 去重
        hosts_set = set()
        for host in self.data["hosts"]:
            hosts_set.add(host)

        hosts_cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], list(hosts_set))

        ips_group_by_cluster = {}
        for one_host in hosts_cluster_info:
            if not ips_group_by_cluster.get(one_host["cluster"]):
                ips_group_by_cluster[one_host["cluster"]] = []
            ips_group_by_cluster[one_host["cluster"]].append(one_host["ip"])

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

        # ### 部署DBMON #############################################################################
        sub_pipelines = []
        for cluster_domain, ips in ips_group_by_cluster.items():
            params = {
                "cluster_domain": cluster_domain,
                "ips": ips,
                "is_stop": False,
            }
            sub_builder = ClusterIPsDbmonInstallAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # ### 部署DBMON ########################################################################## 完毕 ###

        redis_pipeline.run_pipeline()

    def batch_clusters_update_dbmon(self):
        """集群机器整体重装dbmon
        self.data (Dict):
        {
          "bk_biz_id":"",
          "cluster_ids":[1,2,3],
          "is_stop": True/False, # 是否停止dbmon
        }
        """
        # 先cluster_id去重
        cluster_ids_set = set()
        for cluster_id in self.data["cluster_ids"]:
            cluster_ids_set.add(cluster_id)
        clusters = []
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
                "cluster_domain": cluster.immute_domain,
                "is_stop": self.data.get("is_stop", False),
            }
            sub_builder = ClusterDbmonInstallAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
