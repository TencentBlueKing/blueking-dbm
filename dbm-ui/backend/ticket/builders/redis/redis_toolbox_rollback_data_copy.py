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
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
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

    def validate(self, attr):
        """根据复制类型校验info"""

        dst_cluster_set = set()
        src_cluster_set = set()
        for info in attr.get("infos"):
            src_cluster = info.get("src_cluster")
            dst_cluster = info.get("dst_cluster")

            ClusterValidateMixin.check_cluster_phase(dst_cluster)

            if not TbTendisRollbackTasks.objects.filter(
                prod_cluster_id=dst_cluster,
                temp_cluster_proxy=src_cluster,
                recovery_time_point=info.get("recovery_time_point"),
            ).exists():
                raise serializers.ValidationError(_("构造记录不存在，请确认: {}").format(src_cluster))

            if dst_cluster in dst_cluster_set:
                raise serializers.ValidationError(_("目标集群不能重复: {}").format(dst_cluster))

            if src_cluster in src_cluster_set:
                raise serializers.ValidationError(_("源集群不能重复: {}").format(src_cluster))

            if info["key_white_regex"] == "" and info["key_black_regex"] == "":
                raise serializers.ValidationError(_("请补齐缺少正则配置的行"))

            src_cluster_set.add(src_cluster)
            dst_cluster_set.add(dst_cluster)

        return attr


class RedisRollbackDataCopyParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_data_copy

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_ROLLBACK_DATA_COPY)
class RedisRollbackDataCopyFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisRollbackDataCopyDetailSerializer
    inner_flow_builder = RedisRollbackDataCopyParamBuilder
    inner_flow_name = _("Redis 构造实例数据回写")
