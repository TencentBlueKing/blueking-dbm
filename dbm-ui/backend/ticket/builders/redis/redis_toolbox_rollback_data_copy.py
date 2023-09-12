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

from backend.db_services.redis.redis_dts.enums import DtsCopyType
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import TicketType, WriteModeType


class RedisRollbackDataCopyDetailSerializer(serializers.Serializer):
    class InfoSerializer(serializers.Serializer):
        src_cluster = serializers.CharField(help_text=_("构造产物访问入口（ip:port）"))
        dst_cluster = serializers.IntegerField(help_text=_("目标集群ID"))
        key_white_regex = serializers.CharField(help_text=_("包含key"), allow_null=True)
        key_black_regex = serializers.CharField(help_text=_("排除key"), allow_blank=True)
        recovery_time_point = serializers.CharField(help_text=_("待构造时间点"))

    dts_copy_type = serializers.ChoiceField(
        choices=(
            (
                DtsCopyType.COPY_FROM_ROLLBACK_INSTANCE.value,
                DtsCopyType.get_choice_label(DtsCopyType.COPY_FROM_ROLLBACK_INSTANCE.value),
            ),
        )
    )
    write_mode = serializers.ChoiceField(choices=WriteModeType.get_choices())
    infos = InfoSerializer(many=True, help_text=_("批量操作参数列表"))


class RedisRollbackDataCopyParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_data_copy

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_ROLLBACK_DATA_COPY)
class RedisRollbackDataCopyFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisRollbackDataCopyDetailSerializer
    inner_flow_builder = RedisRollbackDataCopyParamBuilder
    inner_flow_name = _("Redis 构造实例数据回写")

    @property
    def need_itsm(self):
        return False
