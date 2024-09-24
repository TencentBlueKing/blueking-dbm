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

from pipeline.component_framework.component import Component

from backend.db_dirty.constants import MachineEventType
from backend.db_dirty.models import MachineEvent
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.cc_manage import CcManage
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class TransferHostToPoolService(BaseService):
    """将主机转移至故障池"""

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        bk_biz_id = kwargs["bk_biz_id"]
        recycle_hosts = kwargs["recycle_hosts"]
        operator = kwargs["operator"]
        event = kwargs["event"]
        ticket = Ticket.objects.get(id=kwargs["ticket_id"])
        # 如果备注为空，则取转移主机备注。TODO：目前考虑支持批量插入，因此暂定所有主机备注一致
        remark = kwargs.get("remark") or recycle_hosts[0].get("remark") or ""
        # 记录主机事件
        MachineEvent.host_event_trigger(bk_biz_id, recycle_hosts, event, operator, ticket, remark=remark)
        # 如果主机事件是回收，则转移CC模块
        if event == MachineEventType.Recycled:
            host_ids = [host["bk_host_id"] for host in recycle_hosts]
            CcManage(bk_biz_id=bk_biz_id, cluster_type=kwargs["db_type"]).recycle_host(host_ids)


class TransferHostToPoolComponent(Component):
    name = __name__
    code = "transfer_host_to_fault"
    bound_service = TransferHostToPoolService
