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
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission


class ReportBaseViewSet(GenericViewSet, mixins.ListModelMixin):
    permission_classes = [DBManageIAMPermission]
    pagination_class = AuditedLimitOffsetPagination

    filter_fields = {
        "bk_biz_id": ["exact"],
        "cluster": ["exact", "in"],
        "cluster_type": ["exact", "in"],
        "create_at": ["gte", "lte"],
        "status": ["exact", "in"],
    }

    report_name = ""
    report_title = []

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["name"] = self.report_name
        response.data["title"] = self.report_title

        return response
