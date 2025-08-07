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
from backend.db_package.models import Package
from backend.db_services.redis.util import is_predixy_proxy_type, is_twemproxy_proxy_type
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ClusterProxysUpgradeAtomJob
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_proxy_util import async_multi_clusters_precheck

logger = logging.getLogger("flow")


class RedisProxyVersionUpgradeSceneFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        """
        self.root_id = root_id
        self.data = data
        self.precheck()

    def precheck(self):
        """
        1. 集群是否存在
        2. 是否存在非 running 状态的 proxy
        3. 是否存在非 running 状态的 redis;
        4. 连接 proxy 是否正常;
        5. 连接 redis 是否正常;
        6. 是否所有master 都有 slave;
        """
        to_precheck_cluster_ids = []
        for input_item in self.data["infos"]:
            if not input_item["target_version_file"]:
                raise Exception(_("redis集群 {} 目标版本文件为空?").format(input_item["cluster_id"]))
            cluster = Cluster.objects.get(id=input_item["cluster_id"])
            to_precheck_cluster_ids.append(cluster.id)

            # 目标版本文件 是否在 "版本文件"中
            proxy_pkg: Package = None
            if is_twemproxy_proxy_type(cluster.cluster_type):
                proxy_pkg = Package.get_latest_package(
                    version=MediumEnum.Latest,
                    pkg_type=MediumEnum.Twemproxy,
                    db_type=DBType.Redis,
                    name_prefix=input_item["target_version_file"],
                )
            elif is_predixy_proxy_type(cluster.cluster_type):
                proxy_pkg = Package.get_latest_package(
                    version=MediumEnum.Latest,
                    pkg_type=MediumEnum.Predixy,
                    db_type=DBType.Redis,
                    name_prefix=input_item["target_version_file"],
                )
            else:
                raise Exception(
                    _("redis集群:{} cluster_type:{} 不认识").format(cluster.immute_domain, cluster.cluster_type)
                )

            # No package matched.
            if not proxy_pkg:
                raise Exception(
                    _("redis集群:{} 目标版本文件:{} 找不到").format(cluster.immute_domain, input_item["target_version_file"])
                )
        # 并发检查多个cluster的proxy、redis实例状态
        async_multi_clusters_precheck(cluster_ids=to_precheck_cluster_ids)

    def batch_clusters_proxys_upgrade(self):
        """集群proxy整体升级版本
        self.data (Dict):
        {
          "bk_biz_id":3,
          "infos": [
            {
                "cluster_id": 1,
                "current_version_file": "twemproxy-0.4.1-v28.tar.gz",
                "target_version_file": "twemproxy-0.4.1-v29.tar.gz",
            },
            {
                "cluster_id": 2,
                "current_version_file": "twemproxy-0.4.1-v27.tar.gz",
                "target_version_file": "twemproxy-0.4.1-v29.tar.gz",
            }
          ]
        }
        """
        # 先cluster_id去重
        cluster_ids_seen = set()
        cluster_id_targets = []
        for input_item in self.data["infos"]:
            cluster_id = input_item["cluster_id"]
            if cluster_id not in cluster_ids_seen:
                cluster_ids_seen.add(cluster_id)
                cluster_id_targets.append((cluster_id, input_item["target_version_file"]))

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines = []
        for cluster_id, target_file in cluster_id_targets:
            cluster = Cluster.objects.get(id=cluster_id)
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True
            act_kwargs.bk_cloud_id = cluster.bk_cloud_id
            params = {
                "cluster_domain": cluster.immute_domain,
                "target_version_file": target_file,
            }
            sub_builder = ClusterProxysUpgradeAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
