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
from bkstorages.backends.bkrepo import BKRepoStorage
from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import PaginatedResponseSwaggerAutoSchema, common_swagger_auto_schema
from backend.db_services.risk_memo.constants import BKREPO_RISK_MEMO_PATH, RiskOpType, Status
from backend.db_services.risk_memo.filters import RiskMemoListFilter, RiskOpRecordListFilter
from backend.db_services.risk_memo.handler import log_operation
from backend.db_services.risk_memo.models.risk_memo import RiskMemo, RiskOperateRecord
from backend.db_services.risk_memo.serializers import (
    RiskMemoDtailSerializer,
    RiskMemoSerializer,
    RiskOpSerializer,
    UpdateRiskStatusSerializer,
    UploadImageSerializer,
)
from backend.iam_app.dataclass import ActionEnum, ResourceEnum
from backend.iam_app.handlers.drf_perm.risk_memo import ListRiskMemoPermission, RiskMemoPermission
from backend.iam_app.handlers.permission import Permission
from backend.utils.string import make_unique_key

RISK_MEMO_VIEW_TAGS = ["risk_memo"]


class RiskMemoViewSet(viewsets.AuditedModelViewSet):
    """
    风险备忘录跟进视图
    """

    action_permission_map = {
        ("list",): [ListRiskMemoPermission()],
        ("update", "create", "retrieve", "update_risk_status"): [RiskMemoPermission()],
        ("get_risk_operate_records", "images"): [],
    }

    queryset = RiskMemo.objects.all()
    pagination_class = AuditedLimitOffsetPagination
    serializer_class = RiskMemoSerializer
    filter_class = RiskMemoListFilter

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RiskMemoDtailSerializer
        elif self.action == "update_risk_status":
            return UpdateRiskStatusSerializer
        return RiskMemoSerializer

    @common_swagger_auto_schema(
        operation_summary=_("风险列表"),
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        tags=RISK_MEMO_VIEW_TAGS,
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["bk_biz_id"],
        actions=[ActionEnum.RISK_MEMO_CREATE, ActionEnum.RISK_MEMO_MANAGE],
        resource_meta=ResourceEnum.BUSINESS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("新建风险"),
        responses={status.HTTP_200_OK: RiskMemoSerializer(label=_("新建风险"))},
        tags=RISK_MEMO_VIEW_TAGS,
    )
    @log_operation(oper_type=RiskOpType.CREATE_RISK.value)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("风险详情"),
        responses={status.HTTP_200_OK: RiskMemoSerializer(label=_("风险详情"))},
        tags=RISK_MEMO_VIEW_TAGS,
    )
    def retrieve(self, request, *args, **kwargs):
        """风险详情"""
        return super().retrieve(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("更新风险"),
        responses={status.HTTP_200_OK: RiskMemoSerializer(label=_("更新风险"))},
        tags=RISK_MEMO_VIEW_TAGS,
    )
    @log_operation(oper_type=RiskOpType.UPDATE_RISK.value)
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("更新风险状态"),
        request_body=UpdateRiskStatusSerializer(),
        tags=RISK_MEMO_VIEW_TAGS,
    )
    @action(detail=True, methods=["POST"], serializer_class=UpdateRiskStatusSerializer)
    def update_risk_status(self, request, *args, **kwargs):
        """更新风险状态"""
        validated_data = self.params_validate(self.get_serializer_class())
        risk = self.get_object()

        # 更新对象
        try:
            RiskMemo.objects.handler_risk_status(request=request, validated_data=validated_data, risk=risk)
        except Exception as e:
            return JsonResponse({"msg": "{}".format(e), "code": 1, "data": ""})

        # 状态与操作类型映射
        status_optrate_map = {
            Status.DONE.value: RiskOpType.FINAL.value,
            Status.DOING.value: RiskOpType.RESTART_RISK.value,
        }

        # 创建risk操作记录
        RiskOperateRecord.objects.create(
            creator=request.user.username, oper_type=status_optrate_map[validated_data["status"]], risk=risk
        )

        serializer = RiskMemoSerializer(instance=risk)
        return Response(serializer.data)

    @common_swagger_auto_schema(
        operation_summary=_("获取风险记录日志"),
        tags=[RISK_MEMO_VIEW_TAGS],
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=RiskOpSerializer,
        queryset=RiskOperateRecord.objects.select_related("risk").order_by("-create_at"),
        filter_class=RiskOpRecordListFilter,
    )
    def get_risk_operate_records(self, request, *args, **kwargs):
        op_records_page_qs = self.paginate_queryset(super().filter_queryset(self.queryset))
        op_records_page_data = self.serializer_class(op_records_page_qs, many=True).data
        return self.get_paginated_response(data=op_records_page_data)

    @common_swagger_auto_schema(
        operation_summary=_("上传图片到制品库"),
        tags=[RISK_MEMO_VIEW_TAGS],
        request_body=UploadImageSerializer(),
    )
    @action(detail=False, methods=["POST"], serializer_class=UploadImageSerializer)
    def images(self, request):
        """上传图片"""
        file_obj = request.data.get("file", None)
        bk_biz_id = request.data.get("bk_biz_id", 0)
        try:
            # 生成文件名
            file_name = make_unique_key(file_obj)
            storage = BKRepoStorage()
            storage.save(name=BKREPO_RISK_MEMO_PATH.format(biz=bk_biz_id, file=file_name), content=file_obj)
        except Exception as e:
            return JsonResponse({"msg": "{}".format(e), "code": 1, "data": ""})

        return Response({"url": storage.url(file_name)})
