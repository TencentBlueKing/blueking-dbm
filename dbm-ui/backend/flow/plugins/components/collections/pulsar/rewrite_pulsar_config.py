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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.pulsar.pulsar_context_dataclass as flow_context
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import LevelName, OpType, ReqType
from backend.flow.consts import ConfigTypeEnum, LevelInfoEnum, NameSpaceEnum, PulsarRoleEnum
from backend.flow.engine.bamboo.scene.pulsar.pulsar_base_flow import get_zk_id_from_host_map
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.pulsar.consts import PulsarConfigEnum
from backend.flow.utils.pulsar.pulsar_context_dataclass import PulsarApplyContext
from backend.ticket.constants import TicketType


class WriteBackPulsarConfigService(BaseService):
    """
    回写集群配置到dbconfig中，扩容时需要
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        conf_items = []
        if global_data["ticket_type"] == TicketType.PULSAR_APPLY.value:
            conf_items = [
                {
                    "conf_name": PulsarConfigEnum.ManagerUserName,
                    "conf_value": global_data["username"],
                    "op_type": OpType.UPDATE,
                },
                {
                    "conf_name": PulsarConfigEnum.ManagerPassword,
                    "conf_value": global_data["password"],
                    "op_type": OpType.UPDATE,
                },
                {"conf_name": PulsarConfigEnum.Port, "conf_value": str(global_data["port"]), "op_type": OpType.UPDATE},
                {
                    "conf_name": PulsarConfigEnum.NumPartitions,
                    "conf_value": str(global_data["partition_num"]),
                    "op_type": OpType.UPDATE,
                },
                {
                    "conf_name": PulsarConfigEnum.EnsembleSize,
                    "conf_value": str(global_data["ensemble_size"]),
                    "op_type": OpType.UPDATE,
                },
                {
                    "conf_name": PulsarConfigEnum.WriteQuorum,
                    "conf_value": str(global_data["replication_num"]),
                    "op_type": OpType.UPDATE,
                },
                {
                    "conf_name": PulsarConfigEnum.AckQuorum,
                    "conf_value": str(global_data["ack_quorum"]),
                    "op_type": OpType.UPDATE,
                },
                {
                    "conf_name": PulsarConfigEnum.RetentionTime,
                    "conf_value": str(global_data["retention_time"]),
                    "op_type": OpType.UPDATE,
                },
            ]
            token = getattr(trans_data, PulsarApplyContext.get_new_token_var_name())["token"]
            conf_items.append(
                {
                    "conf_name": PulsarConfigEnum.ClientAuthenticationParameters,
                    "conf_value": f"token:{token}",
                    "op_type": OpType.UPDATE,
                }
            )
            for i, zk_node in enumerate(global_data["nodes"][PulsarRoleEnum.ZooKeeper]):
                conf_items.append(
                    {
                        "conf_name": f"zk_ip_{i}",
                        "conf_value": zk_node["ip"],
                        "op_type": OpType.UPDATE,
                    }
                )
        elif global_data["ticket_type"] == TicketType.PULSAR_REPLACE.value:
            # 替换类型更新dbconfig时 只更新zk_id 对应 ip
            for ip in kwargs["zk_host_map"].keys():
                zk_my_id = get_zk_id_from_host_map(kwargs["zk_host_map"], ip)
                conf_items.append(
                    {
                        "conf_name": f"zk_ip_{zk_my_id}",
                        "conf_value": ip,
                        "op_type": OpType.UPDATE,
                    }
                )
        DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": global_data["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": NameSpaceEnum.Pulsar,
                },
                "conf_items": conf_items,
                "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
                "confirm": 0,
                "req_type": ReqType.SAVE_AND_PUBLISH,
                "bk_biz_id": str(global_data["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": global_data["domain"],
            }
        )
        self.log_info("successfully write back pulsar config to dbconfig")
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="command result", key="result", type="str")]


class WriteBackPulsarConfigComponent(Component):
    name = __name__
    code = "write_back_pulsar_config"
    bound_service = WriteBackPulsarConfigService
