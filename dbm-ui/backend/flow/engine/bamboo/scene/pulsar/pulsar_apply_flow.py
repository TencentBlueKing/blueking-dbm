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
import copy
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DnsOpType, ManagerOpType, ManagerServiceType, MediumFileTypeEnum, PulsarRoleEnum
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import sa_init_machine_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.pulsar.pulsar_base_flow import PulsarBaseFlow, get_all_node_ips_in_ticket
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.pulsar.exec_actuator_script import (
    ExecutePulsarActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.pulsar.get_pulsar_payload import GetPulsarActPayloadComponent
from backend.flow.plugins.components.collections.pulsar.get_pulsar_resource import GetPulsarResourceComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_db_meta import PulsarDBMetaComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_dns_manage import PulsarDnsManageComponent
from backend.flow.plugins.components.collections.pulsar.pulsar_zk_dns_manage import PulsarZkDnsManageComponent
from backend.flow.plugins.components.collections.pulsar.rewrite_pulsar_config import WriteBackPulsarConfigComponent
from backend.flow.plugins.components.collections.pulsar.trans_files import TransFileComponent
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.pulsar.consts import (
    PULSAR_AUTH_CONF_TARGET_PATH,
    PULSAR_KEY_PATH_LIST_ZOOKEEPER,
    PULSAR_MANAGER_WEB_PORT,
    PULSAR_ZOOKEEPER_SERVICE_PORT,
)
from backend.flow.utils.pulsar.pulsar_act_payload import PulsarActPayload
from backend.flow.utils.pulsar.pulsar_context_dataclass import (
    DnsKwargs,
    PulsarActKwargs,
    PulsarApplyContext,
    TransFilesKwargs,
    ZkDnsKwargs,
)

logger = logging.getLogger("flow")


class PulsarApplyFlow(PulsarBaseFlow):
    """
    构建Pulsar申请流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)

        self.data = data
        # 初始化集群默认仅取任一台ZK做初始化操作
        self.init_cluster_ip = self.nodes[PulsarRoleEnum.ZooKeeper][0]["ip"]
        # 搭建Pulsar Manager IP
        self.manager_ip = self.nodes[PulsarRoleEnum.ZooKeeper][0]["ip"]

    def deploy_pulsar_flow(self):
        """
        定义部署Pulsar集群
        """
        pulsar_flow_data = self.__get_apply_flow_data(self.data)

        pulsar_pipeline = Builder(root_id=self.root_id, data=pulsar_flow_data)
        trans_files = GetFileList(db_type=DBType.Pulsar)
        # 拼接活动节点需要的私有参数
        act_kwargs = PulsarActKwargs(bk_cloud_id=self.base_flow_data["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = PulsarApplyContext.__name__
        act_kwargs.file_list = trans_files.pulsar_apply(db_version=self.data["db_version"])

        # 获取集群部署配置
        pulsar_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetPulsarActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        # 获取机器资源
        pulsar_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetPulsarResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 增加机器初始化子流程
        all_new_ips = get_all_node_ips_in_ticket(self.data)
        pulsar_pipeline.add_sub_pipeline(
            sub_flow=sa_init_machine_sub_flow(
                uid=self.uid,
                root_id=self.root_id,
                bk_cloud_id=self.bk_cloud_id,
                bk_biz_id=self.bk_biz_id,
                init_ips=all_new_ips,
                idle_check_ips=all_new_ips,
                set_dns_ips=[],
            )
        )

        # 下发pulsar介质
        act_kwargs.exec_ip = get_all_node_ips_in_ticket(self.data)
        pulsar_pipeline.add_act(
            act_name=_("下发pulsar介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 所有节点 安装pulsar common子流程 编排
        sub_pipelines = self.new_nodes_common_sub_flow_list(act_kwargs=act_kwargs, data=pulsar_flow_data)
        pulsar_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 绑定域名与ZK_IP
        zk_dns_kwargs = ZkDnsKwargs(
            bk_cloud_id=pulsar_flow_data["bk_cloud_id"],
            dns_op_type=DnsOpType.CREATE,
            domain_name=pulsar_flow_data["domain"],
            dns_op_exec_port=PULSAR_ZOOKEEPER_SERVICE_PORT,
            zk_host_map=pulsar_flow_data["zk_host_map"],
        )
        pulsar_pipeline.add_act(
            act_name=_("添加ZK域名"),
            act_component_code=PulsarZkDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(zk_dns_kwargs)},
        )
        # 判断环境是否支持DNS解析，不支持则需要增加活动节点
        if not self.domain_resolve_supported:
            act_kwargs.exec_ip = self.manager_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_modify_hosts_payload.__name__
            broker_domain_map = copy.deepcopy(pulsar_flow_data["zk_host_map"])
            broker_domain_map[self.nodes[PulsarRoleEnum.Broker][0]["ip"]] = pulsar_flow_data["domain"]
            act_kwargs.zk_host_map = broker_domain_map
            pulsar_pipeline.add_act(
                act_name=_("仅非DNS环境使用-添加broker hosts"),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            act_kwargs.zk_host_map = None

        # 安装zookeeper
        zk_act_list = []
        for i, zk_node in enumerate(self.nodes[PulsarRoleEnum.ZooKeeper]):
            zk_ip = zk_node["ip"]
            act_kwargs.zk_my_id = i
            act_kwargs.exec_ip = zk_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_install_zookeeper_payload.__name__
            zookeeper_act = {
                "act_name": _("安装zookeeper-{}").format(zk_ip),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            zk_act_list.append(zookeeper_act)
        pulsar_pipeline.add_parallel_acts(acts_list=zk_act_list)

        dns_kwargs = DnsKwargs(
            bk_cloud_id=pulsar_flow_data["bk_cloud_id"],
            dns_op_type=DnsOpType.CREATE,
            domain_name=pulsar_flow_data["domain"],
            dns_op_exec_port=pulsar_flow_data["port"],
        )
        pulsar_pipeline.add_act(
            act_name=_("添加域名"),
            act_component_code=PulsarDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 初始化集群配置, 默认仅取任一台ZK做初始化操作
        act_kwargs.exec_ip = self.init_cluster_ip
        act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_init_cluster_payload.__name__
        pulsar_pipeline.add_act(
            act_name=_("初始化集群配置-{}".format(act_kwargs.exec_ip)),
            act_component_code=ExecutePulsarActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
            write_payload_var=PulsarApplyContext.get_new_token_var_name(),
        )

        # 分发初始化集群生成的密钥/token 到所有broker节点
        act_kwargs.file_list = PULSAR_KEY_PATH_LIST_ZOOKEEPER
        act_kwargs.exec_ip = [node["ip"] for node in self.nodes[PulsarRoleEnum.Broker]]
        trans_file_kwargs = TransFilesKwargs(
            source_ip_list=[self.init_cluster_ip],
            file_type=MediumFileTypeEnum.Server.value,
            file_target_path=PULSAR_AUTH_CONF_TARGET_PATH,
        )
        pulsar_pipeline.add_act(
            act_name=_("分发密钥及token"),
            act_component_code=TransFileComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(trans_file_kwargs)},
        )
        # 安装bookkeeper
        bookie_act_list = self.new_bookkeeper_act_list(act_kwargs)
        pulsar_pipeline.add_parallel_acts(acts_list=bookie_act_list)

        # 安装broker
        broker_act_list = self.new_broker_act_list(act_kwargs)
        pulsar_pipeline.add_parallel_acts(acts_list=broker_act_list)

        # 安装pulsar manager
        act_kwargs.exec_ip = self.manager_ip
        act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_install_manager_payload.__name__
        pulsar_pipeline.add_act(
            act_name=_("安装pulsar manager"),
            act_component_code=ExecutePulsarActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 插入pulsar manager实例信息
        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.CREATE,
            db_type=DBType.Pulsar,
            service_type=ManagerServiceType.PULSAR_MANAGER,
            manager_ip=self.manager_ip,
            manager_port=PULSAR_MANAGER_WEB_PORT,
        )
        pulsar_pipeline.add_act(
            act_name=_("插入pulsar manager实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )
        pulsar_pipeline.add_act(
            act_name=_("添加元数据到DBMeta"), act_component_code=PulsarDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        pulsar_pipeline.add_act(
            act_name=_("回写集群配置信息"), act_component_code=WriteBackPulsarConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        # 初始化 manager
        act_kwargs.exec_ip = self.manager_ip
        act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_init_manager_payload.__name__
        pulsar_pipeline.add_act(
            act_name=_("初始化pulsar manager"),
            act_component_code=ExecutePulsarActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        pulsar_pipeline.run_pipeline()

    def __get_apply_flow_data(self, data) -> dict:
        flow_data = copy.deepcopy(data)
        # 写入配置 数据保留时间 单位为 分钟
        flow_data["retention_time"] = data["retention_hours"] * 60
        # 写入配置 ensemble_size 默认为bookkeeper个数
        flow_data["ensemble_size"] = len(data["nodes"][PulsarRoleEnum.BookKeeper])

        zk_host_map = self.make_zk_host_map()
        flow_data["zk_host_map"] = zk_host_map
        # 定义zk_host字符串
        flow_data["zk_hosts_str"] = ",".join(zk_host_map.values())
        return flow_data
