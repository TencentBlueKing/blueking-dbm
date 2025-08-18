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
from collections import defaultdict

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.spider import SpiderController
from backend.flow.engine.validate.exceptions import DisasterToleranceLevelFailedException
from backend.flow.utils.base.roundrobin_algorithm import get_value_for_roundrobin
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer, HostRecycleSerializer, fetch_cluster_ids
from backend.ticket.builders.common.constants import ShrinkType
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbSpiderReduceNodesDetailSerializer(TendbBaseOperateDetailSerializer):
    class SpiderNodesItemSerializer(serializers.Serializer):
        class OldSpiderSerializer(serializers.Serializer):
            spider_reduced_hosts = serializers.ListSerializer(help_text=_("缩容spider信息"), child=HostInfoSerializer())

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        spider_reduced_to_count = serializers.IntegerField(help_text=_("剩余spider数量"), required=False)
        old_nodes = OldSpiderSerializer(help_text=_("缩容指定主机"), required=False)
        reduce_spider_role = serializers.ChoiceField(help_text=_("角色"), choices=TenDBClusterSpiderRole.get_choices())

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"))
    infos = serializers.ListSerializer(help_text=_("缩容信息"), child=SpiderNodesItemSerializer())
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)
    shrink_type = serializers.ChoiceField(
        help_text=_("缩容方式"), choices=ShrinkType.get_choices(), default=ShrinkType.QUANTITY.value
    )
    disable_manual_confirm = serializers.BooleanField(help_text=(_("自愈单据禁用人工确认")), default=False)

    def validate(self, attrs):
        super().validate(attrs)
        self.validate_min_spider_count(attrs)
        return attrs


class TendbSpiderReduceNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.reduce_spider_nodes_scene

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            info["spider_reduced_hosts"] = info.pop("old_nodes")["spider_reduced_hosts"]


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_REDUCE_NODES, is_recycle=True)
class TendbSpiderReduceNodesFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbSpiderReduceNodesDetailSerializer
    inner_flow_builder = TendbSpiderReduceNodesFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 接入层缩容")
    need_patch_recycle_host_details = True
    need_patch_machine_details = True

    def calc_reduce_spider(self):
        """计算实际缩容的spider主机"""
        cluster_ids = fetch_cluster_ids(self.ticket.details["infos"])
        clusters = Cluster.objects.prefetch_related("proxyinstance_set").filter(id__in=cluster_ids)
        cluster_map = {cluster.id: cluster for cluster in clusters}
        for info in self.ticket.details["infos"]:
            # 如果制定主机缩容，则忽略
            if info.get("old_nodes"):
                continue

            cluster = cluster_map[info["cluster_id"]]
            reduce_spider_role = info["reduce_spider_role"]
            info["old_nodes"] = {}

            # 计算合理的待下架的spider节点列表
            info["old_nodes"]["spider_reduced_hosts"] = self.calc_reduce_spider_for_cluster(
                cluster, reduce_spider_role, info["spider_reduced_to_count"]
            )

    @classmethod
    def calc_reduce_spider_for_cluster(cls, cluster: Cluster, role: TenDBClusterSpiderRole, reduced_to_count: int):
        """
        已集群为维度，计算单据每个集群需要下架的spider节点
        针对指定数量下架的场景
        @param cluster: 集群原信息
        @param role: 下架的spider角色
        @param reduced_to_count: 下架后剩余的spider节点数量
        """
        sub_zone_ips = defaultdict(set)

        # 首先根据每个园区ID，给每个spider节点分组
        ctl_primary = cluster.tendbcluster_ctl_primary_address()
        all_spiders = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=role).prefetch_related(
            "machine"
        )
        for spider in all_spiders:
            sub_zone_ips[spider.machine.bk_sub_zone_id].add(spider.machine.ip)

        if (
            cluster.disaster_tolerance_level
            in (
                AffinityEnum.NONE,
                AffinityEnum.CROSS_RACK,
                AffinityEnum.MAX_EACH_ZONE_EQUAL,
            )
            or reduced_to_count == 1
            or role == TenDBClusterSpiderRole.SPIDER_SLAVE
        ):
            # 这类容灾级别不需要判断容灾级别，属于没有要求
            # 获取剩余spider数量只有一台的情况下，也没有容灾要求
            # 如果处理spider slave角色，也没有容灾要求
            # 尽量避开ctl primary
            except_reduce_spiders = [
                spider for spider in all_spiders if spider.machine.ip != ctl_primary.split(":")[0]
            ]
            return [
                {"ip": s.machine.ip, "bk_host_id": s.machine.bk_host_id}
                for s in except_reduce_spiders[: len(all_spiders) - reduced_to_count]
            ]

        if cluster.disaster_tolerance_level == AffinityEnum.CROS_SUBZONE:
            # 属于跨园区的容灾级别，保证sub_zone_id至少要两个以上的
            # 用公平轮训方案，按照园区分组选出要保留的spider ip
            if len(sub_zone_ips) <= 1:
                # 集群当年不能满足跨园区特性，先报出异常
                raise Exception(
                    _(
                        "集群[{}]当前spider层不符合容灾级别[{}], {}节点都在一个园区里{}".format(
                            cluster.immute_domain, cluster.disaster_tolerance_level, role, sub_zone_ips.keys()
                        )
                    )
                )
            remaining_spider_ips = get_value_for_roundrobin(sub_zone_ips, reduced_to_count)
            # 反向计算出缩容的spider ip
            return [
                {"ip": s.machine.ip, "bk_host_id": s.machine.bk_host_id}
                for s in all_spiders.exclude(machine__ip__in=list(remaining_spider_ips))
            ]

        if cluster.disaster_tolerance_level == AffinityEnum.SAME_SUBZONE:
            # 属于同园区（无机架要求）的容灾级别，保证sub_zone_id有且只有一个
            # 根据分组取出同园区的ip，作为保留，如果没有任意一个分组能满足需要，则应该报异常
            remaining_spider_ips = list()
            for values in sub_zone_ips.values():
                if len(values) >= reduced_to_count:
                    remaining_spider_ips.extend(list(values)[:reduced_to_count])

            if not remaining_spider_ips:
                raise Exception(
                    _(
                        "集群[{}]根据设置的容灾级别[{}]，计算不出缩容后能满足spider节点数量， 请检查{}节点的园区分布".format(
                            cluster.immute_domain, cluster.disaster_tolerance_level, role
                        )
                    )
                )

            # 反向计算出缩容的spider ip
            return [
                {"ip": s.machine.ip, "bk_host_id": s.machine.bk_host_id}
                for s in all_spiders.exclude(machine__ip__in=list(remaining_spider_ips))
            ]

        if cluster.disaster_tolerance_level == AffinityEnum.SAME_SUBZONE_CROSS_SWTICH:
            # 属于同园区的容灾级别，保证sub_zone_id有且只有一个， 同时机架保证至少两个以上
            # 先挑出满足保留数量长度的分组
            for values in sub_zone_ips.values():
                if len(values) >= reduced_to_count:
                    # 根据分组的所有主机IP，重新建立新分组信息，以机架ID
                    rack_ips = defaultdict(set)
                    for spider in all_spiders.filter(machine__ip__in=list(values)):
                        rack_ips[spider.machine.bk_rack_id].add(spider.machine.ip)
                    # 计算它的key的长度，如果长度不大于1，退出循环，找下一个满足的分组
                    if len(rack_ips.keys()) <= 1:
                        continue
                    # 满足条件的话，公平轮询去拿ip
                    remaining_spider_ips = get_value_for_roundrobin(rack_ips, reduced_to_count)

                    # 反向计算出缩容的spider ip
                    return [
                        {"ip": s.machine.ip, "bk_host_id": s.machine.bk_host_id}
                        for s in all_spiders.exclude(machine__ip__in=list(remaining_spider_ips))
                    ]
            raise Exception(
                _(
                    "集群[{}]根据设置的容灾级别[{}]，计算不出缩容后能满足spider节点数量， 请检查{}节点的园区分布".format(
                        cluster.immute_domain, cluster.disaster_tolerance_level, role
                    )
                )
            )

        raise DisasterToleranceLevelFailedException(
            f"[{cluster.immute_domain}]not support cluster.disaster_tolerance_level {cluster.disaster_tolerance_level}"
        )

    def patch_ticket_detail(self):
        self.calc_reduce_spider()
        super().patch_ticket_detail()
