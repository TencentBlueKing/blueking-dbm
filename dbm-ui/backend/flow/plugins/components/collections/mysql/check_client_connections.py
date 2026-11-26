"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.flow.consts import CheckClientConnRole
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer, FlowOutputHandler
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.mysql_account_mixed import MySQLAccountMixed
from backend.flow.utils.mysql.check_client_connections import check_client_connection, get_cluster_instances_by_role

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
    # Support both lowercase and uppercase field names from different data sources
    candidates = [
        (["check_address"], "check_address"),
        (["trx_state", "TRX_STATE"], "TRX_STATE"),
        (["trx_started", "TRX_STARTED"], "TRX_STARTED"),
        (["trx_mysql_thread_id", "TRX_MYSQL_THREAD_ID"], "TRX_THREAD_ID"),
        (["Command", "COMMAND"], "COMMAND"),
        (["Db", "DB"], "DB"),
        (["Rows_examined", "ROWS_EXAMINED"], "EXAMINED_ROWS"),
        (["Host", "HOST"], "HOST"),
        (["Id", "ID"], "ID"),
        (["User", "USER"], "USER"),
        (["Info", "INFO"], "INFO"),
        (["Time", "TIME"], "TIME"),
        (["State", "STATE"], "STATE"),
    ]

    # Build column list with actual field names found in data
    cols = []
    for field_variants, display_name in candidates:
        # Find which variant exists in the data
        actual_field = None
        for variant in field_variants:
            if any(variant in r for r in rows):
                actual_field = variant
                break
        if actual_field or field_variants[0] == "check_address":
            cols.append((actual_field or field_variants[0], display_name))

    # Prepare values and compute widths
    values = []
    widths = [len(hdr) for (_, hdr) in cols]
    for r in rows:
        row_vals = []
        for idx, (k, hdr) in enumerate(cols):
            v = r.get(k, "")
            if k in ["Info", "INFO"]:
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

    return "\n" + "\n".join([header, line, *body])


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
            # CheckClientConnKwargs 字段名为 long_process_time，需与 dataclass 对齐
            long_query_time=kwargs.get("long_process_time", -1),
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


class DynamicCheckClientConnService(CheckClientConnService):
    """
    定义运行期动态检测客户端连接的活动节点
    区别于静态模式（构建期传入实例列表），本节点在运行期根据集群ID+角色
    动态获取 running 状态的实例，再复用父类 CheckClientConnService 的检测逻辑
    （含内置账号过滤、proxy 的 dbha 账号过滤、FlowOutput/Excel 输出等）
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        check_role = kwargs["check_role"]

        # 运行期根据集群ID+角色，动态获取该角色 running 状态的实例
        instances = get_cluster_instances_by_role(cluster_id=kwargs["cluster_id"], role=check_role)
        if not instances:
            self.log_error(_("集群[{}]按角色[{}]未查询到 running 状态的待检测实例，联系系统管理员确认").format(kwargs["cluster_id"], check_role))
            return False

        # proxy 角色走 proxyrpc(show processlist)，backend/spider 角色走 rpc(processlist 查询)
        is_proxy = check_role == CheckClientConnRole.PROXY.value

        # 拼装父类 CheckClientConnService._execute 所需的 kwargs
        original_kwargs = kwargs
        check_kwargs = copy.deepcopy(original_kwargs)
        check_kwargs["check_instances"] = instances
        check_kwargs["is_proxy"] = is_proxy
        data.inputs.kwargs = check_kwargs

        self.log_info(f"[dynamic check client conn] role[{check_role}] instances: {instances}")
        result = super()._execute(data, parent_data)

        return result


class DynamicCheckClientConnComponent(Component):
    name = __name__
    code = "mysql_dynamic_check_client_connections"
    bound_service = DynamicCheckClientConnService
