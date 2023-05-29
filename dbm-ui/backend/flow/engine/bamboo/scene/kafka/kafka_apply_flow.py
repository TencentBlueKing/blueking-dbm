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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import (
    DEFAULT_FACTOR,
    DEFAULT_IP,
    ZK_CONF,
    DnsOpType,
    KafkaActuatorActionEnum,
    ManagerDefaultPort,
    ManagerOpType,
    ManagerServiceType,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.kafka.dns_manage import KafkaDnsManageComponent
from backend.flow.plugins.components.collections.kafka.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.kafka.get_kafka_resource import GetKafkaResourceComponent
from backend.flow.plugins.components.collections.kafka.kafka_config import KafkaConfigComponent
from backend.flow.plugins.components.collections.kafka.kafka_db_meta import KafkaDBMetaComponent
from backend.flow.plugins.components.collections.kafka.trans_flies import TransFileComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.kafka.kafka_act_playload import KafkaActPayload
from backend.flow.utils.kafka.kafka_context_dataclass import ActKwargs, ApplyContext, DnsKwargs

logger = logging.getLogger("flow")


class KafkaApplyFlow(object):
    """
    构建kafka申请流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data
        # 写入cluster_type，转模块会使用
        self.data["cluster_type"] = ClusterType.Kafka.value
        self.data["zookeeper_conf"] = self.__get_zookeeper_conf()
        broker_num = len(self.data["nodes"]["broker"])
        if broker_num >= DEFAULT_FACTOR:
            self.data["factor"] = DEFAULT_FACTOR
        else:
            self.data["factor"] = broker_num

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.data["nodes"]:
            return []
        return self.data["nodes"][role]

    def __get_all_node_ips(self) -> list:
        exec_ip = []
        for role in self.data["nodes"]:
            exec_ip.extend(self.__get_node_ips_by_role(role))
        return exec_ip

    def __get_zookeeper_ip(self) -> str:
        return ",".join([zookeeper["ip"] for zookeeper in self.data["nodes"]["zookeeper"]])

    def __get_zookeeper_conf(self) -> str:
        return "\n".join(
            [ZK_CONF.format(i=i, zk_ip=zookeeper["ip"]) for i, zookeeper in enumerate(self.data["nodes"]["zookeeper"])]
        )

    def deploy_kafka_flow(self):
        """
        定义部署kafka集群
        """
        zookeeper_ip = self.__get_zookeeper_ip()
        self.data["zookeeper_ip"] = zookeeper_ip
        kafka_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Kafka)
        # 拼接活动节点需要的私有参数
        bk_cloud_id = self.data["bk_cloud_id"]
        act_kwargs = ActKwargs(bk_cloud_id=bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        act_kwargs.file_list = trans_files.kafka_apply(db_version=self.data["db_version"])
        act_payload = KafkaActPayload(ticket_data=self.data, zookeeper_ip=zookeeper_ip)

        # 获取机器资源
        kafka_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetKafkaResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 下发kafka介质
        act_kwargs.exec_ip = self.__get_all_node_ips()
        kafka_pipeline.add_act(
            act_name=_("下发kafka介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 初始化节点
        act_kwargs.template = act_payload.get_payload(action=KafkaActuatorActionEnum.initKafka.value, host=DEFAULT_IP)
        kafka_pipeline.add_act(
            act_name=_("初始化节点"), act_component_code=ExecuteDBActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 解压kafka包
        act_kwargs.template = act_payload.get_payload(
            action=KafkaActuatorActionEnum.decompressKafkaPkg.value, host=DEFAULT_IP
        )
        kafka_pipeline.add_act(
            act_name=_("解压kafka包"), act_component_code=ExecuteDBActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 安装supervisor
        act_kwargs.template = act_payload.get_payload(
            action=KafkaActuatorActionEnum.installKafkaSupervisor.value, host=DEFAULT_IP
        )
        kafka_pipeline.add_act(
            act_name=_("安装supervisor"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 安装zookeeper
        zk_act_list = []
        for i, zookeeper in enumerate(self.data["nodes"]["zookeeper"]):
            act_kwargs.exec_ip = [zookeeper]
            act_kwargs.template = act_payload.get_zookeeper_payload(
                action=KafkaActuatorActionEnum.installZookeeper.value,
                my_id=i,
                host=zookeeper["ip"],
                zookeeper_conf=self.data["zookeeper_conf"],
            )
            ip = zookeeper["ip"]
            zookeeper_act = {
                "act_name": _("安装zookeeper-{}").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            zk_act_list.append(zookeeper_act)
        kafka_pipeline.add_parallel_acts(acts_list=zk_act_list)

        # 配置账号
        act_kwargs.exec_ip = [self.data["nodes"]["zookeeper"][0]]
        act_kwargs.template = act_payload.get_admin_user_payload(action=KafkaActuatorActionEnum.initKafkaUser.value)
        kafka_pipeline.add_act(
            act_name=_("初始化系统kafkaUser"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        act_kwargs.template = act_payload.get_user_payload(action=KafkaActuatorActionEnum.initKafkaUser.value)
        kafka_pipeline.add_act(
            act_name=_("初始化kafkaUser"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 安装broker
        broker_act_list = []
        for broker in self.data["nodes"]["broker"]:
            act_kwargs.exec_ip = [broker]
            act_kwargs.template = act_payload.get_payload(
                action=KafkaActuatorActionEnum.installBroker.value, host=broker["ip"]
            )
            ip = broker["ip"]
            broker_act = {
                "act_name": _("安装broker-{}").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            broker_act_list.append(broker_act)
        kafka_pipeline.add_parallel_acts(acts_list=broker_act_list)

        # 安装kafka manager
        act_kwargs.exec_ip = [self.data["nodes"]["broker"][0]]
        act_kwargs.template = act_payload.get_manager_payload(
            action=KafkaActuatorActionEnum.installManager.value, host=self.data["nodes"]["broker"][0]["ip"]
        )
        kafka_pipeline.add_act(
            act_name=_("安装kafka manager"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.CREATE,
            db_type=DBType.Kafka,
            service_type=ManagerServiceType.KAFKA_MANAGER,
            manager_ip=self.data["nodes"]["broker"][0]["ip"],
            manager_port=ManagerDefaultPort.KAFKA_MANAGER,
        )
        kafka_pipeline.add_act(
            act_name=_("插入manager实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )

        dns_kwargs = DnsKwargs(
            bk_cloud_id=bk_cloud_id,
            dns_op_type=DnsOpType.CREATE,
            add_domain_name=self.data["domain"],
            dns_op_exec_port=self.data["port"],
        )
        kafka_pipeline.add_act(
            act_name=_("添加集群域名"),
            act_component_code=KafkaDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        kafka_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=KafkaDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        kafka_pipeline.add_act(
            act_name=_("回写kafka集群配置"), act_component_code=KafkaConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        kafka_pipeline.run_pipeline()
