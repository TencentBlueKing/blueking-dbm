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
import pprint

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components.db_remote_service.client import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class CreateDatabaseLikeViaCtlService(BaseService):
    """
    tendbcluster 在清档和 db 重命名时, 需要在 spider 层先复制一份完整的库表结构
    不需要复制源库的存储过程, 触发器和视图
    不考虑复用 TruncateDataCreateStageDatabaseService 是因为过程其实差别还蛮大的
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        ctl_primary = global_data["ctl_primary"]

        sql_cmds = ["set tc_admin=1"]
        for old_db in trans_data.old_new_map:
            new_db = trans_data.old_new_map[old_db]

            create_stage_db_cmd = "create database if not exists `{}`".format(new_db)
            sql_cmds.append(create_stage_db_cmd)

            show_tables_cmd = "select TABLE_NAME from information_schema.tables where TABLE_SCHEMA='{}'".format(old_db)
            show_tables_res = DRSApi.rpc(
                {
                    "addresses": [ctl_primary],
                    "cmds": [show_tables_cmd],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )
            self.log_info("[{}] get table list from old db response: {}".format(kwargs["node_name"], show_tables_res))
            if show_tables_res[0]["error_msg"]:
                self.log_error(
                    "[{}] get {} table list from {} failed: {}".format(
                        kwargs["node_name"], old_db, ctl_primary, show_tables_res[0]["error_msg"]
                    )
                )
                data.outputs.ext_result = False
                return False

            for row in show_tables_res[0]["cmd_results"][0]["table_data"]:
                table_name = row["TABLE_NAME"]

                show_create_table_from_old_cmd = "show create table `{}`.`{}`".format(old_db, table_name)
                show_create_table_from_old_res = DRSApi.rpc(
                    {
                        "addresses": [ctl_primary],
                        "cmds": [show_create_table_from_old_cmd],
                        "forces": False,
                        "bk_cloud_id": kwargs["bk_cloud_id"],
                    }
                )
                self.log_info(
                    "[{}] show create table from old db response: {}".format(
                        kwargs["node_name"], show_create_table_from_old_res
                    )
                )
                if show_create_table_from_old_res[0]["error_msg"]:
                    self.log_error(
                        "[{}] show create table from {} failed: {}".format(
                            kwargs["node_name"], ctl_primary, show_tables_res
                        )
                    )
                    data.outputs.ext_result = False
                    return False

                create_table_cmd = show_create_table_from_old_res[0]["cmd_results"][0]["table_data"][0]["Create Table"]
                self.log_info(
                    "[{}] {}.{} create table cmd: {}".format(kwargs["node_name"], old_db, table_name, create_table_cmd)
                )
                sql_cmds += ["use {}".format(new_db), create_table_cmd]

        create_stage_db_table_res = DRSApi.rpc(
            {
                "addresses": [ctl_primary],
                "cmds": sql_cmds,
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )
        self.log_info("[{}] create stage db table response: {}".format(kwargs["node_name"], create_stage_db_table_res))
        if create_stage_db_table_res[0]["error_msg"]:
            self.log_error(
                "[{}] create stage db table on {} failed: {}".format(
                    kwargs["node_name"], ctl_primary, create_stage_db_table_res[0]["error_msg"]
                )
            )
            data.outputs.ext_result = False
            return False

        self.log_info(_("建立集群备份库表完成"))

        data.outputs["trans_data"] = trans_data
        return True


class CreateDatabaseLikeViaCtlComponent(Component):
    name = __name__
    code = "create_database_like_via_ctl"
    bound_service = CreateDatabaseLikeViaCtlService
