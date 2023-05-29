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
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService


class RenameDatabaseDropFromService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        ip = global_data["ip"]
        port = global_data["port"]

        for j in global_data["jobs"]:
            from_database = j["from_database"]

            drop_from_db_res = DRSApi.rpc(
                {
                    "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                    "cmds": ["drop database if exists `{}`".format(from_database)],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )
            self.log_info("[{}] drop from database response: {}".format(kwargs["node_name"], drop_from_db_res))
            if drop_from_db_res[0]["error_msg"]:
                self.log_error(
                    "[{}] drop from database {} on {}{}{} failed: {}".format(
                        kwargs["node_name"], from_database, ip, IP_PORT_DIVIDER, port, drop_from_db_res[0]["error_msg"]
                    )
                )
                data.outputs.ext_result = False
                return False

        self.log_info(_("删除源数据库完成"))
        data.outputs.ext_result = True
        return True


class RenameDatabaseDropFromComponent(Component):
    name = __name__
    code = "rename_database_drop_from"
    bound_service = RenameDatabaseDropFromService
