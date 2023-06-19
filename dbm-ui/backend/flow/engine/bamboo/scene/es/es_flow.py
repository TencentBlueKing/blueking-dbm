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
from typing import Dict, Optional

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName, ReqType
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import ESRoleEnum, LevelInfoEnum, NameSpaceEnum
from backend.flow.utils.es.es_context_dataclass import EsApplyContext
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class EsFlow(object):
    """
    Es Flow基类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.root_id = root_id
        self.ticket_type = data.get("ticket_type")
        self.cluster_type = ClusterType.Es.value
        self.created_by = data.get("created_by")
        self.ip_source = data.get("ip_source")
        self.uid = data.get("uid")
        self.bk_biz_id = data.get("bk_biz_id")
        self.nodes = data.get("nodes")
        # 仅 IP来源为资源池时，会有传值
        self.resource_spec = data.get("resource_spec")
        if self.ticket_type == TicketType.ES_APPLY:
            self.cluster_id = -1
            self.cluster_name = data.get("cluster_name")
            self.db_version = data.get("db_version")
            self.domain = data.get("domain")
            self.http_port = data.get("http_port")
            self.bk_cloud_id = data.get("bk_cloud_id")

            # 从dbconfig获取配置信息
            dbconfig = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(self.bk_biz_id),
                    "level_name": LevelName.APP,
                    "level_value": str(self.bk_biz_id),
                    "conf_file": self.db_version,
                    "conf_type": ConfType.DBCONF,
                    "namespace": NameSpaceEnum.Es,
                    "format": FormatType.MAP_LEVEL,
                }
            )
            self.es_config = dbconfig["content"]
            self.username = data.get("username")
            self.password = data.get("password")
        else:
            self.cluster_id = data.get("cluster_id")
            cluster = Cluster.objects.get(id=self.cluster_id)
            self.cluster_name = cluster.name
            masters = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_MASTER)
            if not masters:
                logger.info("found 0 master node")
                raise Exception(f"the cluster({self.cluster_id}, {self.cluster_name}) has no master node")
            self.db_version = cluster.major_version
            self.domain = cluster.immute_domain
            self.http_port = masters.first().port
            self.bk_cloud_id = cluster.bk_cloud_id

            # 从dbconfig获取配置信息
            dbconfig = DBConfigApi.get_instance_config(
                {
                    "bk_biz_id": str(self.bk_biz_id),
                    "level_name": LevelName.CLUSTER,
                    "level_value": self.domain,
                    "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
                    "conf_file": self.db_version,
                    "conf_type": ConfType.DBCONF,
                    "namespace": NameSpaceEnum.Es,
                    "format": FormatType.MAP_LEVEL,
                    "method": ReqType.GENERATE_AND_PUBLISH,
                }
            )
            self.es_config = dbconfig["content"]
            # 从dbconfig获取用户名和密码
            self.username = self.es_config["username"]
            self.password = self.es_config["password"]
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
            "uid": self.uid,
            "created_by": self.created_by,
            "domain": self.domain,
            "es_config": self.es_config,
            "resource_spec": self.resource_spec,
        }
        return flow_data

    def __get_flow_data(self) -> dict:
        pass

    def get_all_node_ips_in_dbmeta(self) -> list:
        cluster = Cluster.objects.get(id=self.cluster_id)
        storage_ips = list(set(StorageInstance.objects.filter(cluster=cluster).values_list("machine__ip", flat=True)))
        return storage_ips

    def get_node_in_dbmeta_preferred_hot(self, exclude_ips=None) -> str:
        if exclude_ips is None:
            exclude_ips = []
        order_list = [
            InstanceRole.ES_DATANODE_HOT.value,
            InstanceRole.ES_DATANODE_COLD.value,
            InstanceRole.ES_CLIENT.value,
            InstanceRole.ES_MASTER.value,
        ]
        cluster = Cluster.objects.get(id=self.cluster_id)
        for role in order_list:
            ip_list = list(
                set(
                    StorageInstance.objects.filter(cluster=cluster, instance_role=role)
                    .exclude(machine__ip__in=exclude_ips)
                    .values_list("machine__ip", flat=True)
                )
            )
            if ip_list:
                return ip_list[0]
        return ""


def get_node_ips_in_ticket_by_role(data: dict, role: str) -> list:
    if role not in data.get("nodes"):
        return []
    return [node["ip"] for node in data["nodes"][role]]


def get_all_node_ips_in_ticket(data: dict) -> list:
    ips = []
    for role in data.get("nodes"):
        ips.extend(get_node_ips_in_ticket_by_role(data, role))
    return ips


def get_node_in_ticket_preferred_hot(data: dict) -> str:
    order_list = [ESRoleEnum.HOT.value, ESRoleEnum.COLD.value, ESRoleEnum.CLIENT.value, ESRoleEnum.MASTER.value]
    for role in order_list:
        if data["nodes"].get(role):
            return data["nodes"][role][0]["ip"]


def get_machine_list_in_ticket(data: dict) -> list:
    machine_list = []
    for role in data["nodes"]:
        if role == ESRoleEnum.HOT.value:
            machine_list.append(
                {
                    "machine_type": MachineType.ES_DATANODE.value,
                    "ips_var_name": EsApplyContext.get_new_hot_ips_var_name(),
                }
            )
        elif role == ESRoleEnum.COLD.value:
            machine_list.append(
                {
                    "machine_type": MachineType.ES_DATANODE.value,
                    "ips_var_name": EsApplyContext.get_new_cold_ips_var_name(),
                }
            )
        elif role == ESRoleEnum.MASTER.value:
            machine_list.append(
                {
                    "machine_type": MachineType.ES_MASTER.value,
                    "ips_var_name": EsApplyContext.get_new_master_ips_var_name(),
                }
            )
        elif role == ESRoleEnum.CLIENT.value:
            machine_list.append(
                {
                    "machine_type": MachineType.ES_CLIENT.value,
                    "ips_var_name": EsApplyContext.get_new_client_ips_var_name(),
                }
            )
    return machine_list
