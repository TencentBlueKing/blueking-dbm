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
from backend.flow.engine.bamboo.scene.redis.redis_proxy_scale import RedisProxyScaleFlow
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    HostInfoSerializer,
    HostRecycleSerializer,
    SkipToRepresentationMixin,
    fetch_cluster_ids,
)
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder, ClusterValidateMixin
from backend.ticket.constants import SwitchConfirmType, TicketType


class ProxyScaleDownDetailSerializer(SkipToRepresentationMixin, ClusterValidateMixin, serializers.Serializer):
    """proxy缩容"""

    class InfoSerializer(serializers.Serializer):
        class OldProxySerializer(serializers.Serializer):
            proxy_reduced_hosts = serializers.ListSerializer(
                help_text=_("缩容指定主机"), child=HostInfoSerializer(), required=False
            )

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        target_proxy_count = serializers.IntegerField(help_text=_("目标proxy数量"), min_value=2, required=False)
        proxy_reduce_count = serializers.IntegerField(help_text=_("缩容proxy数量"), required=False)
        old_nodes = OldProxySerializer(help_text=_("缩容指定proxy"), required=False)
        online_switch_type = serializers.ChoiceField(
            help_text=_("切换类型"), choices=SwitchConfirmType.get_choices(), default=SwitchConfirmType.NO_CONFIRM
        )

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)

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
            # 提前存入proxy信息用于后续patch
            attrs.update(proxy_insts=cluster.proxyinstance_set.all(), bk_cloud_id=cluster.bk_cloud_id)

        return attrs


class ProxyScaleDownParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_proxy_scale

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_PROXY_SCALE_DOWN, is_recycle=True)
class ProxyScaleDownFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = ProxyScaleDownDetailSerializer
    inner_flow_builder = ProxyScaleDownParamBuilder
    inner_flow_name = _("Proxy缩容")
    need_patch_recycle_host_details = True

    def patch_old_proxy_nodes(self):
        for info in self.ticket.details["infos"]:
            proxy_insts = info.pop("proxy_insts")

            if info.get("old_nodes"):
                continue

            # 获取proxy ip和ip与host id的映射
            proxy_ip__host = {proxy.machine.ip: proxy.machine for proxy in proxy_insts}
            proxy_ips = list(proxy_insts.values_list("machine__ip", flat=True))
            # 获取实际下架的ip
            target_proxy_count = info["target_proxy_count"]
            down_ips = RedisProxyScaleFlow.calc_scale_down_ips(self.ticket.bk_biz_id, proxy_ips, target_proxy_count)
            # 补充old proxy nodes信息
            info["old_nodes"] = {"proxy": [{"bk_host_id": proxy_ip__host[ip], "ip": ip} for ip in down_ips]}

    def patch_ticket_detail(self):
        self.patch_old_proxy_nodes()
        super().patch_ticket_detail()
