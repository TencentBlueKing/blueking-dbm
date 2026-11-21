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

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.precheck.base import CheckLevel
from backend.flow.utils.mysql.dts.precheck.summary import SKIPPED_NO_FLOW, write_precheck_summary
from backend.flow.utils.mysql.dts.precheck.topology import topology_results

logger = logging.getLogger("root")


class MysqlDtsPrecheckTopologyService(BaseService):
    """拓扑专有检查。many_to_one 写多源落点冲突，one_to_many 写路由覆盖。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        item, results_by_pair = topology_results(kwargs.get("topology"), kwargs.get("pairs") or [])
        if not results_by_pair:
            return True
        root_id = self.runtime_attrs.get("root_pipeline_id")
        has_failure = False
        pairs = {pair["pair_key"]: pair for pair in kwargs.get("pairs") or []}
        for pair_key, results in results_by_pair.items():
            pair = pairs.get(pair_key) or {}
            outcome = write_precheck_summary(
                root_id,
                item,
                results,
                pair.get("source_cluster_domain") or "",
                pair.get("target_cluster_domain") or "",
                kwargs.get("enabled_codes"),
                pair_key=pair_key,
                scope_label=pair.get("scope_label") or "",
            )
            if outcome == SKIPPED_NO_FLOW:
                self.log_info(_("当前流程[{}]未关联单据Flow记录，跳过写入执行摘要").format(root_id))
            if any(not result.ok and result.level != CheckLevel.WARN for result in results):
                has_failure = True
                self.log_error(_("DTS预检查 {} 未通过: {}").format(item.name, results[0].message))
            else:
                self.log_info(_("DTS预检查 {} 通过: {}").format(item.name, results[0].message))
        return not has_failure


class MysqlDtsPrecheckTopologyComponent(Component):
    name = __name__
    code = "mysql_dts_precheck_topology"
    bound_service = MysqlDtsPrecheckTopologyService
