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
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbSchemaRepairDetailSerializer(TendbBaseOperateDetailSerializer):
    """TenDB Cluster 表结构修复单据详情"""

    cluster_ids = serializers.ListField(
        help_text=_("集群ID列表"),
        child=serializers.IntegerField(),
        allow_empty=False,
    )
    auto_fix = serializers.BooleanField(help_text=_("是否自动修复（读取校验结果自动修复不一致项）"), default=False)
    db = serializers.CharField(
        help_text=_("待修复的数据库名，auto_fix 为 False 时必填"),
        required=False,
        default="",
        allow_blank=True,
    )
    tables = serializers.ListField(
        help_text=_("待修复的表名列表，为空表示修复整库"),
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    dry_run = serializers.BooleanField(help_text=_("是否试运行（只生成修复SQL文件，不实际执行）"), default=False)

    def validate(self, attrs):
        attrs = super(TendbBaseOperateDetailSerializer, self).validate(attrs)
        super().validated_cluster_type(attrs, cluster_type=ClusterType.TenDBCluster)

        if not attrs["auto_fix"] and not attrs.get("db"):
            raise serializers.ValidationError(_("auto_fix 为 False 时，db 不能为空"))

        cluster_ids = fetch_cluster_ids(attrs)
        if not cluster_ids:
            raise serializers.ValidationError(_("cluster_ids 不能为空"))
        if not Cluster.objects.filter(id__in=cluster_ids).exists():
            raise serializers.ValidationError(_("集群不存在"))

        return attrs


class TendbSchemaRepairFlowParamBuilder(builders.FlowParamBuilder):
    """TenDB Cluster 表结构修复流程参数构建"""

    controller = SpiderController.spider_schema_repair_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SCHEMA_REPAIR)
class TendbSchemaRepairFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbSchemaRepairDetailSerializer
    inner_flow_builder = TendbSchemaRepairFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 表结构修复")
