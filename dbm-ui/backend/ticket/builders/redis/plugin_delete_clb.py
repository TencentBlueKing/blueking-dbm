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
from django.utils.translation import ugettext_lazy as _

from backend.flow.engine.controller.name_service import NameServiceController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, RedisSingleOpsBaseDetailSerializer
from backend.ticket.constants import TicketType


class RedisPluginDeleteCLBDetailSerializer(RedisSingleOpsBaseDetailSerializer):
    pass


class RedisPluginDeleteCLBFlowParamBuilder(builders.FlowParamBuilder):
    controller = NameServiceController.clb_delete

    def format_ticket_data(self):
        """
        {
            "uid": 340,
            "ticket_type": "REDIS_PLUGIN_DELETE_CLB",
            "created_by": "admin",
            "cluster_id": 1111
        }
        """
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_PLUGIN_DELETE_CLB)
class RedisPluginDeleteCLBFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisPluginDeleteCLBDetailSerializer
    inner_flow_builder = RedisPluginDeleteCLBFlowParamBuilder
    inner_flow_name = _("删除CLB")
    default_need_itsm = False
