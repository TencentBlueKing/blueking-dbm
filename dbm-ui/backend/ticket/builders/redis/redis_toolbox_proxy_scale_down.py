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


class ProxyScaleDownDetailSerializer(serializers.Serializer):
    """proxy缩容"""

    class InfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        target_proxy_count = serializers.IntegerField(help_text=_("目标proxy数量"))
        online_switch_type = serializers.ChoiceField(
            help_text=_("切换类型"), choices=SwitchConfirmType.get_choices(), default=SwitchConfirmType.NO_CONFIRM
        )

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class ProxyScaleDownParamBuilder(builders.FlowParamBuilder):
    controller = None

    def format_ticket_data(self):
        super().format_ticket_data()


class ProxyScaleDownResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.PROXY_SCALE_DOWN)
class ProxyScaleDownFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = ProxyScaleDownDetailSerializer
    inner_flow_builder = ProxyScaleDownParamBuilder
    inner_flow_name = _("Proxy缩容")
    resource_batch_apply_builder = ProxyScaleDownResourceParamBuilder
