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

from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import (
    BaseRedisTicketFlowBuilder,
    RedisBasePauseParamBuilder,
    RedisOpsBaseDetailSerializer,
)
from backend.ticket.constants import TicketType


class RedisPurgeDetailSerializer(RedisOpsBaseDetailSerializer):
    pass


class RedisPurgeFlowParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_flush_data

    def format_ticket_data(self):
        """
        {
            "uid":"2022051612120001",
            "created_by":"xxxx",
            "bk_biz_id":2005000194,
            "ticket_type":"REDIS_PURGE",
            "rules":[
                {
                        "cluster_id": 1,
                        "cluster_type": "TwemproxyRedisInstance",
                        "domain": "cache.test1.redistest.db",
                        "target": "master",
                        "force": true, //safe（检查）/force（强制）
                        "backup": true,
                }
            ]
        }
        """
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_PURGE)
class RedisPurgeFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisPurgeDetailSerializer
    inner_flow_builder = RedisPurgeFlowParamBuilder
    inner_flow_name = _("集群清档")
    pause_node_builder = RedisBasePauseParamBuilder

    @property
    def need_manual_confirm(self):
        return True
