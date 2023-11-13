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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import LevelName, OpType, ReqType
from backend.flow.consts import ConfigTypeEnum, LevelInfoEnum, NameSpaceEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class WriteBackEsConfigService(BaseService):
    """
    回写集群配置到dbconfig
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")

        conf_items = [
            {"conf_name": "username", "conf_value": global_data["username"], "op_type": OpType.UPDATE},
            {"conf_name": "password", "conf_value": global_data["password"], "op_type": OpType.UPDATE},
        ]

        DBConfigApi.upsert_conf_item(
            {
                "conf_file_info": {
                    "conf_file": global_data["db_version"],
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": NameSpaceEnum.Es,
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
        self.log_info("successfully write back es config to dbconfig")
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class WriteBackEsConfigComponent(Component):
    name = __name__
    code = "write_back_es_config"
    bound_service = WriteBackEsConfigService
