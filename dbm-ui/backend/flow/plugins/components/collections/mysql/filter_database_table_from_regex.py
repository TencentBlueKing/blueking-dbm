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
import re

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService


class FilterDatabaseTableFromRegexService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        select from information_schema.tables 当库中没有表的时候会没返回
        所以必须先单独遍历 show databases 的结果, 保证由 [db_patterns, ignore_dbs] 确定的库都找出来了
        bk_cloud_id 统一由私有变量kwargs传入
        """
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        ip = global_data["ip"]
        port = global_data["port"]
        db_filter_regex = trans_data.db_filter_regex
        db_filter_pattern = re.compile(db_filter_regex)

        db_table_filter_regex = trans_data.db_table_filter_regex
        db_table_filter_pattern = re.compile(db_table_filter_regex)

        get_dbs_res = DRSApi.rpc(
            {
                "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                "cmds": ["show databases"],
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )
        self.log_info("[{}] get databases response: {}".format(kwargs["node_name"], get_dbs_res))
        if get_dbs_res[0]["error_msg"]:
            self.log_error(
                "[{}] get databases on {}{}{} failed: {}".format(
                    kwargs["node_name"], ip, IP_PORT_DIVIDER, port, get_dbs_res[0]["error_msg"]
                )
            )
            return False

        targets = {}
        for row in get_dbs_res[0]["cmd_results"][0]["table_data"]:
            db = row["Database"]
            if db_filter_pattern.match(db):
                targets[db] = {}

        self.log_info("[{}] db filter: {}".format(kwargs["node_name"], targets))

        schema_tables_res = DRSApi.rpc(
            {
                "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
                "cmds": [
                    "SELECT TABLE_SCHEMA, TABLE_NAME FROM information_schema.tables where table_type='BASE TABLE'"
                ],
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )
        self.log_info("[{}] get tables response: {}".format(kwargs["node_name"], schema_tables_res))
        if schema_tables_res[0]["error_msg"]:
            self.log_error(
                "[{}] get tables on {}{}{} failed: {}".format(
                    kwargs["node_name"], ip, IP_PORT_DIVIDER, port, schema_tables_res[0]["error_msg"]
                )
            )
            return False

        for row in schema_tables_res[0]["cmd_results"][0]["table_data"]:
            db = row["TABLE_SCHEMA"]
            tbl = row["TABLE_NAME"]
            concat_name = "{}.{}".format(db, tbl)
            if db_table_filter_pattern.match(concat_name):
                targets[db][tbl] = False

        self.log_info(_("[{}] 过滤所得库表: {}").format(kwargs["node_name"], targets))

        if not targets:
            self.log_error(_("[{}] 未匹配到任何库".format(kwargs["node_name"])))
            return False

        trans_data.targets = dict(targets)
        data.outputs["trans_data"] = trans_data
        return True


class FilterDatabaseTableFromRegexComponent(Component):
    name = __name__
    code = "filter_database_table_from_regex"
    bound_service = FilterDatabaseTableFromRegexService
