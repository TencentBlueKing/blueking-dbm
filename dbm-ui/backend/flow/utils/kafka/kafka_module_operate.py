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
from backend.db_meta.enums import MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator
from backend.ticket.constants import TicketType


class KafkaCCTopoOperator(CCTopoOperator):
    db_type = DBType.Kafka.value

    def generate_custom_labels(self, ins: Union[StorageInstance, ProxyInstance]) -> dict:
        # 用于采集Kafka消费延迟的标签
        brokers = ""
        broker_port = str(self.ticket_data["port"])

        if self.ticket_data["ticket_type"] == TicketType.KAFKA_REPLACE:
            # 若替换的是broker
            if self.ticket_data["new_nodes"].get("broker"):
                brokers = self.ticket_data["new_nodes"]["broker"][0]["ip"]
            # 若替换的是zk
            if self.ticket_data["new_nodes"].get("zookeeper"):
                brokers = self.ticket_data["broker_ip"][0]
        else:
            brokers = self.ticket_data["nodes"]["broker"][0]["ip"]

        return {
            "brokers": brokers,
            "broker_port": broker_port,
        }

    def init_instances_service(self, machine_type, instances=None):
        """
        KAFKA 的 zk 只需要一个采集器，采集消费延迟的数据
        """
        if machine_type != MachineType.ZOOKEEPER.value:
            # 非 zk 节点，使用默认方法创建服务实例
            super(KafkaCCTopoOperator, self).init_instances_service(machine_type, instances)
            return

        # machine_type==zk, 消费延迟，仅需一个服务实例
        self.init_unique_service(machine_type)
