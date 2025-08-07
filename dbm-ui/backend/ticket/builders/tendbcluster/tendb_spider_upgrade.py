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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import (
    BaseTendbTicketFlowBuilder,
    TendbBaseOperateDetailSerializer,
    TendbBaseOperateResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class TenDBSpiderUpgradeSerializer(TendbBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        class VersionModelSerializer(serializers.Serializer):
            db_version = serializers.CharField(help_text=_("DB版本"), required=False)
            pkg_name = serializers.CharField(help_text=_("包名称"), required=False)
            charset = serializers.CharField(help_text=_("字符集"), required=False)
            db_module_name = serializers.CharField(help_text=_("DB模块名称"), required=False)

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        pkg_id = serializers.IntegerField(help_text=_("目标版本包ID"))
        new_db_module_id = serializers.IntegerField(help_text=_("数据库模块ID"), required=False)
        resource_spec = serializers.JSONField(help_text=_("资源规格参数"), required=False)
        old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"))
        current_version = VersionModelSerializer(help_text=_("当前版本信息"), required=False)
        target_version = VersionModelSerializer(help_text=_("目标版本信息"), required=False)

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True)
    upgrade_local = serializers.BooleanField(help_text=_("是否本地升级"), default=False)
    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )


class TenDBSpiderUpgradeParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendbcluster_spider_upgrade


class TenDBSpiderUpgradeResourceParamBuilder(TendbBaseOperateResourceParamBuilder):
    def format(self):
        # 在跨机房亲和性要求下，接入层spider的亲和性要求至少分布在2个机房
        self.patch_info_affinity_location()
        for info in self.ticket_data["infos"]:
            for k, v in info["old_nodes"].items():
                for node in v:
                    role = f'{k}_{node["ip"]}'
                    info["resource_spec"][role]["group_count"] = 2

    def get_new_host_info(self, info, spider_role):
        new_host_info = []
        for host in info["old_nodes"][spider_role]:
            role = f'{spider_role}_{host["ip"]}'
            new_host_info.extend(info.pop(role))
        return new_host_info

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            # 格式化规格信息
            info["spider_master_ip_list"] = self.get_new_host_info(info, "spider_master")
            info["spider_slave_ip_list"] = self.get_new_host_info(info, "spider_slave")

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_UPGRADE, is_apply=True, is_recycle=True)
class TenDBSpiderUpgradeFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TenDBSpiderUpgradeSerializer
    inner_flow_builder = TenDBSpiderUpgradeParamBuilder
    inner_flow_name = _("TenDB Cluster 接入层迁移升级")
    resource_batch_apply_builder = TenDBSpiderUpgradeResourceParamBuilder
    need_patch_recycle_host_details = True
