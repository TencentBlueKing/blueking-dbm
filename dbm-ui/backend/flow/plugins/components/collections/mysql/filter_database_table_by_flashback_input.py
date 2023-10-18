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
from collections import defaultdict

from pipeline.component_framework.component import Component

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.consts import SYSTEM_DBS
from backend.flow.plugins.components.collections.common.base_service import BaseService


class FilterDatabaseTableFromFlashbackInputService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        ip = global_data["ip"]
        port = global_data["port"]

        databases = global_data["databases"]
        databases_ignore = global_data["databases_ignore"]
        tables = global_data["tables"]
        tables_ignore = global_data["tables_ignore"]

        databases = [ele.replace("_", "\_").replace("*", "%").replace("?", "_") for ele in databases]
        databases_ignore = [ele.replace("_", "\_").replace("*", "%").replace("?", "_") for ele in databases_ignore]
        tables = [ele.replace("_", "\_").replace("*", "%").replace("?", "_") for ele in tables]
        tables_ignore = [ele.replace("_", "\_").replace("*", "%").replace("?", "_") for ele in tables_ignore]

        db_filter_sql = "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE ({}) AND ({})".format(
            " OR ".join(["SCHEMA_NAME LIKE '{}'".format(ele) for ele in databases]),
            " AND ".join(["SCHEMA_NAME NOT LIKE '{}'".format(ele) for ele in databases_ignore + SYSTEM_DBS]),
        )
        self.log_info("[{}] db_filter_sql: {}".format(kwargs["node_name"], db_filter_sql))
        db_filter_res = DRSApi.rpc(
            {
                "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                "cmds": [db_filter_sql],
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )
        self.log_info("[{}] filter database response: {}".format(kwargs["node_name"], db_filter_res))
        if db_filter_res[0]["error_msg"]:
            self.log_error(
                "[{}] filter databases on {}{}{} failed: {}".format(
                    kwargs["node_name"], ip, IP_PORT_DIVIDER, port, db_filter_res[0]["error_msg"]
                )
            )
            return False

        databases_filtered = [ele["SCHEMA_NAME"] for ele in db_filter_res[0]["cmd_results"][0]["table_data"]]

        # tables 和 tables_ignore 使用三元操作符返回一个恒真表达式, 简化代码
        table_filter_sql = (
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_TYPE='BASE TABLE' AND {} AND ({}) AND ({})"
        ).format(
            "TABLE_SCHEMA IN ({})".format(",".join(["'{}'".format(ele) for ele in databases_filtered])),
            " OR ".join(["TABLE_NAME LIKE '{}'".format(ele) for ele in tables]) if tables else "1=1",
            " AND ".join(["TABLE_NAME NOT LIKE '{}'".format(ele) for ele in tables_ignore])
            if tables_ignore
            else "1=1",
        )
        self.log_info("[{}] table_filter_sql: {}".format(kwargs["node_name"], table_filter_sql))
        table_filter_res = DRSApi.rpc(
            {
                "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                "cmds": [table_filter_sql],
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )
        self.log_info("[{}] filter table response: {}".format(kwargs["node_name"], table_filter_res))
        if table_filter_res[0]["error_msg"]:
            self.log_error(
                "[{}] filter table on {}{}{} failed: {}".format(
                    kwargs["node_name"], ip, IP_PORT_DIVIDER, port, table_filter_res[0]["error_msg"]
                )
            )
            return False

        targets = defaultdict(dict)
        for row in table_filter_res[0]["cmd_results"][0]["table_data"]:
            db = row["TABLE_SCHEMA"]
            tbl = row["TABLE_NAME"]
            targets[db][tbl] = False

        self.log_info("[{}] filtered table: {}".format(kwargs["node_name"], targets))

        if not targets:
            self.log_error("[{}] match nothing".format(kwargs["node_name"]))
            return False

        trans_data.targets = dict(targets)
        data.outputs["trans_data"] = trans_data
        return True


class FilterDatabaseTableFromFlashbackInputComponent(Component):
    name = __name__
    code = "filter_database_table_from_flashback_input"
    bound_service = FilterDatabaseTableFromFlashbackInputService
