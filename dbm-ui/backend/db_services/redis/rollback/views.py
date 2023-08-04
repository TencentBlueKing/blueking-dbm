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
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django_filters import rest_framework as filters

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import ReadOnlyAuditedModelViewSet

from . import constants
from .models import TbTendisRollbackTasks
from .serializers import RollbackSerializer


class RollbackListFilter(filters.FilterSet):
    prod_cluster = filters.CharFilter(field_name="prod_cluster", lookup_expr="icontains", label=_("集群域名"))
    related_rollback_bill_id = filters.CharFilter(
        field_name="related_rollback_bill_id", lookup_expr="exact", label=_("单据id")
    )

    class Meta:
        model = TbTendisRollbackTasks
        fields = ["prod_cluster_id", "prod_cluster", "related_rollback_bill_id", "temp_cluster_proxy"]


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(tags=[constants.RESOURCE_TAG]),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(tags=[constants.RESOURCE_TAG]),
)
class RollbackViewSet(ReadOnlyAuditedModelViewSet):
    """实例构造管理"""

    queryset = TbTendisRollbackTasks.objects.order_by("-create_at")
    serializer_class = RollbackSerializer
    filter_class = RollbackListFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        bk_biz_id = self.kwargs.get("bk_biz_id")
        if self.action == "list" and bk_biz_id:
            queryset = queryset.filter(bk_biz_id=bk_biz_id)

        return queryset
