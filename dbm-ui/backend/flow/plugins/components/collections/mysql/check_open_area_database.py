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

import unicodedata
from collections import defaultdict

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

COLUMN_GAP = " " * 4


class CheckOpenAreaDatabaseService(BaseService):
    """检查开区目标实例是否已存在待创建的数据库。"""

    @staticmethod
    def _display_width(value: str) -> int:
        # 中文等全角字符在等宽字体下占两列，直接用len对齐会错位
        return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in value)

    @classmethod
    def _pad(cls, value: str, width: int) -> str:
        return value + " " * (width - cls._display_width(value))

    @classmethod
    def _format_rows(cls, title: str, rows: list) -> str:
        if not rows:
            return "{}\n{}".format(title, _("无"))

        headers = (_("源集群域名"), _("目标集群域名"), _("库信息"))
        all_rows = [headers] + [tuple(str(value) for value in row) for row in rows]
        widths = [max(cls._display_width(row[index]) for row in all_rows) for index in range(len(headers))]

        lines = [
            title,
            COLUMN_GAP.join(cls._pad(value, widths[index]) for index, value in enumerate(headers)).rstrip(),
        ]
        lines.append("-" * (sum(widths) + len(COLUMN_GAP) * (len(widths) - 1)))
        lines.extend(
            COLUMN_GAP.join(cls._pad(value, widths[index]) for index, value in enumerate(row)).rstrip()
            for row in all_rows[1:]
        )
        return "\n".join(lines)

    @staticmethod
    def _parse_databases(result: dict) -> tuple:
        if not isinstance(result, dict):
            return set(), _("DRS 返回格式异常")

        if result.get("error_msg"):
            return set(), result["error_msg"]

        cmd_results = result.get("cmd_results")
        if not isinstance(cmd_results, list) or not cmd_results:
            return set(), _("DRS 未返回查询结果")

        cmd_result = cmd_results[0]
        if not isinstance(cmd_result, dict):
            return set(), _("DRS 查询结果格式异常")
        if cmd_result.get("error_msg"):
            return set(), cmd_result["error_msg"]

        table_data = cmd_result.get("table_data")
        if not isinstance(table_data, list):
            return set(), _("DRS 未返回数据库列表")

        databases = {row["Database"] for row in table_data if isinstance(row, dict) and "Database" in row}
        if table_data and not databases:
            return set(), _("DRS 数据库列表格式异常")
        return databases, ""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        source_domain = kwargs["source_cluster_domain"]
        targets = kwargs["targets"]

        cloud_addresses = defaultdict(list)
        for target in targets:
            address = target["address"]
            addresses = cloud_addresses[target["bk_cloud_id"]]
            if address not in addresses:
                addresses.append(address)

        databases_by_instance = {}
        errors_by_instance = {}
        for bk_cloud_id, addresses in cloud_addresses.items():
            try:
                results = DRSApi.rpc(
                    {
                        "bk_cloud_id": bk_cloud_id,
                        "addresses": addresses,
                        "cmds": ["show databases"],
                        "force": False,
                    }
                )
            except Exception as err:  # pylint: disable=broad-except
                error = _("DRS 调用异常：{}").format(err)
                for address in addresses:
                    errors_by_instance[(bk_cloud_id, address)] = error
                continue

            valid_results = results if isinstance(results, list) else []
            results_by_address = {
                result.get("address"): result for result in valid_results if isinstance(result, dict)
            }
            for address in addresses:
                instance_key = (bk_cloud_id, address)
                result = results_by_address.get(address)
                if result is None:
                    errors_by_instance[instance_key] = _("DRS 未返回该目标实例的检查结果")
                    continue

                databases, error = self._parse_databases(result)
                if error:
                    errors_by_instance[instance_key] = error
                else:
                    databases_by_instance[instance_key] = databases

        available_rows = []
        unavailable_rows = []
        for target in targets:
            address = target["address"]
            instance_key = (target["bk_cloud_id"], address)
            target_domain = target["target_cluster_domain"]
            for database in target["databases"]:
                if instance_key in errors_by_instance:
                    database_info = _("{}（检查失败：{}）").format(database, errors_by_instance[instance_key])
                    unavailable_rows.append((source_domain, target_domain, database_info))
                elif database in databases_by_instance[instance_key]:
                    unavailable_rows.append((source_domain, target_domain, database))
                else:
                    available_rows.append((source_domain, target_domain, database))

        blocked_title = _("【db在目标集群已存在，不可以开区】")
        self.log_info(self._format_rows(_("【可以开区】"), available_rows))
        if unavailable_rows:
            self.log_error(self._format_rows(blocked_title, unavailable_rows))
            self.log_error(_("存在目标库冲突或目标库检查失败，停止开区流程"))
            return False

        self.log_info(self._format_rows(blocked_title, unavailable_rows))
        return True


class CheckOpenAreaDatabaseComponent(Component):
    name = __name__
    code = "mysql_check_open_area_database"
    bound_service = CheckOpenAreaDatabaseService
