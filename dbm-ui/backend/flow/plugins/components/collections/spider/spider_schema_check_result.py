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
import json
import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer, FlowOutputHandler

logger = logging.getLogger("flow")

DISPLAY_LIMIT = 1000
QUERY_LIMIT = DISPLAY_LIMIT + 1  # 多查一条用于判断是否超限


class SpiderSchemaCheckSerializer(BaseFlowOutputSerializer):
    hidden = True
    table_name = "spider_schema_check"
    dynamic_key = "schema_check_rows"
    schema_check_rows = BaseFlowOutputSerializer.DynamicField(help_text=_("表结构检查结果"))


class SpiderSchemaCheckResultService(BaseService):
    """
    查询 TDBCTL 中控节点 infodba_schema.tscc_schema_checksum 表中的表结构检查结果，
    格式化后通过日志展示。始终返回 True，不阻断流程。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        ip = kwargs["ip"]
        port = kwargs["port"]
        bk_cloud_id = kwargs["bk_cloud_id"]
        address = f"{ip}:{port}"

        self.log_info(_("开始查询表结构检查结果，中控节点: {}").format(address))

        query_sql = (
            f"SELECT db, tbl, status, checksum_result, update_time "
            f"FROM infodba_schema.tscc_schema_checksum "
            f"LIMIT {QUERY_LIMIT};"
        )

        try:
            res = DRSApi.rpc(
                {
                    "addresses": [address],
                    "cmds": [query_sql],
                    "force": False,
                    "bk_cloud_id": bk_cloud_id,
                }
            )
        except Exception as e:
            self.log_warning(_("查询表结构检查结果失败: {}，跳过展示").format(str(e)))
            return True

        if res[0]["error_msg"]:
            self.log_warning(_("查询表结构检查结果出错: {}，跳过展示").format(res[0]["error_msg"]))
            return True

        rows = res[0]["cmd_results"][0]["table_data"]
        total_fetched = len(rows)

        if total_fetched == 0:
            self.log_info(_("表结构检查完成，所有表结构一致，无不一致记录"))
            return True

        truncated = total_fetched > DISPLAY_LIMIT
        display_rows = rows[:DISPLAY_LIMIT]

        self._print_results(display_rows, truncated)

        try:
            excel_rows = self._collect_excel_rows(rows)
            if excel_rows:
                FlowOutputHandler(SpiderSchemaCheckSerializer).insert_data(
                    global_data["job_root_id"], {"schema_check_rows": excel_rows}
                )
                self.log_warning(
                    _(
                        "发现不一致记录共 {} 行，详情请下载excel:"
                        "<a href='{}/apis/taskflow/excel_download/?root_id={}'>excel 下载</a>"
                    ).format(len(excel_rows), env.BK_SAAS_HOST, global_data["job_root_id"])
                )
        except Exception as e:
            self.log_warning(_("写入 Excel 结果失败: {}，跳过").format(str(e)))

        return True

    def _print_results(self, rows, truncated):
        ok_count = sum(1 for r in rows if r.get("status") == "ok")
        inconsistent_count = len(rows) - ok_count
        display_count = len(rows)

        self.log_info("=" * 60)
        self.log_info(_("表结构检查结果汇总"))
        self.log_info("=" * 60)

        if truncated:
            self.log_info(_("注意：检查记录超过 {} 条，以下仅展示前 {} 条").format(DISPLAY_LIMIT, DISPLAY_LIMIT))
            self.log_info("-" * 60)

        self.log_info(
            _("共展示 {} 条记录，其中一致(ok): {} 条，不一致(inconsistent): {} 条").format(display_count, ok_count, inconsistent_count)
        )
        self.log_info("-" * 60)

        for row in rows:
            db = row.get("db", "")
            tbl = row.get("tbl", "")
            status = row.get("status", "")
            update_time = row.get("update_time", "")
            checksum_result_raw = row.get("checksum_result")

            self.log_info(_("[{}.{}]  status: {}  update_time: {}").format(db, tbl, status, update_time))

            if checksum_result_raw:
                self._print_checksum_result(checksum_result_raw)

        self.log_info("=" * 60)

    def _collect_excel_rows(self, rows):
        """将不一致行展开 checksum_result，返回用于 Excel 的扁平列表。

        每个 checksum_result 条目对应 Excel 的一行；若 checksum_result 为空，
        则只输出外层字段（checksum_* 列置空），确保不一致记录不被遗漏。
        """
        excel_rows = []
        for r in rows:
            if r.get("status") == "ok":
                continue
            base = {
                "db": r.get("db", ""),
                "tbl": r.get("tbl", ""),
                "status": r.get("status", ""),
                "update_time": str(r.get("update_time", "")),
            }
            checksum_result_raw = r.get("checksum_result")
            items = []
            if checksum_result_raw:
                try:
                    parsed = (
                        json.loads(checksum_result_raw)
                        if isinstance(checksum_result_raw, str)
                        else checksum_result_raw
                    )
                    if isinstance(parsed, list):
                        items = parsed
                except (json.JSONDecodeError, TypeError):
                    pass

            if items:
                for item in items:
                    excel_rows.append(
                        {
                            **base,
                            "checksum_db": item.get("Db", ""),
                            "checksum_tbl": item.get("Table", ""),
                            "checksum_status": item.get("Status", ""),
                            "server_name": item.get("Server_name", ""),
                            "message": item.get("Message", ""),
                        }
                    )
            else:
                excel_rows.append(
                    {
                        **base,
                        "checksum_db": "",
                        "checksum_tbl": "",
                        "checksum_status": "",
                        "server_name": "",
                        "message": "",
                    }
                )
        return excel_rows

    def _print_checksum_result(self, checksum_result_raw):
        """格式化输出 checksum_result JSON 字段"""
        try:
            if isinstance(checksum_result_raw, str):
                items = json.loads(checksum_result_raw)
            else:
                items = checksum_result_raw

            if not isinstance(items, list):
                self.log_info(_("  checksum_result: {}").format(checksum_result_raw))
                return

            for idx, item in enumerate(items):
                db_name = item.get("Db", "")
                table_name = item.get("Table", "")
                item_status = item.get("Status", "")
                server_name = item.get("Server_name", "")
                message = item.get("Message", "")
                self.log_info(
                    "  [{idx}] Db: {db}  Table: {tbl}  Status: {status}  Server: {server}".format(
                        idx=idx,
                        db=db_name,
                        tbl=table_name,
                        status=item_status,
                        server=server_name,
                    )
                )
                if message:
                    self.log_info(f"       Message: {message}")

        except (json.JSONDecodeError, TypeError):
            self.log_info(_("  checksum_result(raw): {}").format(checksum_result_raw))


class SpiderSchemaCheckResultComponent(Component):
    name = __name__
    code = "spider_schema_check_result"
    bound_service = SpiderSchemaCheckResultService
    node_name = str(_("查询表结构检查结果"))
