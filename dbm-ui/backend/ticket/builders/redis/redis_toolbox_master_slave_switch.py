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
from rest_framework import serializers

from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import SwitchConfirmType, TicketType


class RedisMasterSlaveSwitchDetailSerializer(serializers.Serializer):
    """主从故障切换"""

    class InfoSerializer(serializers.Serializer):
        class PairSerializer(serializers.Serializer):
            redis_master = serializers.IPAddressField(help_text=_("master主机"))
            redis_slave = serializers.IPAddressField(help_text=_("slave主机"))

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        pairs = serializers.ListField(help_text=_("主从切换对"), child=PairSerializer())
        online_switch_type = serializers.ChoiceField(
            help_text=_("切换类型"), choices=SwitchConfirmType.get_choices(), default=SwitchConfirmType.NO_CONFIRM
        )

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisMasterSlaveSwitchParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_failover_scene


@builders.BuilderFactory.register(TicketType.REDIS_MASTER_SLAVE_SWITCH)
class RedisMasterSlaveSwitchFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisMasterSlaveSwitchDetailSerializer
    inner_flow_builder = RedisMasterSlaveSwitchParamBuilder
    inner_flow_name = _("Redis 主从故障切换")

    @property
    def need_itsm(self):
        return False
