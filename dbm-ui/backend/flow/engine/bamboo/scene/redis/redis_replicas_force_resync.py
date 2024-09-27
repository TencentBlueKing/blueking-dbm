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
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_proxy_util import async_multi_clusters_precheck, get_cluster_info_by_cluster_id

logger = logging.getLogger("flow")


class RedisReplicasForceResyncSceneFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        """
        self.root_id = root_id
        self.data = data
        self.precheck(self.data["cluster_ids"])

    @staticmethod
    def precheck(cluster_ids: list):
        async_multi_clusters_precheck(cluster_ids)

    def replicas_force_resync(self):
        """
        slaves 强制重同步
        self.data (Dict):
        {
            "bk_biz_id": "",
            "bk_cloud_id":0,
            "cluster_ids":[1,2,3],
        }
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for cluster_id in self.data["cluster_ids"]:
            cluster = Cluster.objects.get(id=cluster_id)
            cluster_info = get_cluster_info_by_cluster_id(cluster_id=cluster.id)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            cluster_kwargs = deepcopy(act_kwargs)

            sub_pipeline.add_act(
                act_name=_("初始化配置"),
                act_component_code=GetRedisActPayloadComponent.code,
                kwargs=asdict(cluster_kwargs),
            )

            cluster_kwargs.exec_ip = cluster_info["slave_ips"]
            sub_pipeline.add_act(
                act_name=_("下发介质包"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(cluster_kwargs),
            )

            cluster_kwargs.cluster = {}
            acts_list = []
            for slave_ip, slave_ports in cluster_info["slave_ports"].items():
                cluster_kwargs.exec_ip = slave_ip
                cluster_kwargs.cluster = {"slave_ip": slave_ip, "slave_ports": slave_ports}
                cluster_kwargs.get_redis_payload_func = RedisActPayload.redis_replicas_force_resync.__name__
                acts_list.append(
                    {
                        "act_name": _("slave:{} 强制重同步").format(slave_ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(cluster_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)
            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("集群{} slave强制重同步".format(cluster_info["immute_domain"])))
            )

            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
