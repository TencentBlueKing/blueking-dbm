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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisClusterBackupFlow(object):
    """
    redis备份流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_instance_ip_ports(
        bk_biz_id: int, cluster_id: int, instance_role: str = InstanceRole.REDIS_SLAVE.value
    ) -> dict:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        ip_ports = defaultdict(list)
        for slave in cluster.storageinstance_set.filter(instance_role=instance_role):
            ip_ports[slave.machine.ip].append(slave.port)

        return dict(ip_ports)

    @staticmethod
    def __get_domain_and_cloud_id(bk_biz_id: int, cluster_id: int):
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        return cluster.immute_domain, cluster.bk_cloud_id

    def redis_cluster_backup_flow(self):
        """
        主要逻辑：
            1、初始化信息
            3、for
            3.1、根据cluster_id获取slave实例列表
            3.2、下发介质包
            3.3、构建参数下发任务
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)

        sub_pipelines = []
        for rule in self.data["rules"]:
            if rule["target"] == "master":
                ip_ports = self.__get_instance_ip_ports(
                    self.data["bk_biz_id"], rule["cluster_id"], InstanceRole.REDIS_MASTER.value
                )
            else:
                ip_ports = self.__get_instance_ip_ports(
                    self.data["bk_biz_id"], rule["cluster_id"], InstanceRole.REDIS_SLAVE.value
                )
            domain_name, bk_cloud_id = self.__get_domain_and_cloud_id(self.data["bk_biz_id"], rule["cluster_id"])
            cluster = {**ip_ports, **rule, "domain_name": domain_name}

            exec_ip = list(ip_ports.keys())

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.is_update_trans_data = True
            act_kwargs.cluster = cluster
            act_kwargs.bk_cloud_id = bk_cloud_id
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            act_kwargs.exec_ip = exec_ip
            sub_pipeline.add_act(
                act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
            )

            acts_list = []
            for ip, __ in ip_ports.items():
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_backup_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("redis备份: {}").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )

            sub_pipeline.add_parallel_acts(acts_list=acts_list)
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("集群[{}]备份").format(domain_name)))

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
