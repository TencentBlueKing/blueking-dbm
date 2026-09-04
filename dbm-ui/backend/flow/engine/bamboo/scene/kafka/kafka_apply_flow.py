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
import base64
import logging.config
import re
import uuid
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _
from packaging import version
from packaging.version import InvalidVersion

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
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import new_machine_common_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.common.update_hosts_file import UpsertHostsEntryComponent
from backend.flow.plugins.components.collections.kafka.dns_manage import KafkaDnsManageComponent
from backend.flow.plugins.components.collections.kafka.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.kafka.get_kafka_resource import GetKafkaResourceComponent
from backend.flow.plugins.components.collections.kafka.kafka_apply_summary import add_kafka_apply_summary_output_act
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
        self.data["zookeeper_connect"] = self.__get_zookeeper_connect()
        broker_num = len(self.data["nodes"]["broker"])
        if broker_num >= DEFAULT_FACTOR:
            self.data["factor"] = DEFAULT_FACTOR
        else:
            self.data["factor"] = broker_num
        raw_ver = (self.data.get("db_version") or "").strip()
        parsed_version = self._normalize_and_parse(raw_ver)
        self.is_kafka_4 = parsed_version >= version.parse("4.0")

        # --- 新增兼容逻辑 ---
        if self.is_kafka_4:
            # 1. 如果没传 controller，则用 zookeeper节点代替
            if not self.data["nodes"].get("controller"):
                self.data["nodes"]["controller"] = self.data["nodes"].get("zookeeper", [])
            # 2. controller_voters 构建, 格式为 "1@ip:port:UUID,2@ip:port:UUID"
            controller_port = int(self.data.get("controller_port", 2181))
            voters = []
            controller = []
            for i, c in enumerate(self.data["nodes"]["controller"], start=1):
                ip = c.get("ip")
                if not ip:
                    raise ValueError(f"controller node at index {i-1} missing 'ip' field")
                # 生成真实的 Kafka-style UUID 并写回节点字典，便于后续使用
                c_uuid = self._generate_kafka_style_uuid()
                c["node_id"] = i
                c["controller_uuid"] = c_uuid
                voters.append(f"{i}@{ip}:{controller_port}:{c_uuid}")
                controller.append(f"{ip}:{controller_port}")

            self.data["controller_voters"] = ",".join(voters)
            self.data["controller_servers"] = ",".join(controller)

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

    def __get_zookeeper_connect(self) -> str:
        zookeeper_ips = [f'{zookeeper["ip"]}:2181' for zookeeper in self.data["nodes"]["zookeeper"]]
        return ",".join(zookeeper_ips) + "/"

    def _normalize_and_parse(self, ver_str: str) -> version.Version:
        ver_str = (ver_str or "").strip()
        if not ver_str:
            return version.parse("0")
        try:
            return version.parse(ver_str)
        except InvalidVersion:
            m = re.match(r"^(\d+(?:\.\d+)*)(?:\.([A-Za-z][A-Za-z0-9._-]*))?$", ver_str)
            if m:
                core = m.group(1)
                local = m.group(2)
                if local:
                    try:
                        return version.parse(f"{core}+{local}")
                    except InvalidVersion:
                        return version.parse(core)
                return version.parse(core)
            m2 = re.match(r"^(\d+(?:\.\d+)*)", ver_str)
            if m2:
                return version.parse(m2.group(1))
        return version.parse("0")

    @staticmethod
    def _generate_kafka_style_uuid() -> str:
        """生成 Kafka 风格的 UUID（16 字节的 URL-safe base64，无 '=' 填充），长度为 22。"""
        return base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=").decode("ascii")

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

        # 增加机器初始化子流程
        all_new_machines = self.__get_all_node_ips()
        all_new_ips = [node["ip"] for node in all_new_machines]
        common_sub_flow = new_machine_common_sub_flow(
            uid=self.data["uid"], root_id=self.root_id, bk_cloud_id=self.data["bk_cloud_id"], new_ips=all_new_ips
        )
        if common_sub_flow:
            kafka_pipeline.add_sub_pipeline(sub_flow=common_sub_flow)

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

        # ---- 部署 zookeeper（仅 < 4.0） ----
        if not self.is_kafka_4:
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
            act_kwargs.template = act_payload.get_admin_user_payload(
                action=KafkaActuatorActionEnum.initKafkaUser.value
            )
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

        # ---- 部署 controller（仅 >= 4.0） ----
        if self.is_kafka_4:
            controller_act_list = []
            for controller in self.data["nodes"]["controller"]:
                act_kwargs.exec_ip = [controller]
                rack = controller.get("rack_id", "RACK1")
                node_id = controller["node_id"]
                act_kwargs.template = act_payload.get_payload(
                    action=KafkaActuatorActionEnum.installBroker.value,
                    host=controller["ip"],
                    rack=rack,
                    role="controller",
                    node_id=node_id,
                )
                ip = controller["ip"]
                controller_act = {
                    "act_name": _("安装controller-{}").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
                controller_act_list.append(controller_act)
            kafka_pipeline.add_parallel_acts(acts_list=controller_act_list)
        # 安装broker
        broker_act_list = []
        for i, broker in enumerate(self.data["nodes"]["broker"], 4):
            act_kwargs.exec_ip = [broker]
            rack = broker.get("rack_id", "RACK1")
            act_kwargs.template = act_payload.get_payload(
                action=KafkaActuatorActionEnum.installBroker.value,
                host=broker["ip"],
                rack=rack,
                role="broker",
                node_id=i,
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

        # 在 ZK 节点写入 /etc/hosts，将 kafkabroker 指向第一个 broker IP（供 dbm_kafka_exporter 使用）
        kafka_pipeline.add_act(
            act_name=_("写入kafkabroker到ZK节点hosts"),
            act_component_code=UpsertHostsEntryComponent.code,
            kwargs={
                "exec_targets": [
                    {"ip": zk["ip"], "bk_cloud_id": bk_cloud_id} for zk in self.data["nodes"]["zookeeper"]
                ],
                "hosts_entries": [{"ip": self.data["nodes"]["broker"][0]["ip"], "domain": "kafkabroker"}],
            },
        )

        kafka_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=KafkaDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        kafka_pipeline.add_act(
            act_name=_("回写kafka集群配置"), act_component_code=KafkaConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        # 写入集群信息摘要，供前端"执行摘要"展示
        add_kafka_apply_summary_output_act(
            kafka_pipeline=kafka_pipeline,
            bk_biz_id=self.data["bk_biz_id"],
            domain_name=self.data["domain"],
            region=self.data.get("city_code", ""),
            version=self.data["db_version"],
            port=self.data["port"],
        )

        kafka_pipeline.run_pipeline()
