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

from backend.db_services.dbbase.constants import IpSource
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import SwitchConfirmType, TicketType


class RedisScaleUpDetailSerializer(serializers.Serializer):
    """redis扩容"""

    class InfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=True)
        db_version = serializers.CharField(help_text=_("版本号"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=True)

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisScaleUpParamBuilder(builders.FlowParamBuilder):
    controller = None

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisScaleUpResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_SCALE_UP)
class RedisScaleUpFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisScaleUpDetailSerializer
    inner_flow_builder = RedisScaleUpParamBuilder
    inner_flow_name = _("Redis扩容")
    resource_batch_apply_builder = RedisScaleUpResourceParamBuilder
