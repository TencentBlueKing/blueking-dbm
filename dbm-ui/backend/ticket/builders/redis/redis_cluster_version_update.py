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

from backend.db_meta.enums.comm import RedisVerUpdateNodeType
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import TicketType


class RedisVersionUpdateDetailSerializer(serializers.Serializer):
    class UpdateInfoSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        node_type = serializers.ChoiceField(help_text=_("节点类型"), choices=RedisVerUpdateNodeType.get_choices())
        current_versions = serializers.ListField(help_text=_("当前版本列表"), child=serializers.CharField())
        target_version = serializers.CharField(help_text=_("目标版本"))

    infos = serializers.ListField(help_text=_("版本升级信息"), child=UpdateInfoSerializer())

    def to_representation(self, details):
        return details

    def validate(self, attrs):
        for info in attrs["infos"]:
            # 校验当前版本不能和目标版本一致
            if info["target_version"] in info["current_versions"]:
                raise serializers.ValidationError(_("当前版本不能和目标版本{}一致").format(info["current_versions"]))

        return attrs


class RedisVersionUpdateFlowParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_version_update_online

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.REDIS_VERSION_UPDATE_ONLINE)
class RedisVersionUpdateFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisVersionUpdateDetailSerializer
    inner_flow_builder = RedisVersionUpdateFlowParamBuilder
    inner_flow_name = _("redis 集群版本升级")
