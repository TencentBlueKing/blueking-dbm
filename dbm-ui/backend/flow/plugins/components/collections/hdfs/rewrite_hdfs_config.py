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
import logging
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.hdfs.hdfs_context_dataclass as flow_context
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import LevelName, OpType, ReqType
from backend.components.mysql_priv_manager.client import MySQLPrivManagerApi
from backend.flow.consts import ConfigTypeEnum, LevelInfoEnum, MySQLPrivComponent, NameSpaceEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class WriteBackHdfsConfigService(BaseService):
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
        if global_data["ticket_type"] == TicketType.HDFS_REPLACE.value:
            nn1_ip = trans_data.cur_nn1_ip
            nn2_ip = trans_data.cur_nn2_ip
            all_ip_hosts = trans_data.cur_all_ip_hosts
        else:
            nn1_ip = global_data["nn1_ip"]
            nn2_ip = global_data["nn2_ip"]
            all_ip_hosts = global_data["all_ip_hosts"]

        conf_items.append({"conf_name": "nn1_ip", "conf_value": nn1_ip, "op_type": OpType.UPDATE})
        conf_items.append({"conf_name": "nn2_ip", "conf_value": nn2_ip, "op_type": OpType.UPDATE})
        conf_items.append({"conf_name": "nn1_host", "conf_value": all_ip_hosts[nn1_ip], "op_type": OpType.UPDATE})
        conf_items.append({"conf_name": "nn2_host", "conf_value": all_ip_hosts[nn2_ip], "op_type": OpType.UPDATE})
        conf_items.append(
            {"conf_name": "http_port", "conf_value": str(global_data["http_port"]), "op_type": OpType.UPDATE}
        )
        conf_items.append(
            {"conf_name": "rpc_port", "conf_value": str(global_data["rpc_port"]), "op_type": OpType.UPDATE}
        )
        conf_items.append({"conf_name": "username", "conf_value": "root", "op_type": OpType.UPDATE})
        conf_items.append(
            {"conf_name": "password", "conf_value": global_data["haproxy_passwd"], "op_type": OpType.UPDATE}
        )
        DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": global_data["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": NameSpaceEnum.Hdfs,
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

        # Writing to password service
        self.log_info("Writing password to service")
        query_params = {
            "instances": [
                {
                    "ip": global_data["domain"],
                    "port": 0,
                    "bk_cloud_id": global_data["bk_cloud_id"],
                }
            ],
            "password": base64.b64encode(str(global_data["password"]).encode("utf-8")).decode("utf-8"),
            "username": "root",
            "component": NameSpaceEnum.Hdfs,
            "operator": "admin",
        }
        MySQLPrivManagerApi.modify_password(params=query_params)

        self.log_info("successfully write back hdfs config to dbconfig")
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="command result", key="result", type="str")]


class WriteBackHdfsConfigComponent(Component):
    name = __name__
    code = "write_back_hdfs_config"
    bound_service = WriteBackHdfsConfigService
