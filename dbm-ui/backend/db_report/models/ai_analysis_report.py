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
import zlib

from django.db import models
from django.utils.translation import gettext_lazy as _
from uuid_utils import uuid7

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class ResultFormat(StrStructuredEnum):
    """AI 分析结果格式"""

    MARKDOWN = EnumField("markdown", _("Markdown"))
    HTML = EnumField("html", _("HTML"))


class AiAnalysisReport(models.Model):
    """通用 AI 分析结果报告存储表"""

    id = models.CharField(max_length=36, primary_key=True, default=uuid7, help_text=_("UUIDv7 主键"))
    ai_agent = models.CharField(max_length=128, help_text=_("AI Agent 类型标识，用于区分不同的分析类型"))
    format = models.CharField(
        max_length=16, choices=ResultFormat.get_choices(), default=ResultFormat.MARKDOWN, help_text=_("结果格式")
    )

    bk_biz_id = models.IntegerField(default=0, help_text=_("业务 ID，0 表示不关联业务"))
    cluster_domain = models.CharField(max_length=255, default="", help_text=_("集群域名，为空表示不关联集群"))

    title = models.CharField(max_length=512, default="", help_text=_("报告标题"))
    summary = models.TextField(default="", help_text=_("报告摘要"))
    content = models.BinaryField(help_text=_("分析结果内容（zlib 压缩存储）"))

    creator = models.CharField(max_length=64, default="", help_text=_("创建者"))
    create_at = models.DateTimeField(auto_now_add=True, help_text=_("创建时间"))
    update_at = models.DateTimeField(auto_now=True, help_text=_("更新时间"))

    class Meta:
        managed = True
        app_label = "db_report"
        db_table = "tb_ai_analysis_report"
        verbose_name = _("AI分析报告")
        verbose_name_plural = _("AI分析报告")
        indexes = [
            models.Index(fields=["ai_agent", "create_at"], name="idx_agent_create_at"),
            models.Index(fields=["bk_biz_id", "ai_agent"], name="idx_biz_agent"),
            models.Index(fields=["cluster_domain", "ai_agent"], name="idx_domain_agent"),
        ]

    def set_content(self, text: str):
        """压缩并设置 content 字段"""
        self.content = zlib.compress(text.encode("utf-8"))

    def get_content(self) -> str:
        """解压并返回 content 字段的文本内容"""
        if not self.content:
            return ""
        raw = self.content
        if isinstance(raw, memoryview):
            raw = bytes(raw)
        return zlib.decompress(raw).decode("utf-8")

    def __str__(self):
        return f"{self.ai_agent}-{self.title}-{self.id}"
