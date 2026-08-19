# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 - 维度注册表 Model。

模块职责：
    - 登记各巡检维度（如慢日志、配置检查、集群倾斜等）的元信息，
      供集群画像 Agent 通过 MCP 工具 (portrait_list_dimensions) 动态发现可分析维度，
      Agent 本身零硬编码 —— 新增/禁用维度只需操作本表，Agent 无需改动。

设计要点：
    - 每一行 = 一个「db_type + 维度 code」的巡检项定义
    - 只保留 Agent 决策必需字段，业务扩展字段一律禁止（extra/owner/version 等已剔除）
    - 唯一键 (db_type, code) 保证同一 DB 类型下维度不重复
    - enabled 字段用于快速开关维度，仅影响读侧（Agent 分析时忽略禁用维度）

边界：
    - 记录由 SDK 首次上报时自动懒注册；契约来源 ``PortraitDimensionCode`` 枚举
    - 记录的启停由 django command (sync_portrait_dimensions enable/disable) 维护
    - 不直接暴露 CRUD 接口给前端
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_report.enums import SummaryFetchStrategy


class PortraitDimensionRegistry(models.Model):
    """集群画像维度注册表。

    职责：
        - 存储每个巡检维度的元信息（db_type / code / 名称 / 说明）
        - 作为 Agent 通过 MCP 发现维度的唯一权威来源

    典型使用：
        - 巡检开发者：通过 :class:`PortraitDimensionCode` 枚举定义契约；SDK 首次上报时自动注册
        - Agent：通过 MCP 读侧接口拉取 enabled 维度列表 → 决定分析哪些维度

    边界：
        - (db_type, code) 唯一
        - enabled=False 时 Agent 视为不存在，不会进入分析流程；但**不影响 SDK 写入**
    """

    #: 数据库类型；choices 引用 DBType 枚举，保证与平台其它模块一致
    db_type = models.CharField(
        max_length=32,
        choices=DBType.get_choices(),
        verbose_name=_("数据库类型"),
        help_text=_("巡检维度所属的数据库类型，如 mysql/redis/sqlserver 等"),
    )

    #: 维度短码；同一 db_type 下唯一，作为 Agent 与巡检开发者双方约定的稳定标识
    code = models.CharField(
        max_length=64,
        verbose_name=_("维度编码"),
        help_text=_("维度稳定标识，同一 db_type 下唯一，示例：slow_query / config_check / cluster_skew"),
    )

    #: 维度中文名（前端 / 报告展示用）
    name = models.CharField(
        max_length=128,
        verbose_name=_("维度名称"),
        help_text=_("维度中文名，用于前端展示和 LLM Prompt 中的自然语言引用"),
    )

    #: 维度描述；给 LLM 看的 —— 说明"这个维度检查什么、summary 里会讲什么"
    description = models.TextField(
        default="",
        blank=True,
        verbose_name=_("维度描述"),
        help_text=_("用于 LLM 理解本维度语义的说明，建议 100~300 字，描述检查内容与产出的 summary 语义"),
    )

    #: 是否启用；False 时 Agent discover 阶段直接跳过
    enabled = models.BooleanField(
        default=True,
        verbose_name=_("是否启用"),
        help_text=_("False 表示该维度暂不参与集群画像分析"),
    )

    #: 维度计算分数权重；为空表示未配置权重
    weight = models.FloatField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("权重"),
        help_text=_("该维度在画像综合评分中的计算权重，为空表示未配置"),
    )

    #: 获取摘要结果的策略；决定 portrait_fetch_summaries 时间范围内返回哪些结果
    summary_fetch_strategy = models.CharField(
        max_length=16,
        choices=SummaryFetchStrategy.get_choices(),
        default=SummaryFetchStrategy.ALL.value,
        verbose_name=_("摘要获取策略"),
        help_text=_("获取该维度摘要结果的策略：all 返回全部 / last 返回最新一条 / first 返回最老一条"),
    )

    create_at = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))
    update_at = models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))

    class Meta:
        managed = True
        app_label = "db_report"
        db_table = "tb_portrait_dimension_registry"
        verbose_name = _("集群画像-维度注册表")
        verbose_name_plural = _("集群画像-维度注册表")
        constraints = [
            models.UniqueConstraint(
                fields=["db_type", "code"],
                name="uniq_portrait_dim_dbtype_code",
            ),
        ]
        indexes = [
            models.Index(fields=["db_type", "enabled"], name="idx_portrait_dim_dbtype_enable"),
        ]

    def __str__(self) -> str:
        return f"{self.db_type}:{self.code}({'on' if self.enabled else 'off'})"
