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

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService


class RenameDatabaseConfirmEmptyFromService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        ip = global_data["ip"]
        port = global_data["port"]

        for j in global_data["jobs"]:
            from_db = j["from_database"]

            # 只能确认源库的表是不是都没了
            # 其他的比如触发器, 存储过程是用 db actor 迁移, 源库里面肯定还在
            confirm_empty_res = DRSApi.rpc(
                {
                    "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                    "cmds": [
                        "select TABLE_NAME from information_schema.TABLES where TABLE_SCHEMA='{}'".format(from_db),
                    ],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )
            self.log_info(
                "[{}] confirm empty from database response: {}".format(kwargs["node_name"], confirm_empty_res)
            )
            if confirm_empty_res[0]["error_msg"]:
                self.log_error(
                    "[{}] confirm emtpy from database on {}{}{} failed: {}".format(
                        kwargs["node_name"], ip, IP_PORT_DIVIDER, port, confirm_empty_res[0]["error_msg"]
                    )
                )
                return False

            remain_tables = []
            for row in confirm_empty_res[0]["cmd_results"][0]["table_data"]:
                tbl = row["TABLE_NAME"]
                remain_tables.append(tbl)

            if remain_tables:
                self.log_error(
                    "[{}] {} tables remains in from database: {}".format(
                        kwargs["node_name"], len(remain_tables), remain_tables
                    )
                )
                return False

        self.log_info(_("确认源数据库已空完成"))
        return True


class RenameDatabaseConfirmEmptyFromComponent(Component):
    name = __name__
    code = "rename_database_confirm_empty_from"
    bound_service = RenameDatabaseConfirmEmptyFromService
