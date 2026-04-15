# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class SpiderLayerDisasterRecoverDetailSerializer(TendbBaseOperateDetailSerializer):
    """
    单 info 维度按"IP 列表非空"自描述本次恢复的角色：
      - spider_master_new_ip_list 非空 → 恢复 master 段
      - spider_slave_new_ip_list  非空 → 恢复 slave 段
      - 同时非空 → 同集群同 info 内"安装并行 + 路由串行"五阶段编排
    """

    class InfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))

        # ── master 段 IP 列表（非空时本次恢复 spider_master）─────────
        spider_master_new_ip_list = serializers.ListSerializer(
            child=HostInfoSerializer(),
            required=False,
            default=list,
            help_text=_("新 Spider Master 机器（非空时本次恢复 master，第 1 台作为主中控）"),
        )
        spider_master_old_ip_list = serializers.ListSerializer(
            child=HostInfoSerializer(),
            required=False,
            default=list,
            help_text=_("待下线旧 Master，master_new 非空时必填，须与元数据 SPIDER_MASTER 严格一致"),
        )

        # ── slave 段 IP 列表（非空时本次恢复 spider_slave）──────────
        spider_slave_new_ip_list = serializers.ListSerializer(
            child=HostInfoSerializer(),
            required=False,
            default=list,
            help_text=_("新 Spider Slave 机器（非空时本次恢复 slave；要求中控 RUNNING 且 DRS 探活通过）"),
        )
        spider_slave_old_ip_list = serializers.ListSerializer(
            child=HostInfoSerializer(),
            required=False,
            default=list,
            help_text=_("待下线旧 Slave，slave_new 非空时必填，须与元数据 SPIDER_SLAVE 严格一致"),
        )

        privilege_recovery_mode = serializers.ChoiceField(
            choices=(
                ("from_spider_grant_backup", _("从 Spider/tdbctl grant 备份恢复")),
                ("account_rules_only", _("仅依赖 DBM 授权规则与内置账号")),
            ),
            required=False,
            default="from_spider_grant_backup",
            help_text=_("权限恢复策略，默认 from_spider_grant_backup"),
        )
        spider_priv_backup_id = serializers.CharField(required=False, allow_blank=True, help_text=_("指定备份 backup_id"))
        strip_dns_before_install = serializers.BooleanField(
            required=False, default=True, help_text=_("安装前对应域名（主/从）摘除旧 IP")
        )
        skip_schema_sync = serializers.BooleanField(
            required=False, default=False, help_text=_("跳过表结构同步（仅 master 段生效）")
        )
        spider_port = serializers.IntegerField(required=False, allow_null=True, help_text=_("Spider 端口覆盖"))
        ctl_port = serializers.IntegerField(required=False, allow_null=True, help_text=_("tdbctl 端口覆盖（仅 master 段生效）"))

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    infos = serializers.ListSerializer(child=InfoSerializer(), help_text=_("集群维度参数"))


class SpiderLayerDisasterRecoverFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendbcluster_spider_layer_disaster_recover_scene


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_LAYER_DR, is_recycle=True, is_apply=True)
class SpiderLayerDisasterRecoverFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderLayerDisasterRecoverDetailSerializer
    inner_flow_builder = SpiderLayerDisasterRecoverFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 接入层全毁灾难恢复")
    validator = SpiderController.tendbcluster_spider_layer_disaster_recover_scene.validator
