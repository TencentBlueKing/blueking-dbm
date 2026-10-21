# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import MachineType
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, HostInfoSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType

SPIDER_SLAVE_NEW_KEY = "spider_slave_new_ip_list"


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

    def validate(self, attrs):
        # 先走基类公共校验链（业务归属 / 纳管 / 集群状态 / validated_params）
        attrs = super().validate(attrs)
        # Spider Master 与中控同机部署，重建 master 必须至少 2 台，不允许单点中控
        for info in attrs.get("infos", []):
            master_spec = (info.get("resource_spec") or {}).get("spider_master_new_ip_list") or {}
            master_count = master_spec.get("count") or len(master_spec.get("hosts") or [])
            master_count = master_count or len(info.get("spider_master_new_ip_list") or [])
            if master_count and master_count < 2:
                raise serializers.ValidationError(
                    _("Spider Master 重建后数量不能少于 2 台（不允许单点中控），请检查集群 {} 的重建数量").format(info.get("cluster_id"))
                )
        return attrs


class SpiderLayerDisasterRecoverFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendbcluster_spider_layer_disaster_recover_scene


class TendbClusterSpiderLayerDrResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(
            role="spider_master_new_ip_list", remain_machine_type=MachineType.PROXY, replace_key="proxy", tolerance=0.5
        )

    @staticmethod
    def is_slave_role(info: dict) -> bool:
        """按资源申请角色判断本条 info 重建的是 spider_slave 还是 spider_master"""
        return SPIDER_SLAVE_NEW_KEY in (info.get("resource_spec") or {}) or bool(info.get(SPIDER_SLAVE_NEW_KEY))

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        infos = next_flow.details.get("ticket_data", {}).get("infos", [])
        for info in infos:
            if "old_nodes" in info:
                old_nodes_dict = info.pop("old_nodes")
                # 前端无论重建哪个角色，旧机器都放在 old_nodes.proxy，这里按角色映射到流程所需字段
                old_key = "spider_slave_old_ip_list" if self.is_slave_role(info) else "spider_master_old_ip_list"
                info[old_key] = old_nodes_dict.get("proxy", [])

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(
    TicketType.TENDBCLUSTER_SPIDER_LAYER_DR, is_recycle=True, is_apply=True, iam=ActionEnum.TENDBCLUSTER_MANAGE
)
class SpiderLayerDisasterRecoverFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderLayerDisasterRecoverDetailSerializer
    inner_flow_builder = SpiderLayerDisasterRecoverFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 接入层灾难重建")
    resource_batch_apply_builder = TendbClusterSpiderLayerDrResourceParamBuilder
    # 提单时从 infos[].old_nodes 提取旧 spider（master 或 slave）写入 recycle_hosts，
    # 单据成功后由 TicketFlowManager 自动派生主机回收单据（RECYCLE_OLD_HOST）
    need_patch_recycle_host_details = True
    # validator = SpiderController.tendbcluster_spider_layer_disaster_recover_scene.validator
