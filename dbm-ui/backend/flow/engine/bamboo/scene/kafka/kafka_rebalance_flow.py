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
import logging
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import KafkaActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.kafka.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.kafka.trans_flies import TransFileComponent
from backend.flow.utils.kafka.kafka_act_playload import KafkaActPayload
from backend.flow.utils.kafka.kafka_context_dataclass import ActKwargs, ApplyContext

logger = logging.getLogger("flow")


class KafkaRebalanceFlow(object):
    """
    构建kafka再平衡流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

        cluster = Cluster.objects.get(id=self.data["cluster_id"])
        self.data["db_version"] = cluster.major_version
        self.data["bk_cloud_id"] = cluster.bk_cloud_id
        zookeeper_list = cluster.storageinstance_set.filter(instance_role=InstanceRole.ZOOKEEPER)
        zookeeper_ips = [zookeeper.machine.ip for zookeeper in zookeeper_list]
        self.data["zookeeper_ip"] = ",".join(zookeeper_ips)

    def __get_all_rebalance_instances(self) -> list:
        return self.data["instance_list"]

    def rebalance_kafka_flow(self):
        """
        定义Kafka再平衡
        """
        kafka_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Kafka)
        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        act_kwargs.file_list = trans_files.get_db_actuator_package()

        # 下发dbacuator
        rebalance_brokers = self.__get_all_rebalance_instances()
        if not rebalance_brokers:
            logger.error(_("没有可再平衡的Broker实例"))
            return
        broker_ips = [broker["ip"] for broker in rebalance_brokers]
        exec_ip = rebalance_brokers[0]["ip"] if rebalance_brokers else None
        act_kwargs.exec_ip = [{"ip": exec_ip}]
        kafka_pipeline.add_act(
            act_name=_("下发dbacuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 生成执行计划，只在一台机器上执行
        act_kwargs.exec_ip = [{"ip": exec_ip}]
        act_payload = KafkaActPayload(ticket_data=self.data, zookeeper_ip=self.data["zookeeper_ip"])
        act_kwargs.template = act_payload.get_rebalance_payload(
            action=KafkaActuatorActionEnum.GenerateReassignment.value, host=broker_ips
        )
        kafka_pipeline.add_act(
            act_name=_("Kafka生成均衡计划"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 执行均衡，只在一台机器上执行
        act_kwargs.exec_ip = [{"ip": exec_ip}]
        act_kwargs.template = act_payload.get_rebalance_payload(
            action=KafkaActuatorActionEnum.ExecuteReassignment.value, host=broker_ips
        )
        kafka_pipeline.add_act(
            act_name=_("Kafka执行均衡计划"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        kafka_pipeline.run_pipeline()
