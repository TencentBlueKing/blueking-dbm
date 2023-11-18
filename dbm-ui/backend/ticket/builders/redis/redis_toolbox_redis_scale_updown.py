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

from backend.configuration.constants import AffinityEnum
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import SwitchConfirmType, TicketType


class RedisScaleUpDownDetailSerializer(serializers.Serializer):
    """redis集群容量变更"""

    class InfoSerializer(ClusterValidateMixin, serializers.Serializer):
        class ResourceSpecSerializer(serializers.Serializer):
            class BackendGroupSerializer(serializers.Serializer):
                spec_id = serializers.IntegerField(help_text=_("规格ID"))
                count = serializers.IntegerField(help_text=_("数量"))
                affinity = serializers.ChoiceField(
                    help_text=_("亲和性"), choices=AffinityEnum.get_choices(), default=AffinityEnum.NONE
                )

            backend_group = BackendGroupSerializer()

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        shard_num = serializers.IntegerField(help_text=_("集群分片数"))
        group_num = serializers.IntegerField(help_text=_("部署机器组数"))
        db_version = serializers.CharField(help_text=_("版本号"))
        online_switch_type = serializers.ChoiceField(
            help_text=_("切换类型"), choices=SwitchConfirmType.get_choices(), default=SwitchConfirmType.NO_CONFIRM
        )
        resource_spec = ResourceSpecSerializer(help_text=_("资源申请"))
        capacity = serializers.IntegerField(help_text=_("当前容量需求"))
        future_capacity = serializers.IntegerField(help_text=_("未来容量需求"))

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisScaleUpDownParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_backend_scale

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisScaleUpDownResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_SCALE_UPDOWN, is_apply=True)
class RedisScaleUpDownFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisScaleUpDownDetailSerializer
    inner_flow_builder = RedisScaleUpDownParamBuilder
    inner_flow_name = _("Redis 集群容量变更")
    resource_batch_apply_builder = RedisScaleUpDownResourceParamBuilder

    @property
    def need_itsm(self):
        return False
