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
from backend.flow.plugins.components.collections.common.base_service import BaseService


class TruncateDatabaseDropStageDBViaCtlService(BaseService):
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        old_new_map = trans_data.old_new_map
        self.log_info("[{}] truncate on spider old_new_map: {}".format(kwargs["node_name"], old_new_map))

        ctl_primary = global_data["ctl_primary"]

        sql_cmds = ["set tc_admin=1"]
        for old_db in old_new_map:
            new_db = old_new_map[old_db]
            sql_cmds.append("drop database if exists `{}`".format(new_db))

        drop_new_db_res = DRSApi.rpc(
            {"addresses": [ctl_primary], "cmds": sql_cmds, "force": False, "bk_cloud_id": kwargs["bk_cloud_id"]}
        )
        self.log_info("[{}] drop stage database response: {}".format(kwargs["node_name"], drop_new_db_res))
        if drop_new_db_res[0]["error_msg"]:
            self.log_info(
                "[{}] drop stage database on {} failed: {}".format(
                    kwargs["node_name"], ctl_primary, drop_new_db_res[0]["error_msg"]
                )
            )
            data.outputs.ext_result = False
            return False

        self.log_info(_("清理备份库完成"))
        data.outputs["trans_data"] = trans_data
        return True


class TruncateDatabaseDropStageDBViaCtlComponent(Component):
    name = __name__
    code = "truncate_database_drop_stage_db_via_ctl"
    bound_service = TruncateDatabaseDropStageDBViaCtlService
