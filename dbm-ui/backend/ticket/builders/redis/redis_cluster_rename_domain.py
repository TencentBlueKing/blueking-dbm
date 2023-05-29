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

from backend.flow.engine.bamboo.scene.redis.redis_cluster_rename_domain import RedisClusterRenameDomainFlow
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class RedisClusterRenameDomainSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """集群重命名域名设置"""

    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        new_domain = serializers.CharField(help_text=_("集群新域名"))

        def validate(self, attr):
            RedisClusterRenameDomainFlow.precheck_info_item(attr["cluster_id"], attr["new_domain"])
            return attr

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisClusterRenameDomainParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_rename_domain

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_RENAME_DOMAIN, is_apply=False)
class RedisClusterRenameDomainFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisClusterRenameDomainSerializer
    inner_flow_builder = RedisClusterRenameDomainParamBuilder
    inner_flow_name = _("集群域名重命名")
    default_need_itsm = False
    default_need_manual_confirm = False

    def patch_ticket_detail(self):
        super().patch_ticket_detail()
