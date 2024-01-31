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
from backend.flow.utils.sqlserver.sqlserver_db_function import exec_instance_app_login

logger = logging.getLogger("flow")


class ExecSqlserverLoginService(BaseService):
    """
    操作Sqlserver的业务账号，只有禁用和启动操作
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        if exec_instance_app_login(kwargs["cluster_id"], kwargs["exec_mode"]):
            self.log_info(f"exec app-logins-[{kwargs['exec_mode']}] successfully")
            return True

        return False


class ExecSqlserverLoginComponent(Component):
    name = __name__
    code = "exec_sqlserver_login"
    bound_service = ExecSqlserverLoginService
