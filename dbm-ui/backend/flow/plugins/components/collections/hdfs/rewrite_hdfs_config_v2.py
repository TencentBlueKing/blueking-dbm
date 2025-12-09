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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.hdfs.hdfs_context_dataclass as flow_context
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import LevelName, OpType, ReqType
from backend.flow.consts import ConfigTypeEnum, LevelInfoEnum, NameSpaceEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class WriteHdfsConfigV2Service(BaseService):
    """
    部署集群后 回写集群配置到dbconfig 不包含密码服务
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        conf_items = []
        nn_domain = global_data["nn_domain"]
        # 遍历 nn_domain 映射，生成 nn1_ip/nn2_ip 和 nn1_host/nn2_host 配置项
        for ip, domain in nn_domain.items():
            # 取域名前缀（nn1 或 nn2）
            prefix = domain[:3]
            # 添加 IP 配置项，如 nn1_ip -> x.x.x.x
            conf_items.append({"conf_name": f"{prefix}_ip", "conf_value": ip, "op_type": OpType.UPDATE})
            # 添加 host 配置项，如 nn1_host -> nn1.domain
            conf_items.append({"conf_name": f"{prefix}_host", "conf_value": domain, "op_type": OpType.UPDATE})

        conf_items.append(
            {"conf_name": "http_port", "conf_value": str(global_data["http_port"]), "op_type": OpType.UPDATE}
        )
        conf_items.append(
            {"conf_name": "rpc_port", "conf_value": str(global_data["rpc_port"]), "op_type": OpType.UPDATE}
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

        self.log_info("successfully write back hdfs config to dbconfig")
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="command result", key="result", type="str")]


class WriteHdfsConfigV2Component(Component):
    name = __name__
    code = "write_hdfs_config_v2"
    bound_service = WriteHdfsConfigV2Service
