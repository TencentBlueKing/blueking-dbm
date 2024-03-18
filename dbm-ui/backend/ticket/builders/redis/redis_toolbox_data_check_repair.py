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

from backend.db_services.redis.redis_dts.enums import DtsDataRepairMode, ExecuteMode
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, SkipToRepresentationMixin
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import TicketType


class RedisDataCheckRepairDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """数据校验与修复"""

    class InfoSerializer(serializers.Serializer):
        bill_id = serializers.IntegerField(help_text=_("任务ID"))
        src_cluster = serializers.CharField(help_text=_("源集群访问入口"))
        dst_cluster = serializers.CharField(help_text=_("目标集群访问入口"))
        src_instances = serializers.ListField(
            help_text=_("源实例列表"), allow_empty=False, child=serializers.CharField(help_text=_("IP:PORT"))
        )
        key_white_regex = serializers.CharField(help_text=_("包含key"), allow_blank=True)
        key_black_regex = serializers.CharField(help_text=_("排除key"), allow_blank=True)

    execute_mode = serializers.ChoiceField(help_text=_("执行模式"), choices=ExecuteMode.get_choices())
    specified_execution_time = DBTimezoneField(help_text=_("执行模式为定时执行时，需要设置执行时间"), required=False, allow_blank=True)

    keep_check_and_repair = serializers.BooleanField(help_text=_("是否保持校验"))
    check_stop_time = DBTimezoneField(help_text=_("校验终止时间，当不保持校验时，需要设置该时间"), required=False, allow_blank=True)

    data_repair_enabled = serializers.BooleanField(help_text=_("是否修复数据"))
    repair_mode = serializers.ChoiceField(help_text=_("数据修复模式"), choices=DtsDataRepairMode.get_choices())

    infos = serializers.ListField(help_text=_("批量校验与修复列表"), child=InfoSerializer(), allow_empty=False)

    def validate(self, attr):
        """进一步校验info"""
        key_white_regex_cnt = sum(map(lambda info: 1 if len(info["key_white_regex"]) else 0, attr["infos"]))
        key_black_regex_cnt = sum(map(lambda info: 1 if len(info["key_black_regex"]) else 0, attr["infos"]))
        if (key_white_regex_cnt + key_black_regex_cnt) < len(attr["infos"]):
            raise serializers.ValidationError(_("请补齐缺少正则配置的行"))

        return attr


class RedisDataCheckRepairParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_data_check_repair

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisDataCheckRepairResourceParamBuilder(BaseOperateResourceParamBuilder):
    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_DATACOPY_CHECK_REPAIR)
class RedisDataCheckRepairFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisDataCheckRepairDetailSerializer
    inner_flow_builder = RedisDataCheckRepairParamBuilder
    inner_flow_name = _("Redis 数据校验与修复")
    resource_batch_apply_builder = RedisDataCheckRepairResourceParamBuilder
