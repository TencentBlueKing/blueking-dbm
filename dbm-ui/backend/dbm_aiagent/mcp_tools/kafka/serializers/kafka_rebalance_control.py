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


class GetRebalanceProgressInputSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(help_text=_("Kafka rebalance 单据ID"))


class GetRebalanceProgressOutputSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(help_text=_("单据ID"))
    current_topic = serializers.CharField(help_text=_("当前正在处理的topic"), required=False, allow_blank=True)
    current = serializers.IntegerField(help_text=_("已完成的topic数量"), required=False)
    total = serializers.IntegerField(help_text=_("总topic数量"), required=False)
    percent = serializers.FloatField(help_text=_("完成百分比"), required=False)
    status = serializers.CharField(help_text=_("执行状态：pending/in_progress/completed/failed"))
    current_throttle_mib_s = serializers.FloatField(
        help_text=_("当前限速，单位MiB/s（1024x1024字节/秒）"), required=False, allow_null=True
    )
    override_mode = serializers.CharField(help_text=_("调速模式：auto（自动）/manual（人工控制）"), required=False)
    message = serializers.CharField(help_text=_("提示信息"), required=False, allow_blank=True)


class SetRebalanceThrottleInputSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(help_text=_("Kafka rebalance 单据ID"))
    throttle_mib_s = serializers.IntegerField(help_text=_("限速值，单位MiB/s（1024x1024字节/秒）"), min_value=1)


class SetRebalanceThrottleOutputSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(help_text=_("单据ID"))
    throttle_mib_s = serializers.FloatField(help_text=_("设置后的限速值，单位MiB/s（1024x1024字节/秒）"))
    override_mode = serializers.CharField(help_text=_("当前调速模式：auto/manual"))
    message = serializers.CharField(help_text=_("提示信息"), required=False, allow_blank=True)


class ResumeAutoThrottleInputSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(help_text=_("Kafka rebalance 单据ID"))


class ResumeAutoThrottleOutputSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(help_text=_("单据ID"))
    override_mode = serializers.CharField(help_text=_("当前调速模式：auto/manual"))
    message = serializers.CharField(help_text=_("提示信息"), required=False, allow_blank=True)
