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


import logging

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_report.enums import SWAGGER_TAG
from backend.db_report.models import ChecksumInstance
from backend.db_report.report_baseview import ReportBaseViewSet

logger = logging.getLogger("root")


class ChecksumInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecksumInstance
        fields = ("ip", "port", "master_ip", "master_port", "details", "id")


class ChecksumInstanceViewSet(ReportBaseViewSet):
    queryset = ChecksumInstance.objects.all()
    serializer_class = ChecksumInstanceSerializer
    filter_fields = {
        "report_id": ["exact"],
    }
    report_name = _("失败的从库实例详情")
    report_title = []

    @common_swagger_auto_schema(
        operation_summary=_("失败的从库实例详情"),
        responses={status.HTTP_200_OK: ChecksumInstanceSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
