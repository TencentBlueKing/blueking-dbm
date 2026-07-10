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
import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import MySQLDTSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


def _is_ignorable_offline_error(exc: Exception) -> bool:
    """进程已停后 Master 不可达、节点已不存在等视为可忽略。"""
    msg = str(exc).lower()
    keywords = [
        "connection refused",
        "connection reset",
        "connect timeout",
        "timed out",
        "timeout",
        "502",
        "503",
        "bad gateway",
        "unavailable",
        "unreachable",
        "not found",
        "no such",
        "does not exist",
        "not exist",
        "already",
    ]
    return any(k in msg for k in keywords)


class MysqlDtsOfflineNodesService(BaseService):
    """从 DTS Master 下线 Worker / Master 节点注册信息。"""

    def _offline_one(
        self, *, role: str, name: str, master_addr: str, force_destroy: bool, ignore_unreachable: bool
    ) -> bool:
        try:
            if role == "worker":
                MySQLDTSApi.offline_worker(master_addr, name)
            else:
                MySQLDTSApi.offline_master(master_addr, name)
            self.log_info(_("下线 {} 成功: {}").format(role, name))
            return True
        except Exception as exc:  # pylint: disable=broad-except
            if force_destroy or (ignore_unreachable and _is_ignorable_offline_error(exc)):
                self.log_warning(_("忽略下线 {} {} 失败: {}").format(role, name, exc))
                return True
            self.log_error(_("下线 {} {} 失败: {}").format(role, name, exc))
            return False

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        master_addr = kwargs.get("master_addr")
        force_destroy = kwargs.get("force_destroy", False)
        ignore_unreachable = kwargs.get("ignore_unreachable", False)
        worker_nodes = kwargs.get("worker_nodes") or []
        master_nodes = kwargs.get("master_nodes") or []
        if not master_addr:
            self.log_warning(_("master_addr 为空，跳过 offline_worker/offline_master"))
            return True

        for node in worker_nodes:
            worker_name = node.get("name") or node.get("worker_name")
            if not worker_name:
                continue
            if not self._offline_one(
                role="worker",
                name=worker_name,
                master_addr=master_addr,
                force_destroy=force_destroy,
                ignore_unreachable=ignore_unreachable,
            ):
                return False

        for node in master_nodes:
            master_name = node.get("name") or node.get("master_name")
            if not master_name:
                continue
            if not self._offline_one(
                role="master",
                name=master_name,
                master_addr=master_addr,
                force_destroy=force_destroy,
                ignore_unreachable=ignore_unreachable,
            ):
                return False
        return True


class MysqlDtsOfflineNodesComponent(Component):
    name = __name__
    code = "mysql_dts_offline_nodes"
    bound_service = MysqlDtsOfflineNodesService
