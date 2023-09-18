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

from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.report import mock_data
from backend.db_services.report.serializers import ReportResponseSerializer

SWAGGER_TAG = _("巡检报告")


class InspectionReportView(viewsets.SystemViewSet):
    """巡检报告视图"""

    @common_swagger_auto_schema(
        operation_summary=_("查询巡检报告"),
        responses={status.HTTP_200_OK: ReportResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ReportResponseSerializer)
    def get_report(self, requests, *args, **kwargs):
        # TODO: 暂时使用假数据mock
        return Response(mock_data.REPORT_DATA)
