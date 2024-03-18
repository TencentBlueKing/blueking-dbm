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

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.redis.redis_toolbox_cut_off import (
    RedisClusterCutOffFlowBuilder,
    RedisClusterCutOffResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class RedisClusterAutofixDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """故障自愈"""

    class InfoSerializer(serializers.Serializer):
        class HostInfoSerializer(serializers.Serializer):
            ip = serializers.IPAddressField()
            spec_id = serializers.IntegerField()

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        proxy = serializers.ListField(help_text=_("proxy列表"), child=HostInfoSerializer(), required=False)
        redis_slave = serializers.ListField(help_text=_("slave列表"), child=HostInfoSerializer(), required=False)

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisClusterAutofixParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_auotfix_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisClusterAutofixResourceParamBuilder(RedisClusterCutOffResourceParamBuilder):
    def post_callback(self):
        # 与整机替换的处理方法一致，直接调用父类即可
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_AUTOFIX, is_apply=True)
class RedisClusterAutofixFlowBuilder(RedisClusterCutOffFlowBuilder):
    serializer = RedisClusterAutofixDetailSerializer
    inner_flow_builder = RedisClusterAutofixParamBuilder
    inner_flow_name = _("故障自愈")
    resource_batch_apply_builder = RedisClusterAutofixResourceParamBuilder
    default_need_itsm = True
    default_need_manual_confirm = False

    @property
    def need_itsm(self):
        return True

    def patch_ticket_detail(self):
        # 与整机替换的处理方法一致，直接调用父类即可
        super().patch_ticket_detail()
