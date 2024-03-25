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
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName, ReqType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import DorisRoleEnum, LevelInfoEnum, NameSpaceEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.doris.consts import DorisConfigEnum
from backend.flow.utils.doris.doris_act_payload import DorisActPayload
from backend.flow.utils.doris.doris_context_dataclass import DorisActKwargs
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class DorisBaseFlow(object):
    """
    Doris Flow基类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.root_id = root_id
        self.ticket_type = data.get("ticket_type")
        self.cluster_type = ClusterType.Doris.value
        self.created_by = data.get("created_by")
        self.ip_source = data.get("ip_source")
        self.uid = data.get("uid")
        self.bk_biz_id = data.get("bk_biz_id")
        self.nodes = data.get("nodes")
        # 仅 IP来源为资源池时，会有传值
        self.resource_spec = data.get("resource_spec")
        if self.ticket_type == TicketType.DORIS_APPLY:
            self.cluster_id = -1
            self.cluster_name = data.get("cluster_name")
            self.db_version = data.get("db_version")
            self.domain = data.get("domain")
            self.http_port = data.get("http_port")
            self.query_port = data.get("query_port")
            self.bk_cloud_id = data.get("bk_cloud_id")

            # 从dbconfig获取配置信息
            dbconfig = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(self.bk_biz_id),
                    "level_name": LevelName.APP,
                    "level_value": str(self.bk_biz_id),
                    "conf_file": self.db_version,
                    "conf_type": ConfType.DBCONF,
                    "namespace": NameSpaceEnum.Doris,
                    "format": FormatType.MAP_LEVEL,
                }
            )
            self.doris_config = dbconfig["content"]
            self.be_conf = self.doris_config[DorisConfigEnum.Backend]
            self.fe_conf = self.doris_config[DorisConfigEnum.Frontend]

            self.username = data.get("username")
            self.password = data.get("password")
        else:
            self.cluster_id = data.get("cluster_id")
            cluster = Cluster.objects.get(id=self.cluster_id)
            self.cluster_name = cluster.name
            masters = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.DORIS_FOLLOWER)
            if not masters:
                logger.info("found 0 master node")
                raise Exception(f"the cluster({self.cluster_id}, {self.cluster_name}) has no master node")
            self.db_version = cluster.major_version
            self.domain = cluster.immute_domain
            self.http_port = masters.first().port
            self.bk_cloud_id = cluster.bk_cloud_id

            # 从dbconfig获取配置信息
            dbconfig = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(self.bk_biz_id),
                    "level_name": LevelName.CLUSTER,
                    "level_value": self.domain,
                    "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
                    "conf_file": self.db_version,
                    "conf_type": ConfType.DBCONF,
                    "namespace": NameSpaceEnum.Doris,
                    "format": FormatType.MAP_LEVEL,
                    "method": ReqType.GENERATE_AND_PUBLISH,
                }
            )
            self.doris_config = dbconfig["content"]
            self.be_conf = self.doris_config[DorisConfigEnum.Backend]
            self.fe_conf = self.doris_config[DorisConfigEnum.Frontend]
            self.http_port = self.doris_config[DorisConfigEnum.Frontend]["http_port"]
            self.query_port = self.doris_config[DorisConfigEnum.Frontend]["query_port"]

            auth_info = PayloadHandler.get_bigdata_auth_by_cluster(cluster, 0)
            self.username = auth_info["username"]
            self.password = auth_info["password"]
            self.username = "username"
            self.password = "password"
            self.master_ips = [master.machine.ip for master in masters]

    def get_flow_base_data(self) -> dict:
        flow_data = {
            "bk_cloud_id": self.bk_cloud_id,
            "bk_biz_id": self.bk_biz_id,
            "ticket_type": self.ticket_type,
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "ip_source": self.ip_source,
            "db_version": self.db_version,
            "username": self.username,
            "password": self.password,
            "http_port": self.http_port,
            "query_port": self.query_port,
            "uid": self.uid,
            "created_by": self.created_by,
            "domain": self.domain,
            "fe_conf": self.fe_conf,
            "be_conf": self.be_conf,
            "resource_spec": self.resource_spec,
        }
        return flow_data

    def __get_flow_data(self) -> dict:
        pass

    def make_meta_host_map(self, data: dict) -> dict:
        host_map = {}
        for role in self.nodes:
            ips = [node["ip"] for node in self.nodes[role]]
            host_map[role] = ips

        return host_map

    def get_all_node_ips_in_dbmeta(self) -> list:
        cluster = Cluster.objects.get(id=self.cluster_id)
        storage_ips = list(set(StorageInstance.objects.filter(cluster=cluster).values_list("machine__ip", flat=True)))
        return storage_ips

    def new_common_sub_flows(self, act_kwargs: DorisActKwargs, data: dict) -> list:
        # """
        # 新增节点common操作sub_flow 数组
        # 包括
        #     节点初始化
        #     解压缩介质包
        #     渲染集群配置
        #     安装supervisor
        # 操作
        # """
        sub_pipelines = []
        for role, role_nodes in self.nodes.items():
            for node in role_nodes:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
                ip = node["ip"]
                # 节点初始化
                act_kwargs.get_doris_payload_func = DorisActPayload.get_sys_init_payload.__name__
                act_kwargs.doris_role = role
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("节点初始化-{}").format(ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                # 解压缩
                act_kwargs.get_doris_payload_func = DorisActPayload.get_decompress_doris_pkg_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("解压缩介质包-{}").format(ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                # 渲染集群配置
                act_kwargs.get_doris_payload_func = DorisActPayload.get_render_config_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("渲染集群配置-{}").format(ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                # 安装supervisor
                act_kwargs.get_doris_payload_func = DorisActPayload.get_install_supervisor_payload.__name__
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("安装supervisor-{}").format(ip),
                    act_component_code=ExecuteDorisActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("安装Doris {}-{}子流程").format(role, ip)))

        return sub_pipelines

    # 新加入frontend(follower/observer)节点子流程(不包括元数据更新)
    def new_fe_sub_flows(self, act_kwargs: DorisActKwargs, data: dict) -> list:
        sub_pipelines = []
        for role, role_nodes in self.nodes.items():
            if role in [DorisRoleEnum.FOLLOWER.value, DorisRoleEnum.OBSERVER.value]:
                for fe_node in role_nodes:
                    fe_ip = fe_node["ip"]
                    if data["master_fe_ip"] == fe_ip:
                        # 若为master_fe_ip 无需操作
                        continue
                    else:
                        sub_pipeline = SubBuilder(root_id=self.root_id, data=data)

                        act_kwargs.exec_ip = fe_ip
                        act_kwargs.doris_role = role
                        act_kwargs.get_doris_payload_func = DorisActPayload.get_start_fe_by_helper_payload.__name__
                        sub_pipeline.add_act(
                            act_name=_("启动初始化-{}-{}").format(role, fe_ip),
                            act_component_code=ExecuteDorisActuatorScriptComponent.code,
                            kwargs=asdict(act_kwargs),
                        )
                        act_kwargs.get_doris_payload_func = DorisActPayload.get_install_doris_payload.__name__
                        sub_pipeline.add_act(
                            act_name=_("启动-{}-{}").format(role, fe_ip),
                            act_component_code=ExecuteDorisActuatorScriptComponent.code,
                            kwargs=asdict(act_kwargs),
                        )
                        sub_pipelines.append(
                            sub_pipeline.build_sub_process(sub_name=_("安装DorisFE {}-{}子流程").format(role, fe_ip))
                        )

        return sub_pipelines

    # 新加入backend(hot/cold)节点子流程(不包括元数据更新)
    def new_bew_sub_acts(self, act_kwargs: DorisActKwargs, data: dict) -> list:
        be_acts = []
        for role, role_nodes in self.nodes.items():
            if role in [DorisRoleEnum.COLD.value, DorisRoleEnum.HOT.value]:
                for be_node in role_nodes:
                    act_kwargs.exec_ip = be_node["ip"]
                    act_kwargs.doris_role = role
                    act_kwargs.get_doris_payload_func = DorisActPayload.get_install_doris_payload.__name__
                    be_act = {
                        "act_name": _("启动DorisBE-{}-{}").format(role, be_node["ip"]),
                        "act_component_code": ExecuteDorisActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                    be_acts.append(be_act)
        return be_acts


def get_node_ips_in_ticket_by_role(data: dict, role: str) -> list:
    if role not in data.get("nodes"):
        return []
    return [node["ip"] for node in data["nodes"][role]]


def get_all_node_ips_in_ticket(data: dict) -> list:
    ips = []
    for role in data.get("nodes"):
        ips.extend(get_node_ips_in_ticket_by_role(data, role))
    return ips


def fe_exists_in_ticket(data: dict) -> bool:
    return DorisRoleEnum.FOLLOWER in data["nodes"] or DorisRoleEnum.OBSERVER in data["nodes"]


def be_exists_in_ticket(data: dict) -> bool:
    return DorisRoleEnum.HOT in data["nodes"] or DorisRoleEnum.COLD in data["nodes"]
