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
from backend.flow.utils.cc_manage import operate_bklog_host_collectors

logger = logging.getLogger("flow")


class OperateHostBklogCollectorService(BaseService):
    """按主机维度安装/卸载日志采集项"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        bk_host_ids = list(kwargs.get("bk_host_ids") or [])

        if isinstance(trans_data, dict) and trans_data.get("hosts"):
            bk_host_ids.extend([host.get("bk_host_id") or host.get("host_id") for host in trans_data["hosts"]])

        bk_host_ids = [host_id for host_id in bk_host_ids if host_id]
        if not bk_host_ids:
            self.log_warning(_("未找到待操作主机，跳过日志采集项操作"))
            return True

        operate_bklog_host_collectors(
            bk_host_ids=bk_host_ids,
            action=kwargs["action"],
            collector_names=kwargs["collector_names"],
            bk_biz_id=kwargs["bk_biz_id"],
        )
        self.log_info(_("主机{} {}采集项{}").format(bk_host_ids, kwargs["action"], kwargs["collector_names"]))
        return True


class OperateHostBklogCollectorComponent(Component):
    name = __name__
    code = "operate_host_bklog_collector"
    bound_service = OperateHostBklogCollectorService
