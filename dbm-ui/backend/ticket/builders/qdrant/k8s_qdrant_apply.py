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

import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.qdrant_temp import QdrantController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import TicketBaseValidateSerializerMixin
from backend.ticket.builders.qdrant.base import BaseQdrantTicketFlowBuilder
from backend.ticket.constants import TicketType


class K8sQdrantApplyDetailSerializer(TicketBaseValidateSerializerMixin, serializers.Serializer):
    class ComponentInfo(serializers.Serializer):
        component_name = serializers.CharField(help_text=_("组件名称"))
        replicas = serializers.IntegerField(help_text=_("副本数"))
        request_cpu = serializers.CharField(help_text=_("请求CPU，格式如：100m、0.5、1、2"))
        request_memory = serializers.CharField(help_text=_("请求内存，格式如：100Mi、256Mi、512Mi、1Gi、2Gi"))
        storage = serializers.CharField(help_text=_("存储，格式如：10Gi、20Gi、50Gi、100Gi"))

        def validate(self, attrs):
            attrs = super().validate(attrs)
            # K8s 资源格式正则
            # CPU: 带m后缀的毫核（如100m）或不带单位的核数（整数或小数，如0.5、1、1.5、2）
            cpu_pattern = r"^(\d+m|\d*\.\d+|\d+)$"
            # 内存/存储：以 Ki、Mi、Gi、Ti、Pi、Ei 结尾（如 100Mi、1Gi、1.5Gi）
            memory_pattern = r"^\d+(\.\d+)?[KMGTPE]i$"

            # 字段名 -> (正则, 错误提示)
            field_validators = {
                "request_cpu": (
                    cpu_pattern,
                    _("CPU格式错误，请使用Kubernetes标准格式：带m后缀表示毫核（如100m），不带单位表示核数（如0.5、1、1.5、2）"),
                ),
                "request_memory": (
                    memory_pattern,
                    _("内存格式错误，请使用Kubernetes标准格式：以Ki、Mi、Gi等结尾（如100Mi、256Mi、512Mi、1Gi、2Gi）"),
                ),
                "storage": (
                    memory_pattern,
                    _("存储格式错误，请使用Kubernetes标准格式：以Ki、Mi、Gi等结尾（如10Gi、20Gi、50Gi、100Gi）"),
                ),
            }

            errors = {}
            for field, (pattern, error_message) in field_validators.items():
                if not re.match(pattern, attrs[field]):
                    errors[field] = [error_message]
            if errors:
                raise serializers.ValidationError(errors)

            return attrs

    creator = serializers.CharField(help_text=_("申请人"))
    remark = serializers.CharField(help_text=_("备注"), required=False, allow_blank=True, default="")
    db_app_abbr = serializers.CharField(help_text=_("应用名称"))
    bk_biz_name = serializers.CharField(help_text=_("业务名称"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    bk_cloud_region = serializers.CharField(help_text=_("云区域名称"), allow_blank=True)
    city_code = serializers.CharField(help_text=_("城市编码"))
    k8s_cluster_name = serializers.CharField(help_text=_("集群名称"))
    major_version = serializers.CharField(help_text=_("主版本号"))
    db_version = serializers.CharField(help_text=_("版本号"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_name = serializers.CharField(help_text=_("集群名称"))
    cluster_alias = serializers.CharField(help_text=_("集群别名"))
    component_list = serializers.ListField(help_text=_("组件列表"), child=ComponentInfo())


class K8sQdrantApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = QdrantController.placeholder


@builders.BuilderFactory.register(
    TicketType.K8S_QDRANT_HA_APPLY,
    is_apply=True,
    cluster_type=ClusterType.K8sQdrantHa,
    iam=ActionEnum.K8S_QDRANT_APPLY,
)
class K8sQdrantApplyFlowBuilder(BaseQdrantTicketFlowBuilder):
    serializer = K8sQdrantApplyDetailSerializer
    inner_flow_builder = K8sQdrantApplyFlowParamBuilder
    inner_flow_name = _("Qdrant部署执行")
