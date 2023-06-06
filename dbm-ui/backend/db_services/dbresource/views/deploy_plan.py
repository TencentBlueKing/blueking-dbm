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

from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.models import Cluster
from backend.db_meta.models.spec import ClusterDeployPlan
from backend.db_services.dbresource.constants import SWAGGER_TAG
from backend.db_services.dbresource.exceptions import DeployPlanOperateException
from backend.db_services.dbresource.filters import ClusterDeployPlanFilter
from backend.db_services.dbresource.serializers import ClusterDeployPlanSerializer, DeleteDeployPlanSerializer
from backend.iam_app.handlers.drf_perm import GlobalManageIAMPermission


class DeployPlanViewSet(viewsets.AuditedModelViewSet):

    pagination_class = AuditedLimitOffsetPagination
    view_name = ""

    def _get_custom_permissions(self):
        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("新建{}部署方案").format(view_name),
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("更新{}部署方案").format(view_name),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        deploy_plan_id = int(kwargs["pk"])
        if Cluster.is_refer_deploy_plan([deploy_plan_id]):
            raise DeployPlanOperateException(_("部署方案: {} 正在被引用，无法修改相关参数").format(deploy_plan_id))
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("查询{}部署方案列表").format(view_name),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("删除{}部署方案").format(view_name),
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        deploy_plan_id = int(kwargs["pk"])
        if Cluster.is_refer_deploy_plan([deploy_plan_id]):
            raise DeployPlanOperateException(_("部署方案: {} 正在被引用，无法删除").format(deploy_plan_id))
        super().destroy(request, *args, **kwargs)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("批量删除{}部署方案").format(view_name),
        request_body=DeleteDeployPlanSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteDeployPlanSerializer)
    def batch_delete(self, request, *args, **kwargs):
        plan_ids = self.params_validate(self.get_serializer_class())["deploy_plan_ids"]
        if Cluster.is_refer_deploy_plan(plan_ids):
            raise DeployPlanOperateException(_("部署方案: {} 存在被引用，无法删除").format(plan_ids))
        return Response(self.deploy_plan_model.objects.filter(id__in=plan_ids).delete())


class ClusterDeployPlanViewSet(DeployPlanViewSet):

    queryset = ClusterDeployPlan.objects.all()
    serializer_class = ClusterDeployPlanSerializer
    deploy_plan_model = ClusterDeployPlan
    filter_class = ClusterDeployPlanFilter
