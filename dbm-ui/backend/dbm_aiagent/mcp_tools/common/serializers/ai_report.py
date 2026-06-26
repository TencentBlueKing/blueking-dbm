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

from backend.db_report.models.ai_analysis_report import ResultFormat


class WriteAiReportInputSerializer(serializers.Serializer):
    ai_agent = serializers.CharField(help_text=_("AI Agent 类型标识，用于区分不同的分析类型"))
    format = serializers.ChoiceField(
        choices=ResultFormat.get_choices(), default=ResultFormat.MARKDOWN, help_text=_("结果格式：markdown 或 html")
    )
    bk_biz_id = serializers.IntegerField(default=0, help_text=_("业务 ID，0 表示不关联业务"))
    cluster_domain = serializers.CharField(default="", allow_blank=True, required=False, help_text=_("集群域名，为空表示不关联集群"))
    title = serializers.CharField(help_text=_("报告标题"))
    summary = serializers.CharField(default="", allow_blank=True, required=False, help_text=_("报告摘要"))
    content = serializers.CharField(help_text=_("分析结果内容, 可以是完整报告内容，使用 dbm-mcp-cli 时也可以是 @file_path 这样的文件路径"))


class WriteAiReportOutputSerializer(serializers.Serializer):
    report_id = serializers.CharField(help_text=_("报告 ID（UUIDv7）"))
    message = serializers.CharField(help_text=_("操作结果信息"))


class ReadAiReportInputSerializer(serializers.Serializer):
    report_id = serializers.CharField(required=True, help_text=_("报告 ID，必填"))
    bk_biz_id = serializers.IntegerField(required=True, help_text=_("业务 ID，必填"))
    cluster_domain = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("集群域名，可选"))


class AiReportDetailSerializer(serializers.Serializer):
    id = serializers.CharField(help_text=_("报告 ID"))
    ai_agent = serializers.CharField(help_text=_("AI Agent 类型标识"))
    format = serializers.CharField(help_text=_("结果格式"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    title = serializers.CharField(help_text=_("报告标题"))
    summary = serializers.CharField(help_text=_("报告摘要"))
    content = serializers.CharField(help_text=_("分析结果内容"))
    context = serializers.JSONField(help_text=_("附加上下文信息"))
    creator = serializers.CharField(help_text=_("创建者"))
    create_at = serializers.DateTimeField(help_text=_("创建时间"))
    update_at = serializers.DateTimeField(help_text=_("更新时间"))


class ReadAiReportOutputSerializer(serializers.Serializer):
    report = AiReportDetailSerializer(help_text=_("报告详情"))
