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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, RedisOpsBaseDetailSerializer
from backend.ticket.constants import TicketType


class RedisRollbackExerciseDetailSerializer(RedisOpsBaseDetailSerializer):
    """Redis backup rollback exercise serializer"""

    class RollbackExerciseInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        instance_ip = serializers.CharField(help_text=_("实例IP"))
        instance_port = serializers.IntegerField(help_text=_("实例端口"))
        recovery_time_point = serializers.CharField(help_text=_("恢复时间点"))
        report_id = serializers.IntegerField(help_text=_("任务记录ID"))

    infos = serializers.ListSerializer(help_text=_("回滚演练信息"), child=RollbackExerciseInfoSerializer())
    drill_config = serializers.JSONField(help_text=_("演练设置"), required=True)


class RedisRollbackExerciseParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_rollback_exercise

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(
    TicketType.REDIS_ROLLBACK_EXERCISE,
    is_apply=False,
    is_recycle=True,
)
class RedisRollbackExerciseFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisRollbackExerciseDetailSerializer
    inner_flow_builder = RedisRollbackExerciseParamBuilder
    inner_flow_name = _("Redis 回档演练")
    default_need_itsm = False
    default_need_manual_confirm = False

    @property
    def need_resource_pool(self):
        return False
