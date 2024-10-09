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
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer, SkipToRepresentationMixin, fetch_cluster_ids
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import SwitchConfirmType, TicketType


class ProxyScaleDownDetailSerializer(SkipToRepresentationMixin, ClusterValidateMixin, serializers.Serializer):
    """proxy缩容"""

    class InfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        target_proxy_count = serializers.IntegerField(help_text=_("目标proxy数量"), min_value=2, required=False)
        proxy_reduce_count = serializers.IntegerField(help_text=_("缩容proxy数量"), required=False)
        proxy_reduced_hosts = serializers.ListSerializer(
            help_text=_("缩容指定主机"), child=HostInfoSerializer(), required=False
        )
        online_switch_type = serializers.ChoiceField(
            help_text=_("切换类型"), choices=SwitchConfirmType.get_choices(), default=SwitchConfirmType.NO_CONFIRM
        )

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())

    def validate(self, attrs):
        clusters = Cluster.objects.filter(id__in=fetch_cluster_ids(attrs)).prefetch_related("proxyinstance_set")
        cluster_id__cluster_map = {cluster.id: cluster for cluster in clusters}

        # 验证缩容后数量至少为2
        for info in attrs["infos"]:
            cluster = cluster_id__cluster_map[info["cluster_id"]]
            if info.get("proxy_reduced_hosts"):
                info["target_proxy_count"] = cluster.proxyinstance_set.count() - len(info["proxy_reduced_hosts"])
            if info["target_proxy_count"] < 2:
                raise serializers.ValidationError(_("请保证集群{}缩容后proxy数量不小于2").format(cluster.immute_domain))

        return attrs


class ProxyScaleDownParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_proxy_scale

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_PROXY_SCALE_DOWN)
class ProxyScaleDownFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = ProxyScaleDownDetailSerializer
    inner_flow_builder = ProxyScaleDownParamBuilder
    inner_flow_name = _("Proxy缩容")
