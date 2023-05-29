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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import KafkaActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.kafka.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.kafka.kafka_db_meta import KafkaDBMetaComponent
from backend.flow.utils.kafka.kafka_act_playload import get_base_payload
from backend.flow.utils.kafka.kafka_context_dataclass import ActKwargs, ApplyContext

logger = logging.getLogger("flow")


class KafkaDisableFlow(object):
    """
    构建Kafka启用流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.root_id = root_id
        self.data = data
        # 写入cluster_type，转模块会使用
        self.data["cluster_type"] = ClusterType.Kafka.value

    def __get_all_node_ips(self) -> list:
        cluster = Cluster.objects.get(id=self.data["cluster_id"])
        self.data["bk_cloud_id"] = cluster.bk_cloud_id
        broker_obj = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.BROKER).first()
        self.data["port"] = broker_obj.port
        storage_ips = list(set(StorageInstance.objects.filter(cluster=cluster).values_list("machine__ip", flat=True)))
        return storage_ips

    def disable_kafka_flow(self):
        """
        定义禁用Kafka集群
        :return:
        """
        kafka_pipeline = Builder(root_id=self.root_id, data=self.data)
        all_ips = self.__get_all_node_ips()
        act_kwargs = ActKwargs(bk_cloud_id=self.data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        sub_pipelines = []
        for ip in all_ips:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            # 停止进程
            act_kwargs.template = get_base_payload(action=KafkaActuatorActionEnum.StopProcess.value, host=ip)
            act_kwargs.exec_ip = [{"ip": ip}]
            sub_pipeline.add_act(
                act_name=_("停止进程-{}").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("禁用Kafka {}子流程").format(ip)))
        # 并发执行所有子流程
        kafka_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 修改DBMeta
        kafka_pipeline.add_act(
            act_name=_("修改Meta"), act_component_code=KafkaDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        kafka_pipeline.run_pipeline()
