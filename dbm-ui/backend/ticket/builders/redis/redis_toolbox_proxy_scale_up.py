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
import logging

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class ProxyScaleUpDetailSerializer(serializers.Serializer):
    """proxy扩容"""

    class InfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        target_proxy_count = serializers.IntegerField(help_text=_("目标proxy数量"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class ProxyScaleUpParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_proxy_scale

    def format_ticket_data(self):
        super().format_ticket_data()


class ProxyScaleUpResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        logger.info("ticket_data: %s", ticket_data)
        super().post_callback()


@builders.BuilderFactory.register(TicketType.PROXY_SCALE_UP)
class ProxyScaleUpFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = ProxyScaleUpDetailSerializer
    inner_flow_builder = ProxyScaleUpParamBuilder
    inner_flow_name = _("Proxy扩容")
    resource_batch_apply_builder = ProxyScaleUpResourceParamBuilder

    @property
    def need_itsm(self):
        return False