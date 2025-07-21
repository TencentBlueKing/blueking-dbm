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

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.doris.resource_db_meta import DorisResourceDBMeta

logger = logging.getLogger("flow")


class DorisResourceMetaService(BaseService):
    """
    根据单据类型来更新cmdb
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")
        doris_meta = DorisResourceDBMeta(ticket_data=global_data, trans_data=trans_data)

        # 根据kwargs里的单据类型调用不同方法
        result = doris_meta.write(kwargs["res_op_type"])
        self.log_info("Doris Resource DBMeta write successfully")

        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class DorisResourceMetaComponent(Component):
    name = __name__
    code = "doris_resource_meta"
    bound_service = DorisResourceMetaService
