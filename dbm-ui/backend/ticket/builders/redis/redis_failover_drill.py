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

from backend.db_meta.models import AppCache
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisInstanceTicketFlowBuilder, RedisOpsBaseDetailSerializer
from backend.ticket.constants import TicketType


class RedisFailoverDrillDetailSerializer(RedisOpsBaseDetailSerializer):
    class FailoverDrillInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群id"))

    drill_infos = serializers.ListSerializer(help_text=_("容灾演练信息"), child=FailoverDrillInfoSerializer())


class RedisFailoverDrillParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_failover_drill

    def format_ticket_data(self):
        app = AppCache.objects.get(bk_biz_id=self.ticket_data["bk_biz_id"])
        self.ticket_data.update(bk_biz_id=app.bk_biz_id, db_app_addr=app.db_app_abbr)


@builders.BuilderFactory.register(TicketType.REDIS_FAILOVER_DRILL)
class RedisFailoverDrillFlowBuilder(BaseRedisInstanceTicketFlowBuilder):
    serializer = RedisFailoverDrillDetailSerializer
    inner_flow_builder = RedisFailoverDrillParamBuilder
    inner_flow_name = _("redis容灾演练")
    default_need_itsm = False
    default_need_manual_confirm = False
