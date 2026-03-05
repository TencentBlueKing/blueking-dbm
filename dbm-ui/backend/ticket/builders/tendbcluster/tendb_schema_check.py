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


class CheckObjectSerializer(serializers.Serializer):
    """表结构校验对象"""

    dbname = serializers.CharField(help_text=_("数据库名"))
    tables = serializers.ListField(
        help_text=_("表名列表，为空表示校验整个库"),
        child=serializers.CharField(),
        required=False,
        default=list,
    )


class TendbSchemaCheckDetailSerializer(TendbBaseOperateDetailSerializer):
    """TenDB Cluster 表结构校验单据详情"""

    cluster_ids = serializers.ListField(
        help_text=_("集群ID列表"),
        child=serializers.IntegerField(),
        allow_empty=False,
    )
    check_all = serializers.BooleanField(help_text=_("是否校验所有非系统库表"), default=False)
    inconsistency_throws_err = serializers.BooleanField(help_text=_("发现不一致时是否抛出错误"), default=False)
    check_objects = serializers.ListField(
        help_text=_("指定校验对象列表，check_all为False时生效"),
        child=CheckObjectSerializer(),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        attrs = super(TendbBaseOperateDetailSerializer, self).validate(attrs)

        if not attrs["check_all"] and not attrs.get("check_objects"):
            raise serializers.ValidationError(_("check_all 为 False 时，check_objects 不能为空"))

        cluster_ids = fetch_cluster_ids(attrs)
        if Cluster.objects.filter(id__in=cluster_ids).count() != len(set(cluster_ids)):
            raise serializers.ValidationError(_("部分集群不存在"))

        super().validated_cluster_type(attrs, cluster_type=ClusterType.TenDBCluster)

        return attrs


class TendbSchemaCheckFlowParamBuilder(builders.FlowParamBuilder):
    """TenDB Cluster 表结构校验流程参数构建"""

    controller = SpiderController.spider_schema_check_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SCHEMA_CHECK)
class TendbSchemaCheckFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbSchemaCheckDetailSerializer
    inner_flow_builder = TendbSchemaCheckFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 表结构校验")
