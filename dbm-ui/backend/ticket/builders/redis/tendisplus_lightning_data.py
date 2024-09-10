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

from backend.flow.engine.bamboo.scene.redis.tendisplus_lightning_data import TendisPlusLightningData
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class TendisPlusLightningDataSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """TendisPlus闪电导入数据"""

    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        cos_file_keys = serializers.ListField(help_text=_("cos文件key列表"), child=serializers.CharField())

    infos = serializers.ListField(help_text=_("参数列表"), child=InfoSerializer())

    def validate(self, attr):
        TendisPlusLightningData.precheck(attr["infos"])
        return attr


class TendisplusLightingDataParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.tendisplus_lightning_data

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_TENDISPLUS_LIGHTNING_DATA, is_apply=False)
class RedisClusterRenameDomainFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = TendisPlusLightningDataSerializer
    inner_flow_builder = TendisplusLightingDataParamBuilder
    inner_flow_name = _("tendisplus闪电导入数据")
    default_need_itsm = False
    default_need_manual_confirm = True

    def patch_ticket_detail(self):
        super().patch_ticket_detail()
