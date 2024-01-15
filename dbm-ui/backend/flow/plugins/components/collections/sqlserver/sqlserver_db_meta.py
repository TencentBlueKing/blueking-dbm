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

from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta

logger = logging.getLogger("flow")


class SqlserverDBMetaService(BaseService):
    """
    根据sqlserver单据类型来更新cmdb
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        meta = SqlserverDBMeta(global_data=global_data, trans_data=trans_data)

        result = getattr(meta, kwargs.get("db_meta_class_func"))()

        self.log_info("successfully")
        data.outputs.ext_result = result
        return result


class SqlserverDBMetaComponent(Component):
    name = __name__
    code = "sqlserver_db_meta"
    bound_service = SqlserverDBMetaService
