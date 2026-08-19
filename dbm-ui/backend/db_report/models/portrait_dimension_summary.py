# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 - 维度摘要报告表 Model。

模块职责：
    - 承接各巡检维度上报的「一次巡检摘要」，作为集群画像 Agent 分析的唯一数据源
    - 一条记录 = 某集群在某维度上的一次巡检产出（摘要文本 + 详情页链接）
    - 巡检方每完成一次巡检 → 追加写一条；Agent 分析时按 (集群, 维度) 读取时间窗内**全部**匹配记录
      （不做「每维度取最新」的聚合，Agent 可看到多次巡检的时间序列）

设计要点：
    - 精确到秒（report_time），允许一天多次上报；但推荐一天一次，避免 LLM 上下文冗余
    - summary 为单条摘要文本；由巡检方自己组织语言，Agent/LLM 直接引用
    - detail_url 为本次巡检对应的详情页链接，前端在画像报告卡片上提供"查看详情"跳转
    - 严格通过 (db_type, code) 与注册表对齐；未注册的维度即便有数据 Agent 也不会拉取

边界：
    - summary 允许为空字符串，视为「本次巡检无风险要点」
    - Agent 侧读取语义为「时间窗内每维度返回全部匹配记录」，由 MCP 工具实现，本表只做纯追加存储
    - 若未来需要「每维度取最新一条」的聚合视图，应在 MCP 工具层新增方法，而非改动本表写入语义

TODO（数据老化 / TTL）：
    - 本表当前为纯追加写入，无自动清理；上线跑通后需评估保留窗口与清理策略
    - 参考实现：bamboo-engine 的定时清理（django management command + celery beat 周期触发，删除 N 天前数据）
    - 待评估项：保留窗口（默认 30d / 90d）、是否按 db_type 差异化、是否需要归档冷存储
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType


class PortraitDimensionSummary(models.Model):
    """集群画像 - 维度巡检摘要表。

    职责：
        - 存储各巡检维度对某集群的「单次巡检摘要 + 详情链接」
        - 每行 = 巡检方一次上报动作

    典型使用：
        - 巡检开发者：巡检产出后通过 db_report.portrait.sdk.ingest_summary(...) 追加一条
        - 集群画像 Agent：调 MCP portrait_fetch_summaries，读取时间窗内全部匹配记录参与分析
          （同一维度多次上报会得到多条，可按时间线观察变化趋势）

    边界：
        - report_time 精确到秒；上报频率由巡检方自控，本表不做去重
        - summary 为空字符串代表「无风险要点」，仍会被 Agent 视为有效数据
    """

    #: 业务 ID；用于按业务隔离查询
    bk_biz_id = models.IntegerField(
        verbose_name=_("业务ID"),
        help_text=_("CMDB 业务 ID"),
    )

    #: 集群不可变域名；集群画像的核心检索键
    cluster_domain = models.CharField(
        max_length=255,
        verbose_name=_("集群域名"),
        help_text=_("集群不可变主域名，作为画像检索维度"),
    )

    #: 数据库类型；与注册表 db_type 保持一致
    db_type = models.CharField(
        max_length=32,
        choices=DBType.get_choices(),
        verbose_name=_("数据库类型"),
        help_text=_("集群所属 DB 类型，与 tb_portrait_dimension_registry.db_type 对齐"),
    )

    #: 维度编码；与注册表 code 保持一致，Agent 通过它找到维度语义
    code = models.CharField(
        max_length=64,
        verbose_name=_("维度编码"),
        help_text=_("维度稳定标识，与 tb_portrait_dimension_registry.code 对齐"),
    )

    #: 本次巡检的产生时间；精确到秒；由巡检方决定填写「本次巡检的业务时间」
    report_time = models.DateTimeField(
        verbose_name=_("巡检时间"),
        help_text=_("本次巡检产出的业务时间，精确到秒；Agent 按 time_range 过滤"),
    )

    #: 本次巡检的摘要文本；由巡检方直接组织好语义，LLM 会原样引用
    summary = models.TextField(
        default="",
        blank=True,
        verbose_name=_("巡检摘要"),
        help_text=_("单次巡检的摘要文本；示例：'近 24h 慢日志同比上涨 32%，top1 SQL 未走索引'"),
    )

    #: 本次巡检对应的详情页 URL；报告中该维度卡片的「查看详情」跳转链接
    detail_url = models.CharField(
        max_length=1024,
        default="",
        blank=True,
        verbose_name=_("详情页URL"),
        help_text=_("本次巡检产出的详情页完整链接，前端画像报告在该维度卡片提供跳转"),
    )

    #: 本次摘要结果的分数；为空表示未上报分数
    score = models.FloatField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("分数"),
        help_text=_("本次巡检摘要结果的分数，为空表示未上报"),
    )

    create_at = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))

    class Meta:
        managed = True
        app_label = "db_report"
        db_table = "tb_portrait_dimension_summary"
        verbose_name = _("集群画像-维度巡检摘要")
        verbose_name_plural = _("集群画像-维度巡检摘要")
        indexes = [
            # 主查询路径：Agent 按 (集群 + 维度 + 时间倒序) 拉取时间窗内的历史记录
            models.Index(
                fields=["cluster_domain", "code", "-report_time"],
                name="idx_pt_sum_cluster_code_t",
            ),
            # 业务维度聚合：便于按业务批量拉全部维度
            models.Index(
                fields=["bk_biz_id", "db_type", "-report_time"],
                name="idx_pt_sum_biz_dbtype_t",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.db_type}:{self.code}@{self.cluster_domain}#{self.report_time:%Y-%m-%d %H:%M:%S}"
