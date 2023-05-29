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


class TruncateDataCreateStageDatabaseService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        ip = global_data["ip"]
        port = global_data["port"]

        sql_cmds = []
        for db in trans_data.old_new_map:
            create_stage_db_cmd = "create database if not exists `{}`".format(trans_data.old_new_map[db])
            sql_cmds.append(create_stage_db_cmd)

        create_stage_db_res = DRSApi.rpc(
            {
                "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                "cmds": sql_cmds,
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )
        self.log_info("[{}] create stage database response: {}".format(kwargs["node_name"], create_stage_db_res))
        if create_stage_db_res[0]["error_msg"]:
            self.log_error(
                "[{}] create stage database on {}{}{} failed: {}".format(
                    kwargs["node_name"], ip, IP_PORT_DIVIDER, port, create_stage_db_res[0]["error_msg"]
                )
            )
            data.outputs.ext_result = False
            return False

        self.log_info(_("建立备份库完成"))

        data.outputs["trans_data"] = trans_data
        return True


class TruncateDataCreateStageDatabaseComponent(Component):
    name = __name__
    code = "create_truncate_data_stage_db"
    bound_service = TruncateDataCreateStageDatabaseService
