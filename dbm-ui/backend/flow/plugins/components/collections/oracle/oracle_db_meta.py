# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Oracle DBMeta 通用组件, 命名与 sqlserver_db_meta / mysql_db_meta 对齐,
承载日常运维单据(如 add_slave)的元数据写入职责。
"""
import logging
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.oracle.oracle_db_meta import OracleDBMeta

logger = logging.getLogger("flow")


class OracleDBMetaService(BaseService):
    """根据单据类型执行元数据写入"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        result = OracleDBMeta(info=kwargs).action()
        self.log_info("oracle db_meta operate successfully")
        data.outputs["trans_data"] = trans_data
        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class OracleDBMetaComponent(Component):
    name = __name__
    code = "oracle_db_meta"
    bound_service = OracleDBMetaService
