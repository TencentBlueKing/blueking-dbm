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

from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TenDBLocalUpgradeSerializer(TendbBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        class VersionModelSerializer(serializers.Serializer):
            db_version = serializers.CharField(help_text=_("DB版本"), required=False)
            pkg_name = serializers.CharField(help_text=_("包名称"), required=False)
            charset = serializers.CharField(help_text=_("字符集"), required=False)
            db_module_name = serializers.CharField(help_text=_("DB模块名称"), required=False)

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        pkg_id = serializers.IntegerField(help_text=_("目标版本包ID"))
        new_db_module_id = serializers.IntegerField(help_text=_("数据库模块ID"), required=False)
        current_version = VersionModelSerializer(help_text=_("当前版本信息"), required=False)
        target_version = VersionModelSerializer(help_text=_("目标版本信息"), required=False)

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True)
    upgrade_local = serializers.BooleanField(help_text=_("是否本地升级"), default=True)


class TenDBLocalUpgradeParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendbcluster_spider_upgrade


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_LOCAL_UPGRADE)
class TenDBLocalUpgradeFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TenDBLocalUpgradeSerializer
    inner_flow_builder = TenDBLocalUpgradeParamBuilder
    inner_flow_name = _("TenDB Cluster 接入层本地升级")
