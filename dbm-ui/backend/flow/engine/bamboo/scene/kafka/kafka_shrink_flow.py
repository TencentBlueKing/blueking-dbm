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
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import (
    DnsOpType,
    KafkaActuatorActionEnum,
    ManagerDefaultPort,
    ManagerOpType,
    ManagerServiceType,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.bigdata_manager_service import (
    BigdataManagerComponent,
    get_manager_ip,
)
from backend.flow.plugins.components.collections.kafka.dns_manage import KafkaDnsManageComponent
from backend.flow.plugins.components.collections.kafka.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.kafka.kafka_db_meta import KafkaDBMetaComponent
from backend.flow.plugins.components.collections.kafka.trans_flies import TransFileComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.kafka.kafka_act_playload import KafkaActPayload, get_base_payload
from backend.flow.utils.kafka.kafka_context_dataclass import ActKwargs, ApplyContext, DnsKwargs

logger = logging.getLogger("flow")


class KafkaShrinkFlow(object):
    """
    构建kafka缩容流程的抽象类
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
        self.data["cluster_name"] = cluster.name
        self.data["domain"] = cluster.immute_domain
        zookeeper_list = cluster.storageinstance_set.filter(instance_role=InstanceRole.ZOOKEEPER)
        zookeeper_ips = [zookeeper.machine.ip for zookeeper in zookeeper_list]
        self.data["zookeeper_ip"] = ",".join(zookeeper_ips)
        broker_obj = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.BROKER).first()
        self.data["port"] = broker_obj.port
        self.data["db_version"] = cluster.major_version
        broker_list = cluster.storageinstance_set.filter(instance_role=InstanceRole.BROKER)
        broker_ips = [broker.machine.ip for broker in broker_list]
        self.data["broker_ips"] = broker_ips

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.data["nodes"]:
            return []
        return [node["ip"] for node in self.data["nodes"][role]]

    def __get_all_node_ips(self) -> list:
        ips = []
        for role in self.data["nodes"]:
            ips.extend(self.__get_node_ips_by_role(role))
        return ips

    def __get_manager_ip(self, manager_ip: str) -> str:
        for broker_ip in self.data["broker_ips"]:
            if broker_ip != manager_ip:
                return broker_ip
        return ""

    def shrink_kafka_flow(self):
        """
        定义Kafka缩容
        """
        kafka_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Kafka)
        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        act_kwargs.file_list = trans_files.fetch_kafka_actuator_path()

        # 下发dbacuator
        exclude_brokers = self.__get_all_node_ips()
        exec_ip = self.data["nodes"]["broker"]
        act_kwargs.exec_ip = exec_ip
        kafka_pipeline.add_act(
            act_name=_("下发dbacuator"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 执行搬迁数据调度，只在一台机器上执行
        act_kwargs.exec_ip = self.data["nodes"]["broker"][:1]
        act_payload = KafkaActPayload(ticket_data=self.data, zookeeper_ip=self.data["zookeeper_ip"])
        act_kwargs.template = act_payload.get_shrink_payload(
            action=KafkaActuatorActionEnum.ReduceBroker.value, host=exclude_brokers
        )
        kafka_pipeline.add_act(
            act_name=_("Kafka搬迁数据"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 检查搬迁进度，只在一台机器上执行
        act_kwargs.template = act_payload.get_shrink_payload(
            action=KafkaActuatorActionEnum.CheckReassign.value, host=exclude_brokers
        )
        kafka_pipeline.add_act(
            act_name=_("Kafka检查搬迁进度"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 清理域名
        dns_kwargs = DnsKwargs(
            bk_cloud_id=self.data["bk_cloud_id"],
            dns_op_type=DnsOpType.RECYCLE_RECORD,
            dns_op_exec_port=self.data["port"],
            add_domain_name=self.data["domain"],
        )
        kafka_pipeline.add_act(
            act_name=_("删除broker的域名记录"),
            act_component_code=KafkaDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 停进程
        all_ips = self.__get_all_node_ips()
        logger.debug(_("停止进程"), all_ips)
        sub_pipelines = []
        for ip in all_ips:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            logger.debug("sub_pipeline", sub_pipeline)
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

        # 清理数据
        logger.debug(_("清理数据"))
        sub_pipelines = []
        for ip in all_ips:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            # 清理数据
            act_kwargs.template = get_base_payload(action=KafkaActuatorActionEnum.CleanData.value, host=ip)
            act_kwargs.exec_ip = [{"ip": ip}]
            sub_pipeline.add_act(
                act_name=_("节点清理-{}").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("清理Kafka {}子流程").format(ip)))
        # 并发执行所有子流程
        kafka_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        manager_ip = get_manager_ip(
            bk_biz_id=self.data["bk_biz_id"],
            db_type=DBType.Kafka,
            cluster_name=self.data["cluster_name"],
            service_type=ManagerServiceType.KAFKA_MANAGER,
        )
        shrink_ips = [broker["ip"] for broker in self.data["nodes"]["broker"]]

        if manager_ip in shrink_ips:
            # 安装kafka manager
            new_manager_ip = self.__get_manager_ip(manager_ip=manager_ip)
            act_kwargs.exec_ip = [{"ip": new_manager_ip}]
            act_kwargs.template = act_payload.get_manager_payload(
                action=KafkaActuatorActionEnum.installManager.value, host=new_manager_ip
            )
            kafka_pipeline.add_act(
                act_name=_("安装kafka manager"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            manager_kwargs = BigdataManagerKwargs(
                manager_op_type=ManagerOpType.UPDATE,
                db_type=DBType.Kafka,
                service_type=ManagerServiceType.KAFKA_MANAGER,
                manager_ip=new_manager_ip,
                manager_port=ManagerDefaultPort.KAFKA_MANAGER,
            )
            kafka_pipeline.add_act(
                act_name=_("更新manager实例信息"),
                act_component_code=BigdataManagerComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
            )

        # 清理db meta 挪模块
        kafka_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=KafkaDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        kafka_pipeline.run_pipeline()
