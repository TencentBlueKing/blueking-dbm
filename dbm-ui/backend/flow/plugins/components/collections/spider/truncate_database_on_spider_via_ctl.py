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
from backend.flow.consts import TruncateDataTypeEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService


class TruncateDatabaseOnSpiderViaCtlService(BaseService):
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        truncate_data_type = global_data["truncate_data_type"]
        self.log_info("[{}] truncate data type: {}".format(kwargs["node_name"], truncate_data_type))

        old_new_map = trans_data.old_new_map
        self.log_info("[{}] truncate on spider old_new_map: {}".format(kwargs["node_name"], old_new_map))

        ctl_primary = global_data["ctl_primary"]

        # old_db 下没有表了
        sql_cmds = ["set tc_admin=1"]
        if truncate_data_type == TruncateDataTypeEnum.TRUNCATE_TABLE.value:
            # 重建空表
            for old_db in old_new_map:
                new_db = old_new_map[old_db]

                show_tables_cmd = "select TABLE_NAME from information_schema.tables where TABLE_SCHEMA='{}'".format(
                    new_db
                )
                show_tables_res = DRSApi.rpc(
                    {
                        "addresses": [ctl_primary],
                        "cmds": [show_tables_cmd],
                        "bk_cloud_id": kwargs["bk_cloud_id"],
                    }
                )
                self.log_info(
                    "[{}] get table list from new db response: {}".format(kwargs["node_name"], show_tables_res)
                )
                if show_tables_res[0]["error_msg"]:
                    self.log_error(
                        "[{}] get {} table list from {} failed: {}".format(
                            kwargs["node_name"], new_db, ctl_primary, show_tables_res[0]["error_msg"]
                        )
                    )
                    data.outputs.ext_result = False
                    return False

                for row in show_tables_res[0]["cmd_results"][0]["table_data"]:
                    table_name = row["TABLE_NAME"]

                    show_create_table_cmd = "show create table `{}`.`{}`".format(new_db, table_name)
                    show_create_table_res = DRSApi.rpc(
                        {
                            "addresses": [ctl_primary],
                            "cmds": [show_create_table_cmd],
                            "forces": False,
                            "bk_cloud_id": kwargs["bk_cloud_id"],
                        }
                    )
                    self.log_info(
                        "[{}] show create table from new db response: {}".format(
                            kwargs["node_name"], show_create_table_res
                        )
                    )
                    if show_create_table_res[0]["error_msg"]:
                        self.log_error(
                            "[{}] show create table from {} failed: {}".format(
                                kwargs["node_name"], ctl_primary, show_tables_res
                            )
                        )
                        data.outputs.ext_result = False
                        return False

                    create_table_cmd = show_create_table_res[0]["cmd_results"][0]["table_data"][0]["Create Table"]
                    self.log_info(
                        "[{}] {}.{} create table cmd: {}".format(
                            kwargs["node_name"], new_db, table_name, create_table_cmd
                        )
                    )
                    sql_cmds += [
                        "drop table if exists {}.{}".format(old_db, table_name),
                        "use {}".format(old_db),
                        create_table_cmd,
                    ]
        elif truncate_data_type == TruncateDataTypeEnum.DROP_TABLE.value:
            # remote 没有表, spider 有表
            # 要把 spider old_db 的表 drop 掉
            for old_db in old_new_map:
                show_tables_cmd = "select TABLE_NAME from information_schema.tables where TABLE_SCHEMA='{}'".format(
                    old_db
                )
                show_tables_res = DRSApi.rpc(
                    {
                        "addresses": [ctl_primary],
                        "cmds": [show_tables_cmd],
                        "bk_cloud_id": kwargs["bk_cloud_id"],
                    }
                )
                self.log_info(
                    "[{}] get table list from old db response: {}".format(kwargs["node_name"], show_tables_res)
                )
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
                    sql_cmds.append("drop table if exists `{}`.`{}`".format(old_db, table_name))
        elif truncate_data_type == TruncateDataTypeEnum.DROP_DATABASE.value:
            # 把 old_db drop 掉
            sql_cmds += ["drop database {}".format(old_db) for old_db in old_new_map.keys()]

        res = DRSApi.rpc(
            {"addresses": [ctl_primary], "cmds": sql_cmds, "force": False, "bk_cloud_id": kwargs["bk_cloud_id"]}
        )
        self.log_info("[{}] process cluster table via ctl response: {}".format(kwargs["node_name"], res))
        if res[0]["error_msg"]:
            self.log_error(
                "[{}] process cluster table on {} failed: {}".format(
                    kwargs["node_name"], ctl_primary, res[0]["error_msg"]
                )
            )
            data.outputs.ext_result = False
            return False

        self.log_info(_("处理集群表完成"))
        data.outputs["trans_data"] = trans_data
        return True


class TruncateDatabaseOnSpiderViaCtlComponent(Component):
    name = __name__
    code = "truncate_database_on_spider_via_ctl"
    bound_service = TruncateDatabaseOnSpiderViaCtlService
