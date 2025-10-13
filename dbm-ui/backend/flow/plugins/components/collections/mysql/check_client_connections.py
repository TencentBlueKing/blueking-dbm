"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer, FlowOutputHandler
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.mysql_account_mixed import MySQLAccountMixed
from backend.flow.utils.mysql.check_client_connections import check_client_connection

# --------------------------
# Helpers for formatted output
# --------------------------


def _truncate_middle(text: str, max_len: int = 120, head: int = 60, tail: int = 40) -> str:
    """Truncate long text by keeping head and tail parts.

    Examples:
        "abcdefghijklmnopqrstuvwxyz" -> "abcdefghijklmnopqr ... uvwxyz" (when too long)
    """
    if text is None:
        return ""
    s = str(text)
    if len(s) <= max_len:
        return s
    head = min(head, max_len)
    tail = min(tail, max_len - head - 5)
    if tail <= 0:
        # fallback: simple cut
        return s[: max_len - 3] + "..."
    return f"{s[:head]} ... {s[-tail:]}"


def _format_process_infos(rows: list[dict], info_max_len: int = 120) -> str:
    """Format process infos into an aligned table string.

    Columns are best-effort mapped from typical SHOW PROCESSLIST fields.
    """
    if not rows:
        return ""

    # Candidate columns and mapping to display headers
    candidates = [
        ("check_address", "check_address"),
        ("Command", "COMMAND"),
        ("Db", "DB"),
        ("Rows_examined", "EXAMINED_ROWS"),
        ("Host", "HOST"),
        ("Id", "ID"),
        ("Info", "INFO"),
        ("Time", "TIME"),
        ("State", "STATE"),
    ]
    # Pick columns that exist in any row
    cols = [(k, hdr) for (k, hdr) in candidates if any(k in r for r in rows) or k == "check_address"]

    # Prepare values and compute widths
    values = []
    widths = [len(hdr) for (_, hdr) in cols]
    for r in rows:
        row_vals = []
        for idx, (k, hdr) in enumerate(cols):
            v = r.get(k, "")
            if k == "Info":
                v = _truncate_middle(v, max_len=info_max_len)
            v_str = "" if v is None else str(v)
            row_vals.append(v_str)
            widths[idx] = max(widths[idx], len(v_str))
        values.append(row_vals)

    # Build table
    sep = "  "  # two spaces between columns
    header = sep.join(hdr.ljust(widths[i]) for i, (_, hdr) in enumerate(cols))
    line = sep.join("-" * widths[i] for i in range(len(widths)))
    body = [sep.join(val[i].ljust(widths[i]) for i in range(len(widths))) for val in values]

    return "\n".join([header, line, *body])


class CheckClientSerializer(BaseFlowOutputSerializer):
    hidden = True
    table_name = "check_client"
    dynamic_key = "process_infos"
    process_infos = BaseFlowOutputSerializer.DynamicField(help_text=_("process信息"))


class CheckClientConnService(BaseService):
    """
    定义检测实例是否存储用户连接的活动节点（系统账号和内置账号会过滤）
    本节点只支持mysql/spider实例，不支持中控实例的检测
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        results = check_client_connection(
            bk_cloud_id=kwargs["bk_cloud_id"],
            instances=kwargs["check_instances"],
            is_filter_sleep=kwargs.get("is_filter_sleep", False),
            is_proxy=kwargs.get("is_proxy", False),
            filter_hosts=kwargs.get("filter_hosts", []),
            long_query_time=kwargs.get("long_query_time", -1),
        )
        process_infos = []
        for res in results:
            # 检查返回的每个实例的结果
            if res["error_msg"]:
                self.log_error(f"select processlist failed: {res['error_msg']}")
                return False

            infos = res["cmd_results"][0]["table_data"]
            if kwargs.get("is_proxy", False):
                # 这里做对proxy连接做优化，如果出现dbha账号的链接过滤
                dbha_user = MySQLAccountMixed.mysql_dbha_account(kwargs["bk_cloud_id"])["user"]
                self.log_info(f"filter dbha accounts:[{dbha_user}]")
                infos[:] = [d for d in infos if d.get("User") != dbha_user]

            if infos:
                self.log_error(f"[{res['address']}] There are also {len(infos)} not-system threads")
                temp = {"check_address": res["address"]}
                for i in infos:
                    process_infos.append({**temp, **i})
            else:
                self.log_info(f"This node [{res['address']}]  passed the checkpoint [check-client-conn]!")

        if len(process_infos) > 0:
            data = {"process_infos": process_infos}
            FlowOutputHandler(CheckClientSerializer).insert_data(global_data["job_root_id"], data)
            # 结果录入缓存，目的打印到注册表
            self.set_flow_output(
                global_data["job_root_id"],
                key="check_result",
                value=process_infos,
                is_sensitive=False,
            )

            # 对齐且截断过长INFO字段的格式化输出，便于日志查看
            formatted = _format_process_infos(process_infos, info_max_len=120)
            if formatted:
                self.log_error(formatted)

            # 输出下载打印
            self.log_error(
                _("检测结果详情请下载excel:<a href='{}/apis/taskflow/excel_download/?root_id={}'>excel 下载</a>").format(
                    env.BK_SAAS_HOST, global_data["job_root_id"]
                )
            )
            return False

        return True


class CheckClientConnComponent(Component):
    name = __name__
    code = "check_client_connections"
    bound_service = CheckClientConnService
