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
from typing import Union

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator
from backend.flow.utils.hdfs.consts import (
    DATANODE_DEFAULT_HTTP_PORT,
    DATANODE_DEFAULT_PORT,
    DATANODE_DEFAULT_RPC_PORT,
    NAME_NODE_DEFAULT_PORT,
)


class HdfsCCTopoOperator(CCTopoOperator):
    db_type = DBType.Hdfs.value

    def generate_custom_labels(self, ins: Union[StorageInstance, ProxyInstance]) -> dict:
        # 定义注册HDFS服务监控实例需要的labels标签结构

        rpc_port = DATANODE_DEFAULT_RPC_PORT
        jmx_http_port = DATANODE_DEFAULT_HTTP_PORT
        service_rpc_port = DATANODE_DEFAULT_PORT

        if ins.instance_role == InstanceRole.HDFS_NAME_NODE.value:
            rpc_port = self.ticket_data.get("rpc_port", rpc_port)
            jmx_http_port = self.ticket_data.get("http_port", jmx_http_port)
            service_rpc_port = NAME_NODE_DEFAULT_PORT

        return {
            "instance_name": ins.name,
            "rpc_port": str(rpc_port),
            "jmx_http_port": str(jmx_http_port),
            "service_rpc_port": str(service_rpc_port),
        }

    def init_instances_service(self, machine_type, instances=None):
        """
        1. 所有 HDFS_DATANODE 都需要添加服务实例并监控
        2. HDFS_MASTER 包括 NAME_NODE，ZOOKEEPER，JOURNAL_NODE
        3. 只有 NAME_NODE 需要添加服务实例并监控
        """
        if machine_type == MachineType.HDFS_MASTER:
            instances = filter(lambda ins: ins.instance_role == InstanceRole.HDFS_NAME_NODE, instances)
        super(HdfsCCTopoOperator, self).init_instances_service(machine_type, instances)
