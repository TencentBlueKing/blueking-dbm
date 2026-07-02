# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import MachineType
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, HostInfoSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class SpiderLayerDisasterRecoverDetailSerializer(TendbBaseOperateDetailSerializer):
    class SpiderDrInfoSerializer(serializers.Serializer):
        class OldProxySerializer(serializers.Serializer):
            proxy = serializers.ListSerializer(child=HostInfoSerializer())

        cluster_id = serializers.IntegerField(help_text=_("集群 ID"), required=True)
        spider_master_new_ip_list = serializers.ListField(
            help_text=_("新 Spider Master IP 列表"), child=HostInfoSerializer(), required=False
        )
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        old_nodes = OldProxySerializer(help_text=_("旧 Spider Master IP 列表"))
        strip_dns_before_install = serializers.BooleanField(help_text=_("安装前是否摘除 DNS"), default=True)

    infos = serializers.ListField(help_text=_("Spider 容灾切换/替换列表"), child=SpiderDrInfoSerializer())
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL.value
    )


class SpiderLayerDisasterRecoverFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendbcluster_spider_layer_disaster_recover_scene


class TendbClusterSpiderLayerDrResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(
            role="spider_master_new_ip_list", remain_machine_type=MachineType.PROXY, replace_key="proxy", tolerance=0.5
        )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        infos = next_flow.details.get("ticket_data", {}).get("infos", [])
        for info in infos:
            if "old_nodes" in info:
                old_nodes_dict = info.pop("old_nodes")
                info["spider_master_old_ip_list"] = old_nodes_dict.get("proxy", [])

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_LAYER_DR, is_recycle=True, is_apply=True)
class SpiderLayerDisasterRecoverFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderLayerDisasterRecoverDetailSerializer
    inner_flow_builder = SpiderLayerDisasterRecoverFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 接入层灾难重建")
    resource_batch_apply_builder = TendbClusterSpiderLayerDrResourceParamBuilder
    # validator = SpiderController.tendbcluster_spider_layer_disaster_recover_scene.validator
