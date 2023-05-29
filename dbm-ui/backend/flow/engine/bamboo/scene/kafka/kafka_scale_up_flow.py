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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import DEFAULT_IP, DnsOpType, KafkaActuatorActionEnum, LevelInfoEnum, NameSpaceEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.kafka.dns_manage import KafkaDnsManageComponent
from backend.flow.plugins.components.collections.kafka.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.kafka.get_kafka_resource import GetKafkaResourceComponent
from backend.flow.plugins.components.collections.kafka.kafka_db_meta import KafkaDBMetaComponent
from backend.flow.plugins.components.collections.kafka.trans_flies import TransFileComponent
from backend.flow.utils.kafka.kafka_act_playload import KafkaActPayload
from backend.flow.utils.kafka.kafka_context_dataclass import ActKwargs, ApplyContext, DnsKwargs

logger = logging.getLogger("flow")


class KafkaScaleUpFlow(object):
    """
    构建kafka扩容流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

        cluster = Cluster.objects.get(id=self.data["cluster_id"])
        self.data["bk_cloud_id"] = cluster.bk_cloud_id
        zookeeper_list = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ZOOKEEPER).all()
        zookeeper_ip = ",".join([zookeeper.machine.ip for zookeeper in zookeeper_list])
        self.data["zookeeper_ip"] = zookeeper_ip
        broker_list = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.BROKER).all()
        self.data["db_version"] = cluster.major_version
        self.data["domain"] = cluster.immute_domain
        self.data["cluster_name"] = cluster.name
        self.data["port"] = broker_list[0].port
        # 写入cluster_type，转模块会使用
        self.data["cluster_type"] = ClusterType.Kafka.value

        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.data["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": self.data["domain"],
                "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
                "conf_file": self.data["db_version"],
                "conf_type": ConfType.DBCONF,
                "namespace": NameSpaceEnum.Kafka,
                "format": FormatType.MAP,
            }
        )
        kafka_config = data["content"]
        self.data["retention_hours"] = int(kafka_config["retention_hours"])
        self.data["replication_num"] = int(kafka_config["replication_num"])
        self.data["partition_num"] = int(kafka_config["partition_num"])
        self.data["factor"] = int(kafka_config["factor"])
        self.data["adminUser"] = kafka_config["adminUser"]
        self.data["adminPassword"] = kafka_config["adminPassword"]

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.data["nodes"]:
            return []
        return self.data["nodes"][role]

    def __get_all_node_ips(self) -> list:
        exec_ip = []
        for role in self.data["nodes"]:
            exec_ip.extend(self.__get_node_ips_by_role(role))
        return exec_ip

    def scale_up_kafka_flow(self):
        """
        定义部署kafka集群
        """
        kafka_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Kafka)
        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        act_kwargs.file_list = trans_files.kafka_apply(db_version=self.data["db_version"])

        # 获取机器资源
        kafka_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetKafkaResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 下发kafka介质
        act_kwargs.exec_ip = self.__get_all_node_ips()
        kafka_pipeline.add_act(
            act_name=_("下发kafka介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        act_payload = KafkaActPayload(ticket_data=self.data, zookeeper_ip=self.data["zookeeper_ip"])
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

        dns_kwargs = DnsKwargs(
            bk_cloud_id=self.data["bk_cloud_id"],
            dns_op_type=DnsOpType.CREATE,
            add_domain_name=self.data["domain"],
            dns_op_exec_port=self.data["port"],
        )
        kafka_pipeline.add_act(
            act_name=_("更新域名"),
            act_component_code=KafkaDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        kafka_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=KafkaDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        kafka_pipeline.run_pipeline()
