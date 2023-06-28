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

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.db_services.redis_dts.models import TendisDtsServer
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class RedisDtsServerMetaService(BaseService):
    """
    更新redis dts server meta
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        if global_data["ticket_type"] == TicketType.REDIS_ADD_DTS_SERVER.value:
            cluster = kwargs["cluster"]
            row = TendisDtsServer()
            row.bk_cloud_id = cluster["bk_cloud_id"]
            row.ip = cluster["ip"]
            row.city_id = cluster["bk_city_id"]
            row.city_name = cluster["bk_city_name"]
            row.status = 0
            row.heartbeat_time = "1997-01-01 00:00:00"
            row.save()
        elif global_data["ticket_type"] == TicketType.REDIS_REMOVE_DTS_SERVER.value:
            cluster = kwargs["cluster"]
            TendisDtsServer.objects.filter(ip=cluster["ip"], bk_cloud_id=cluster["bk_cloud_id"]).delete()

        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RedisDtsServerMetaComponent(Component):
    name = __name__
    code = "redis_dts_server_meta"
    bound_service = RedisDtsServerMetaService
