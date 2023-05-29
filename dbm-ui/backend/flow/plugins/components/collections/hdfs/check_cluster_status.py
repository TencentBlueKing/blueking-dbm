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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.enums import ClusterPhase
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class CheckClusterStatusService(BaseService):
    """
    集群下架时检查集群状态
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")

        self.log_info("check cluster status when cluster delete")

        result = False
        if global_data["ticket_type"] in (TicketType.HDFS_ENABLE, TicketType.HDFS_DESTROY):
            result = global_data["cluster_phase"] == ClusterPhase.OFFLINE.value
        elif global_data["ticket_type"] == TicketType.HDFS_DISABLE:
            result = global_data["cluster_phase"] == ClusterPhase.ONLINE.value

        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class CheckClusterStatusComponent(Component):
    name = __name__
    code = "check_cluster_phase"
    bound_service = CheckClusterStatusService
