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

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.flow.consts import PipelineStatus
from backend.flow.models import FlowTree
from backend.utils.time import calculate_cost_time

from . import mock_data


class ReportResponseSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("巡检表名"))
    title = serializers.ListField(help_text=_("表头"), child=serializers.CharField())
    data = serializers.JSONField(help_text=_("表数据"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.REPORT_DATA}
