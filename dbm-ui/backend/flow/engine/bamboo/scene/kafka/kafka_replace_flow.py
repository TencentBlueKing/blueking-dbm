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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName
from backend.components.mysql_priv_manager.client import MySQLPrivManagerApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import (
    DEFAULT_IP,
    ZK_CONF,
    ZK_PORT,
    DnsOpType,
    KafkaActuatorActionEnum,
    LevelInfoEnum,
    ManagerDefaultPort,
    ManagerOpType,
    ManagerServiceType,
    MySQLPrivComponent,
    NameSpaceEnum,
)
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import sa_init_machine_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.bigdata_manager_service import (
    BigdataManagerComponent,
    get_manager_ip,
)
from backend.flow.plugins.components.collections.kafka.dns_manage import KafkaDnsManageComponent
from backend.flow.plugins.components.collections.kafka.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.kafka.get_kafka_resource import GetKafkaResourceComponent
from backend.flow.plugins.components.collections.kafka.kafka_config import KafkaConfigComponent
from backend.flow.plugins.components.collections.kafka.kafka_db_meta import KafkaDBMetaComponent
from backend.flow.plugins.components.collections.kafka.trans_flies import TransFileComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.kafka.kafka_act_playload import KafkaActPayload, get_base_payload
from backend.flow.utils.kafka.kafka_context_dataclass import ActKwargs, ApplyContext, DnsKwargs

logger = logging.getLogger("flow")


