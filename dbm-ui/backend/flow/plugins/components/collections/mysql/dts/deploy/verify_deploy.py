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
from pipeline.core.flow.activity import StaticIntervalGenerator

from backend.components import MySQLDTSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_VERIFY_MAX_RETRIES, MYSQL_DTS_VERIFY_RETRY_INTERVAL
from backend.flow.utils.mysql.dts.verify_helper import match_nodes

logger = logging.getLogger("flow")


class MysqlDtsDeployVerifyService(BaseService):
    """经 DRS/MySQLDTSApi 轮询验收 DTS 部署结果。"""

    __need_schedule__ = True
    interval = StaticIntervalGenerator(MYSQL_DTS_VERIFY_RETRY_INTERVAL)

    def _execute(self, data, parent_data) -> bool:
        data.outputs.retry_count = 0
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        node_name = kwargs["node_name"]
        master_addr = kwargs["master_addr"]
        verify_role = kwargs.get("verify_role", "all")
        expected_master_nodes = kwargs.get("expected_master_nodes", [])
        expected_worker_nodes = kwargs.get("expected_worker_nodes", [])
        retry_count = data.get_one_of_outputs("retry_count", 0) + 1
        data.outputs.retry_count = retry_count

        try:
            MySQLDTSApi.get_cluster_info(master_addr)
            if verify_role in ("master", "all") and expected_master_nodes:
                masters_resp = MySQLDTSApi.list_masters(master_addr)
                match_nodes(masters_resp.data, expected_master_nodes, "Master")
            if verify_role in ("worker", "all") and expected_worker_nodes:
                workers_resp = MySQLDTSApi.list_workers(master_addr)
                match_nodes(workers_resp.data, expected_worker_nodes, "Worker")

            self.log_info(_("[{}] DTS 部署验收通过").format(node_name))
            self.finish_schedule()
            return True
        except Exception as exc:
            if retry_count >= MYSQL_DTS_VERIFY_MAX_RETRIES:
                self.log_error(_("DTS 部署验收失败，已重试 {} 次: {}").format(retry_count, str(exc)))
                self.finish_schedule()
                return False
            self.log_info(_("DTS 部署验收第 {} 次未通过，等待重试: {}").format(retry_count, str(exc)))
            return True


class MysqlDtsDeployVerifyComponent(Component):
    name = __name__
    code = "mysql_dts_deploy_verify"
    bound_service = MysqlDtsDeployVerifyService
