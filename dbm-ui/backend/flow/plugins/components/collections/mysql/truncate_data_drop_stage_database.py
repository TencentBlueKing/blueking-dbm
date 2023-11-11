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


class TruncateDataDropStageDatabaseService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        ip = global_data["ip"]
        port = global_data["port"]

        old_new_map = trans_data.old_new_map

        drop_db_cmds = []
        for old_db in old_new_map:
            drop_db_cmds.append("drop database if exists `{}`".format(old_new_map[old_db]))

        drop_db_res = DRSApi.rpc(
            {
                "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                "cmds": drop_db_cmds,
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )

        self.log_info("[{}] drop stage db response: {}".format(kwargs["node_name"], drop_db_res))

        self.log_info(_("删除备份库完成"))
        data.outputs["trans_data"] = trans_data
        return True


class TruncateDataDropStageDatabaseComponent(Component):
    name = __name__
    code = "truncate_data_drop_stage_database"
    bound_service = TruncateDataDropStageDatabaseService