class KafkaReplaceFlow(object):
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
        cluster = Cluster.objects.get(id=self.data["cluster_id"])
        self.data["bk_cloud_id"] = cluster.bk_cloud_id
        # 生成zk连接串
        zookeeper_list = cluster.storageinstance_set.filter(instance_role=InstanceRole.ZOOKEEPER)
        zookeeper_ip = [zookeeper.machine.ip for zookeeper in zookeeper_list]
        if self.data["new_nodes"].get("zookeeper"):
            new_zookeeper_ip = []
            old_zookeeper_ip = [old_zookeeper["ip"] for old_zookeeper in self.data["old_nodes"]["zookeeper"]]
            i = 0
            for old in zookeeper_ip:
                if old in old_zookeeper_ip:
                    new = self.data["new_nodes"]["zookeeper"][i]["ip"]
                    new_zookeeper_ip.append(new)
                    i = i + 1
                else:
                    new_zookeeper_ip.append(old)
            self.data["zookeeper_ip"] = ",".join(new_zookeeper_ip)

            for zookeeper in zookeeper_list:
                if zookeeper.bk_instance_id and zookeeper.machine.ip in old_zookeeper_ip:
                    self.data["zk_ip"] = self.data["new_nodes"]["zookeeper"][0]["ip"]
        else:
            self.data["zookeeper_ip"] = ",".join(zookeeper_ip)

        # 填充集群信息
        broker_list = cluster.storageinstance_set.filter(instance_role=InstanceRole.BROKER)
        self.data["broker_ip"] = [broker.machine.ip for broker in broker_list]
        self.data["db_version"] = cluster.major_version
        self.data["domain"] = cluster.immute_domain
        self.data["cluster_name"] = cluster.name
        self.data["port"] = broker_list[0].port

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
        # 填充集群配置
        kafka_config = data["content"]
        self.data["retention_hours"] = int(kafka_config["retention_hours"])
        self.data["replication_num"] = int(kafka_config["replication_num"])
        self.data["partition_num"] = int(kafka_config["partition_num"])
        self.data["username"] = kafka_config["username"]
        self.data["password"] = kafka_config["password"]
        self.data["factor"] = int(kafka_config["factor"])
        self.data["old_zookeeper_conf"] = kafka_config["zookeeper_conf"]
        self.data["zookeeper_conf"] = self.data["old_zookeeper_conf"]

        # get username
        query_params = {
            "instances": [{"ip": str(self.data["domain"]), "port": 0, "bk_cloud_id": self.data["bk_cloud_id"]}],
            "users": [{"username": MySQLPrivComponent.KAFKA_FAKE_USER.value, "component": NameSpaceEnum.Kafka}],
        }
        ret = MySQLPrivManagerApi.get_password(query_params)
        username = base64.b64decode(ret["items"][0]["password"]).decode("utf-8")

        # get password
        query_params = {
            "instances": [{"ip": str(self.data["domain"]), "port": 0, "bk_cloud_id": self.data["bk_cloud_id"]}],
            "users": [{"username": username, "component": NameSpaceEnum.Kafka}],
        }
        ret = MySQLPrivManagerApi.get_password(query_params)
        password = base64.b64decode(ret["items"][0]["password"]).decode("utf-8")
        self.data["username"] = username
        self.data["password"] = password

    def __get_node_ips_by_role(self, role: str) -> list:
        if role not in self.data["new_nodes"]:
            return []
        return self.data["new_nodes"][role]

    def __get_all_node_ips(self) -> list:
        exec_ip = []
        for role in self.data["new_nodes"]:
            exec_ip.extend(self.__get_node_ips_by_role(role))
        return exec_ip

    # 生成zk配置文件
    def __get_zookeeper_conf(self) -> (str, int, str):
        old_zookeeper_conf = self.data["old_zookeeper_conf"]
        old_zookeeper_conf_list = old_zookeeper_conf.strip("\n").split("\n")
        """
        找出最大的myid
        字符串形式：
            server.0=127.0.0.1:2888:3888;2181
            server.1=127.0.0.1:2888:3888;2181
            server.2=127.0.0.1:2888:3888;2181
        self.data["zookeeper_conf"]记录了最终形态
        返回值是中间形态
        """
        max_my_id = 0
        zookeeper_conf_list = []
        old_my_id_list = []
        old_zookeeper_ip_set = {zookeeper["ip"] for zookeeper in self.data["old_nodes"]["zookeeper"]}
        for old_zookeeper_conf in old_zookeeper_conf_list:
            result = re.sub(ZK_PORT, "", old_zookeeper_conf.strip("server")).split("=")
            list_str = list(result[0])
            list_str.pop(0)
            my_id = int("".join(list_str))
            if my_id > max_my_id:
                max_my_id = my_id

            ip = result[1]
            if ip not in old_zookeeper_ip_set:
                zookeeper_conf_list.append(old_zookeeper_conf)
            else:
                old_my_id_list.append(str(my_id))

        base_my_id = max_my_id + 1
        new_zookeeper_conf_list = old_zookeeper_conf_list
        for i, zookeeper in enumerate(self.data["new_nodes"]["zookeeper"]):
            new_zookeeper_conf = ZK_CONF.format(i=base_my_id + i, zk_ip=zookeeper["ip"])
            new_zookeeper_conf_list.append(new_zookeeper_conf)
            zookeeper_conf_list.append(new_zookeeper_conf)
        self.data["zookeeper_conf"] = "\n".join(zookeeper_conf_list)

        return "\n".join(new_zookeeper_conf_list), base_my_id, ",".join(old_my_id_list).strip(",")

    def replace_kafka_flow(self):
        """
        定义部署kafka集群
        """
        kafka_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Kafka)
        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = ApplyContext.__name__
        act_kwargs.file_list = trans_files.kafka_apply(db_version=self.data["db_version"])
        act_payload = KafkaActPayload(ticket_data=self.data, zookeeper_ip=self.data["zookeeper_ip"])

        # 获取机器资源
        kafka_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetKafkaResourceComponent.code, kwargs=asdict(act_kwargs)
        )
        # 增加机器初始化子流程
        all_new_machines = self.__get_all_node_ips()
        all_new_ips = [node["ip"] for node in all_new_machines]
        kafka_pipeline.add_sub_pipeline(
            sub_flow=sa_init_machine_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_cloud_id=self.data["bk_cloud_id"],
                bk_biz_id=self.data["bk_biz_id"],
                init_ips=all_new_ips,
                idle_check_ips=all_new_ips,
                set_dns_ips=[],
            )
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

        # 判断是否替换zk节点
        if self.data["new_nodes"].get("zookeeper"):
            zookeeper_conf, base, remove_my_id = self.__get_zookeeper_conf()
            # 安装zookeeper
            zk_act_list = []
            for i, zookeeper in enumerate(self.data["new_nodes"]["zookeeper"]):
                act_kwargs.exec_ip = [zookeeper]
                act_kwargs.template = act_payload.get_zookeeper_payload(
                    action=KafkaActuatorActionEnum.installZookeeper.value,
                    my_id=base + i,
                    host=zookeeper["ip"],
                    zookeeper_conf=zookeeper_conf,
                )
                ip = zookeeper["ip"]
                zookeeper_act = {
                    "act_name": _("安装zookeeper-{}").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
                zk_act_list.append(zookeeper_act)
            kafka_pipeline.add_parallel_acts(acts_list=zk_act_list)

            # 动态加入zookeeper
            act_kwargs.exec_ip = [self.data["new_nodes"]["zookeeper"][0]]
            act_kwargs.template = get_base_payload(action=KafkaActuatorActionEnum.ReconfigAdd.value, host="")
            kafka_pipeline.add_act(
                act_name=_("增加zookeeper节点"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 滚动重启broker
            for broker_ip in self.data["broker_ip"]:
                act_kwargs.exec_ip = [{"ip": broker_ip}]
                act_kwargs.template = act_payload.get_restart_payload()
                kafka_pipeline.add_act(
                    act_name=_("滚动重启broker节点-{ip}").format(ip=broker_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

            # 动态剔除zookeeper
            act_kwargs.exec_ip = [self.data["new_nodes"]["zookeeper"][0]]
            act_kwargs.template = get_base_payload(
                action=KafkaActuatorActionEnum.ReconfigRemove.value, host=remove_my_id
            )
            kafka_pipeline.add_act(
                act_name=_("移除zookeeper节点"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 下架zookeeper
            sub_pipelines = []
            for zookeeper in self.data["old_nodes"]["zookeeper"]:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
                act_kwargs.exec_ip = [zookeeper]
                act_kwargs.template = get_base_payload(
                    action=KafkaActuatorActionEnum.StopProcess.value, host=zookeeper["ip"]
                )
                ip = zookeeper["ip"]
                sub_pipeline.add_act(
                    act_name=_("停止进程-{}").format(ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                act_kwargs.template = get_base_payload(
                    action=KafkaActuatorActionEnum.CleanData.value, host=zookeeper["ip"]
                )
                sub_pipeline.add_act(
                    act_name=_("节点清理-{}").format(ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("下架zookeeper-{}子流程").format(ip)))
            kafka_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

            kafka_pipeline.add_act(
                act_name=_("回写kafka集群配置"), act_component_code=KafkaConfigComponent.code, kwargs=asdict(act_kwargs)
            )

        # 判断是否替换broker节点
        if self.data["new_nodes"].get("broker"):
            # 安装broker
            broker_act_list = []
            for broker in self.data["new_nodes"]["broker"]:
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

            manager_ip = get_manager_ip(
                bk_biz_id=self.data["bk_biz_id"],
                db_type=DBType.Kafka,
                cluster_name=self.data["cluster_name"],
                service_type=ManagerServiceType.KAFKA_MANAGER,
            )
            old_broker_ip = [old_broker["ip"] for old_broker in self.data["old_nodes"]["broker"]]

            # 判断是否替换manager节点
            if manager_ip in old_broker_ip:
                # 安装kafka manager
                act_kwargs.exec_ip = [self.data["new_nodes"]["broker"][0]]
                act_kwargs.template = act_payload.get_manager_payload(
                    action=KafkaActuatorActionEnum.installManager.value, host=self.data["new_nodes"]["broker"][0]["ip"]
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
                    manager_ip=self.data["new_nodes"]["broker"][0]["ip"],
                    manager_port=ManagerDefaultPort.KAFKA_MANAGER,
                )
                kafka_pipeline.add_act(
                    act_name=_("更新manager实例信息"),
                    act_component_code=BigdataManagerComponent.code,
                    kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
                )

            # 更新DNS
            dns_kwargs = DnsKwargs(
                bk_cloud_id=self.data["bk_cloud_id"],
                dns_op_type=DnsOpType.UPDATE,
                add_domain_name=self.data["domain"],
                dns_op_exec_port=self.data["port"],
            )
            kafka_pipeline.add_act(
                act_name=_("更新集群域名"),
                act_component_code=KafkaDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
            )

            # 迁移数据
            exclude_brokers = [broker["ip"] for broker in self.data["old_nodes"]["broker"]]
            new_brokers = [broker["ip"] for broker in self.data["new_nodes"]["broker"]]
            act_kwargs.exec_ip = self.data["new_nodes"]["broker"][:1]
            act_kwargs.template = act_payload.get_shrink_payload(
                action=KafkaActuatorActionEnum.ReplaceBroker.value, host=exclude_brokers, new_host=new_brokers
            )
            kafka_pipeline.add_act(
                act_name=_("Kafka搬迁数据"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 检查搬迁进度
            act_kwargs.template = act_payload.get_shrink_payload(
                action=KafkaActuatorActionEnum.CheckReassign.value, host=exclude_brokers
            )
            kafka_pipeline.add_act(
                act_name=_("Kafka检查搬迁进度"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 下架broker
            sub_pipelines = []
            for broker in self.data["old_nodes"]["broker"]:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
                act_kwargs.exec_ip = [broker]
                act_kwargs.template = get_base_payload(
                    action=KafkaActuatorActionEnum.StopProcess.value, host=broker["ip"]
                )
                ip = broker["ip"]
                sub_pipeline.add_act(
                    act_name=_("停止进程-{}").format(ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                act_kwargs.template = get_base_payload(
                    action=KafkaActuatorActionEnum.CleanData.value, host=broker["ip"]
                )
                sub_pipeline.add_act(
                    act_name=_("节点清理-{}").format(ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("下架broker-{}子流程").format(ip)))
            kafka_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        kafka_pipeline.add_act(
            act_name=_("更新DBMeta元信息"), act_component_code=KafkaDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        kafka_pipeline.run_pipeline()
