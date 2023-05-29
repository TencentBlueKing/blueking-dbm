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
import logging.config

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import Cluster
from backend.db_monitor.serializers import AlarmCallBackDataSerializer
from backend.db_services.redis.maxmemory_set.maxmemory_set import RedisClusterMaxmemorySet
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class RedisClusterMaxmemorySetAlarmTransformSerializer(AlarmCallBackDataSerializer):
    """
    接收告警事件,确认是否可执行maxmemory,执行maxmemory设置单据
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        logger.info("RedisClusterMaxmemorySetAlarmTransformSerializer validate data:{}".format(data))
        dimensions = data["callback_message"]["event"]["dimensions"]
        cluster = Cluster.objects.get(immute_domain=dimensions["cluster_domain"])
        maxmemory_set_obj = RedisClusterMaxmemorySet(cluster_id=cluster.id)
        maxmemory_set_obj.get_cluster_data()
        maxmemory_set_obj.get_maxmemory_set_config()
        skip, msg = self.is_skip_maxmemory_set()
        if skip:
            raise serializers.ValidationError(msg)
        maxmemory_set_obj.get_cluster_masters_used_memory()
        should_update, msg = self.should_update_cluter_maxmemory()
        if not should_update:
            raise serializers.ValidationError(msg)
        maxmemory_set_obj.save_cluster_backends()
        return attrs

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        dimensions = data["callback_message"]["event"]["dimensions"]
        cluster = Cluster.objects.get(immute_domain=dimensions["cluster_domain"])
        ticket_detail = {
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_ids": [cluster.id],
        }
        return ticket_detail


class RedisClusterMaxMemorySetDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """集群maxmemory设置"""

    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())


class RedisClusterMaxMemorySetParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_maxmemory_set

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_MAXMEMORY_SET, is_apply=False)
class RedisClusterMaxMemorySetFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisClusterMaxMemorySetDetailSerializer
    alarm_transform_serializer = RedisClusterMaxmemorySetAlarmTransformSerializer
    inner_flow_builder = RedisClusterMaxMemorySetParamBuilder
    inner_flow_name = _("集群maxmemory设置")
    default_need_itsm = False
    default_need_manual_confirm = False

    def patch_ticket_detail(self):
        super().patch_ticket_detail()
