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
from backend.flow.utils.sqlserver.sqlserver_db_function import check_sqlserver_db_exist

logger = logging.getLogger("flow")


class CheckDBExistService(BaseService):
    """
    判断数据库是否存在
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        is_no_err = True
        res = check_sqlserver_db_exist(cluster_id=kwargs["cluster_id"], check_dbs=kwargs["check_dbs"])
        for info in res:
            if not info["is_exists"]:
                is_no_err = False
                logger.error(f"[{info['name']}] db not exist, check")

        return is_no_err


class CheckDBExistComponent(Component):
    name = __name__
    code = "sqlserver_check_db_exist"
    bound_service = CheckDBExistService
