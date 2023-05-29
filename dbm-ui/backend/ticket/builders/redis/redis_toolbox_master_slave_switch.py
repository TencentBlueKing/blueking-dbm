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

from backend.db_meta.models import Cluster
from backend.db_services.redis.toolbox.handlers import ToolboxHandler
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import SwitchConfirmType, TicketType


class RedisMasterSlaveSwitchDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """主从切换"""

    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        class PairSerializer(serializers.Serializer):
            redis_master = serializers.IPAddressField(help_text=_("master主机"))
            redis_slave = serializers.IPAddressField(help_text=_("slave主机"))

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        pairs = serializers.ListField(help_text=_("主从切换对"), child=PairSerializer(), allow_empty=False)
        online_switch_type = serializers.ChoiceField(
            help_text=_("切换类型"), choices=SwitchConfirmType.get_choices(), default=SwitchConfirmType.NO_CONFIRM
        )

        def validate(self, attr):
            """业务逻辑校验"""
            cluster = Cluster.objects.get(id=attr.get("cluster_id"))

            master_slaves = {
                pair["master_ip"]: pair["slave_ip"]
                for pair in ToolboxHandler(self.context.get("bk_biz_id")).query_master_slave_pairs(
                    attr.get("cluster_id")
                )
            }

            for pair in attr["pairs"]:
                if master_slaves.get(pair["redis_master"]) != pair["redis_slave"]:
                    raise serializers.ValidationError(
                        _("集群{}的主从关系不匹配：{} -> {}.").format(
                            cluster.immute_domain,
                            pair["redis_master"],
                            master_slaves.get(pair["redis_master"]),
                        )
                    )

            return attr

    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisMasterSlaveSwitchParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_failover_scene


@builders.BuilderFactory.register(TicketType.REDIS_MASTER_SLAVE_SWITCH)
class RedisMasterSlaveSwitchFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisMasterSlaveSwitchDetailSerializer
    inner_flow_builder = RedisMasterSlaveSwitchParamBuilder
    inner_flow_name = _("Redis 主从切换")
