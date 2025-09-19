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
from rest_framework import status

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.risk_memo.constants import RiskOpType
from backend.db_services.risk_memo.filters import RiskMemoFollowUpListFilter
from backend.db_services.risk_memo.handler import log_operation
from backend.db_services.risk_memo.models.risk_memo import RiskMemoFollowUp
from backend.db_services.risk_memo.serializers import RiskMemoFollowUpSerializer, UpdateRiskMemoFollowUpSerializer

RISK_MEMO_FOLLOWUP_VIEW_TAGS = ["risk_memo_follow_up"]


class RiskMemoFollowUpViewSet(viewsets.AuditedModelViewSet):
    """
    风险备忘录跟进视图
    """

    queryset = RiskMemoFollowUp.objects.all().prefetch_related("risk")
    pagination_class = AuditedLimitOffsetPagination
    serializer_class = RiskMemoFollowUpSerializer
    filter_class = RiskMemoFollowUpListFilter

    def get_serializer_class(self):
        if self.action == "update":
            return UpdateRiskMemoFollowUpSerializer
        return self.serializer_class

    def get_serializer_context(self):
        # 将request对象添加到序列化器上下文
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @common_swagger_auto_schema(
        operation_summary=_("新建风险跟进"),
        request_body=RiskMemoFollowUpSerializer(),
        responses={status.HTTP_200_OK: RiskMemoFollowUpSerializer(label=_("新建风险跟进"))},
        tags=RISK_MEMO_FOLLOWUP_VIEW_TAGS,
    )
    @log_operation(RiskOpType.CREATE_FOLLOW_UP.value)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("更新风险跟进"),
        request_body=UpdateRiskMemoFollowUpSerializer(),
        responses={status.HTTP_200_OK: RiskMemoFollowUpSerializer(label=_("更新风险跟进"))},
        tags=RISK_MEMO_FOLLOWUP_VIEW_TAGS,
    )
    @log_operation(RiskOpType.UPDATE_FOLLOW_UP.value)
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("删除风险跟进"),
        tags=RISK_MEMO_FOLLOWUP_VIEW_TAGS,
    )
    @log_operation(RiskOpType.REMOVE_FOLLOW_UP.value)
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
