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

from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import DisplayInfoSerializer
from backend.ticket.builders.redis.base import (
    BaseRedisTicketFlowBuilder,
    ClusterValidateMixin,
    RedisBaseOperateDetailSerializer,
)
from backend.ticket.constants import LoadConfirmType, TicketType


class RedisLoadModuleSerializer(RedisBaseOperateDetailSerializer):
    """redis集群加载module"""

    class InfoSerializer(DisplayInfoSerializer, ClusterValidateMixin, serializers.Serializer):

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        db_version = serializers.CharField(help_text=_("版本号"))
        load_modules = serializers.ListField(
            help_text=_("module类型列表"),
            child=serializers.ChoiceField(
                help_text=_("module类型"), choices=LoadConfirmType.get_choices(), default=LoadConfirmType.REDIS_BLOOM
            ),
            required=False,
        )

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisLoadModuleParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_load_modules

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_LOAD_MODULES, is_apply=True)
class RedisLoadModuleFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisLoadModuleSerializer
    inner_flow_builder = RedisLoadModuleParamBuilder
    inner_flow_name = _("Redis 存量集群安装module")
