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
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mysql.check_client_connections import _format_process_infos


def _build_long_trx_sql(min_trx_age_seconds: int) -> str:
    """Build SQL for long-running InnoDB transactions (age threshold in seconds)."""
    return (
        "SELECT t1.trx_state, t1.trx_started, t1.trx_mysql_thread_id, "
        "t2.ID, t2.USER, t2.HOST, t2.DB, t2.COMMAND, t2.TIME, t2.STATE, t2.INFO "
        "FROM information_schema.innodb_trx t1 "
        "INNER JOIN information_schema.processlist t2 ON t1.trx_mysql_thread_id = t2.ID "
        "WHERE t1.trx_started < DATE_SUB(NOW(), INTERVAL {} SECOND)".format(min_trx_age_seconds)
    )


class CheckLongInnoDbTrxService(BaseService):
    """
    检测实例上是否存在开始时间过早且仍未提交的 InnoDB 事务（通过 DRS 查询）。
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        raw_sec = kwargs.get("min_trx_age_seconds", 300)
        try:
            min_trx_age_seconds = int(raw_sec)
        except (TypeError, ValueError):
            self.log_error(_("参数 min_trx_age_seconds 无效: {}").format(raw_sec))
            return False
        if min_trx_age_seconds <= 0:
            self.log_error(_("参数 min_trx_age_seconds 必须为正整数，当前为: {}").format(min_trx_age_seconds))
            return False

        check_sql = _build_long_trx_sql(min_trx_age_seconds)
        self.log_info(_("执行 InnoDB 长事务检测 SQL（阈值 {} 秒）").format(min_trx_age_seconds))
        self.log_info(check_sql)

        results = DRSApi.short_rpc(
            {
                "addresses": kwargs["check_instances"],
                "cmds": [check_sql],
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )

        trx_rows = []
        for res in results:
            if res["error_msg"]:
                self.log_error(_("查询 InnoDB 事务失败 [{}]: {}").format(res.get("address", ""), res["error_msg"]))
                return False
            cmd_result = res["cmd_results"][0]
            if cmd_result["error_msg"]:
                self.log_error(_("查询 InnoDB 事务失败 [{}]: {}").format(res.get("address", ""), cmd_result["error_msg"]))
                return False
            table_data = cmd_result["table_data"]
            if not table_data:
                self.log_info(_("节点 [{}] 通过 InnoDB 长事务检查").format(res["address"]))
                continue
            self.log_error(
                _("节点 [{}] 存在 {} 条超过 {} 秒的未提交 InnoDB 事务").format(res["address"], len(table_data), min_trx_age_seconds)
            )
            prefix = {"check_address": res["address"]}
            for row in table_data:
                trx_rows.append({**prefix, **row})

        if trx_rows:
            formatted = _format_process_infos(trx_rows, info_max_len=120)
            if formatted:
                self.log_error(formatted)
            return False

        return True


class CheckLongInnoDbTrxComponent(Component):
    name = __name__
    code = "check_long_innodb_trx"
    bound_service = CheckLongInnoDbTrxService
