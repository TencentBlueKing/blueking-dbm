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

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.k8s_vm import K8sVmController
from backend.flow.utils.k8s_db.vm.consts import COMPONENT_VMSTORAGE
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import TicketBaseValidateSerializerMixin
from backend.ticket.builders.victoriametrics.base import BaseK8sVmTicketFlowBuilder
from backend.ticket.builders.victoriametrics.enums import VictoriaMetricsOperationType
from backend.ticket.constants import TicketType


class K8sVictoriaMetricsApplyDetailSerializer(TicketBaseValidateSerializerMixin, serializers.Serializer):
    created_by = serializers.CharField(help_text=_("申请人"), required=False)
    creator = serializers.CharField(help_text=_("申请人"), required=False)
    remark = serializers.CharField(help_text=_("备注"), required=False, allow_blank=True, default="")
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    bk_biz_name = serializers.CharField(help_text=_("业务名称"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    bk_cloud_region = serializers.CharField(help_text=_("云区域名称"), allow_blank=True)
    city_code = serializers.CharField(help_text=_("城市编码"))
    k8s_cluster_name = serializers.CharField(help_text=_("K8s集群名称"))
    major_version = serializers.CharField(help_text=_("主版本号"))
    db_version = serializers.CharField(help_text=_("DB版本号"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_name = serializers.CharField(help_text=_("集群名称"))
    cluster_alias = serializers.CharField(help_text=_("集群别名"))
    component_list = serializers.ListField(help_text=_("组件列表"))

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get("cluster_type") not in [
            ClusterType.K8sVictoriametricsStandard.value,
            ClusterType.K8sVictoriametricsQuery.value,
        ]:
            raise serializers.ValidationError(_("VictoriaMetrics 标准集群类型不正确"))

        for item in attrs["component_list"]:
            replicas = item.get("replicas")
            if not isinstance(replicas, int):
                raise serializers.ValidationError(_("replicas 必须是整数"))
            if not 2 <= replicas <= 100:
                raise serializers.ValidationError(_("replicas 最小为2，最大为100"))
            if item["component_name"] == COMPONENT_VMSTORAGE and not item.get("storage"):
                raise serializers.ValidationError(_("vmstorage 组件必须配置持久化存储"))
            if item["component_name"] != COMPONENT_VMSTORAGE and item.get("storage"):
                raise serializers.ValidationError(_("vminsert 和 vmselect 组件不能配置持久化存储"))
        return attrs


class K8sVictoriaMetricsApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = K8sVmController.vm_apply_scene


class BaseK8sVictoriaMetricsApplyFlowBuilder(BaseK8sVmTicketFlowBuilder):
    serializer = K8sVictoriaMetricsApplyDetailSerializer
    inner_flow_builder = K8sVictoriaMetricsApplyFlowParamBuilder
    enable_operation_log = False

    def patch_ticket_detail(self):
        super().patch_ticket_detail()
        self.add_apply_operation_log(self.ticket, VictoriaMetricsOperationType.CreateCluster)


@builders.BuilderFactory.register(
    TicketType.K8S_VICTORIAMETRICS_STANDARD_APPLY,
    is_apply=True,
    cluster_type=ClusterType.K8sVictoriametricsStandard,
    iam=ActionEnum.K8S_VICTORIAMETRICS_APPLY,
)
class K8sVictoriaMetricsStandardApplyFlowBuilder(BaseK8sVictoriaMetricsApplyFlowBuilder):
    inner_flow_name = _("VictoriaMetrics 标准集群部署执行")
