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
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ProxyUnInstallAtomJob, RedisBatchShutdownAtomJob
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisClusterInstanceShutdownSceneFlow(object):
    """
    ## proxy/storage 下架 通用入口 [只做实例下架， clb/dns..这里不干活！！]
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"vitox",
        "ticket_type":"REDIS_CLUSTER_INSTANCE_SHUTDOWN",
        "infos": [
            {
            "cluster_id": 1,
            "proxy": ["1.1.1.a"],
            "redis_slave": ["1.1.1.a"],
            }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def get_cluster_info(bk_biz_id: int, cluster_id: int) -> dict:
        """获取集群现有信息
        1. master 对应 slave 机器
        2. master 上的端口列表
        3. 实例对应关系：{master:port:slave:port}
        """
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        slave_ports = defaultdict(list)

        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            slave_ports[slave_obj.machine.ip].append(slave_obj.port)
        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": str(cluster.bk_biz_id),
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "cluster_name": cluster.name,
            "cluster_id": cluster.id,
            "slave_ports": dict(slave_ports),
            "proxy_port": cluster.proxyinstance_set.first().port,
            "proxy_ips": [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()],
            "db_version": cluster.major_version,
        }

    def __init_builder(self, operate_name: str):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            "operate": operate_name,
        }
        return redis_pipeline, act_kwargs

    # flow 入口
    def start_instance_shutdown(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS-实例下架"))
        sub_pipelines = []
        for cluster_instances in self.data["infos"]:
            cluster_kwargs = deepcopy(act_kwargs)
            cluster_info = self.get_cluster_info(self.data["bk_biz_id"], cluster_instances["cluster_id"])

            flow_data = self.data
            for k, v in cluster_info.items():
                cluster_kwargs.cluster[k] = v
            cluster_kwargs.cluster["created_by"] = self.data["created_by"]
            flow_data["shutdown_instances"] = cluster_instances
            redis_pipeline.add_act(
                act_name=_("初始化配置-{}".format(cluster_info["immute_domain"])),
                act_component_code=GetRedisActPayloadComponent.code,
                kwargs=asdict(cluster_kwargs),
            )
            sub_pipeline = self.instance_shutdown(cluster_kwargs, cluster_instances)
            sub_pipelines.append(sub_pipeline)

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

    # 对每个集群操作
    def instance_shutdown(self, sub_kwargs, shutdown_params):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        # #### 下架旧实例 ############################################################################
        sub_pipelines = []
        for shutdown_ip in shutdown_params.get("redis_slave", {}):
            sub_builder = RedisBatchShutdownAtomJob(
                self.root_id,
                self.data,
                deepcopy(sub_kwargs),
                {
                    "ip": shutdown_ip,
                    "ports": sub_kwargs.cluster["slave_ports"][shutdown_ip],
                },
            )
            sub_pipelines.append(sub_builder)
        if len(sub_pipelines) > 0:
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # #### 下架旧实例 ###################################################################### 完毕 ###

        # #### 下架旧实例 ############################################################################
        sub_pipelines = []
        for proxy_ip in shutdown_params.get("proxy", {}):
            sub_builder = ProxyUnInstallAtomJob(
                self.root_id,
                self.data,
                deepcopy(sub_kwargs),
                {"ip": proxy_ip, "proxy_port": sub_kwargs.cluster["proxy_port"]},
            )
            sub_pipelines.append(sub_builder)
        if len(sub_pipelines) > 0:
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # #### 下架旧实例 ###################################################################### 完毕 ###

        return sub_pipeline.build_sub_process(sub_name=_("实例下架-{}").format(sub_kwargs.cluster["immute_domain"]))
