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
from backend.ticket.constants import TicketType


class RedisClusterInstShutdownDetailSerializer(serializers.Serializer):
    """实例下架"""

    class InfoSerializer(serializers.Serializer):
        class HostInfoSerializer(serializers.Serializer):
            ip = serializers.IPAddressField()

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        # bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        proxy = serializers.ListField(help_text=_("proxy列表"), child=HostInfoSerializer(), required=False)
        redis_slave = serializers.ListField(help_text=_("slave列表"), child=HostInfoSerializer(), required=False)

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisClusterInstShutdownParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_instance_shutdown

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN, is_apply=False)
class RedisClusterInstShutdownFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisClusterInstShutdownDetailSerializer
    inner_flow_builder = RedisClusterInstShutdownParamBuilder
    inner_flow_name = _("实例下架")

    def patch_ticket_detail(self):
        super().patch_ticket_detail()
