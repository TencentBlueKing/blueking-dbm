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
from backend.flow.engine.controller.surrealdb import SurrealdbHaController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import TicketBaseValidateSerializerMixin
from backend.ticket.builders.surrealdb.base import BaseSurrealDBTicketFlowBuilder
from backend.ticket.builders.surrealdb.enums import SurrealDBOperationType
from backend.ticket.constants import TicketType


class K8sSurrealDBApplyDetailSerializer(TicketBaseValidateSerializerMixin, serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    creator = serializers.CharField(help_text=_("申请人"))
    remark = serializers.CharField(help_text=_("备注"), required=False, allow_blank=True, default="")
    db_app_abbr = serializers.CharField(help_text=_("应用缩写"))
    bk_biz_name = serializers.CharField(help_text=_("业务名称"))
    bk_cloud_region = serializers.CharField(
        help_text=_("云区域"), required=False, allow_blank=True, allow_null=True, default=""
    )
    k8s_cluster_name = serializers.CharField(help_text=_("K8s 集群名称"))
    major_version = serializers.CharField(help_text=_("主版本号"))
    db_version = serializers.CharField(help_text=_("数据库版本"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_name = serializers.CharField(help_text=_("集群名称"))
    cluster_alias = serializers.CharField(help_text=_("集群别名"))
    component_list = serializers.ListField(
        child=serializers.DictField(), help_text=_("组件列表"), required=False, default=list
    )
    # 部署模式：True(默认)表示共享集群，False表示独占集群
    is_public = serializers.BooleanField(help_text=_("是否共享集群(True:共享集群, False:独占集群)"), default=True)
    # 业务ID，独占集群下用于获取该业务独占的BCS集群资源
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # 独占集群必须绑定业务ID，未显式传入时默认取当前提单的业务ID
        if attrs.get("bk_biz_id") is None:
            attrs["bk_biz_id"] = int(self.context.get("bk_biz_id") or 0)
        if not attrs["is_public"] and not attrs["bk_biz_id"]:
            raise serializers.ValidationError(_("独占集群部署必须提供业务ID"))
        return attrs


class K8sSurrealDBApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = SurrealdbHaController.surrealdb_apply_scene


@builders.BuilderFactory.register(
    TicketType.K8S_SURREALDB_HA_APPLY,
    is_apply=True,
    cluster_type=ClusterType.K8sSurrealdbHa,
    iam=ActionEnum.K8S_SURREALDB_APPLY,
)
class K8sSurrealDBApplyFlowBuilder(BaseSurrealDBTicketFlowBuilder):
    serializer = K8sSurrealDBApplyDetailSerializer
    inner_flow_builder = K8sSurrealDBApplyFlowParamBuilder
    inner_flow_name = _("Surrealdb部署执行")
    enable_operation_log = False

    def patch_ticket_detail(self):
        super().patch_ticket_detail()
        self.add_apply_operation_log(self.ticket, SurrealDBOperationType.CreateCluster)
