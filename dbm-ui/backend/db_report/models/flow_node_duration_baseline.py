# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

流程节点耗时基线主表 model。

模块职责：
  - 存储 (ticket_type, bk_biz_id, component_code, normalized_name) 四维粒度下的节点耗时基线
  - 同时保存正态分布指标（mean/stddev）与分位数指标（p50/p90/p95/p99），供上层按分布形态选择性使用
  - 支持通过 Welford 算法的中间量 m2_accumulator 做增量合并（每日增量任务用）

数据源与约束：
  - 数据源：flow_tree + flow_node，由 FlowSampleCollector 拉取
  - normalized_name 来自 FlowNodeNameAlias 归一化结果，非原始 flow_tree.tree 里的 name
  - bk_biz_id=0 保留给"全局基线"（跨业务兜底），业务级基线 bk_biz_id > 0
  - 走 db_report app，自动路由到 report_db 独立数据库
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel


class DistributionType(models.TextChoices):
    """节点耗时的经验分布形态标记。

    用于上层查询判断：均值 / 标准差是否可信、是否只应看分位数。
    判定依据：stddev / mean 的比值（在 BaselineAggregator 中计算）。
    """

    #: 窄单峰：stddev/mean <= 0.5，均值+标准差高度可信
    NARROW_UNIMODAL = "narrow_unimodal", _("窄单峰分布")
    #: 宽单峰：0.5 < stddev/mean <= 2.0，均值可参考但需配合分位数
    WIDE_UNIMODAL = "wide_unimodal", _("宽单峰分布")
    #: 重尾：stddev/mean > 2.0，均值失真，只应看分位数
    HEAVY_TAILED = "heavy_tailed", _("重尾分布")
    #: 样本不足：sample_count 未达可靠阈值，任何指标都仅供参考
    UNRELIABLE = "unreliable", _("样本不足")


class FlowNodeDurationBaseline(AuditedModel):
    """流程节点耗时基线表（四维 unique）。

    职责：
      - 记录每个 (ticket_type, bk_biz_id, component_code, normalized_name) 的耗时基线
      - 双基线：正态分布 (mean/stddev) + 分位数 (p50/p90/p95/p99)
      - 支持增量合并：Welford 累计量 m2_accumulator + sample_count 可 O(1) 合并新样本

    使用方式：
      - 存量初始化：由 FlowBaselineService.rebuild() 全量重建
      - 每日增量：由 FlowBaselineService.incremental_run() 通过 Welford 算法合并昨日新样本

    边界：
      - 同一四维 key 唯一；重复写入需走 update_or_create 或 Welford 合并
      - bk_biz_id=0 表示全局基线，需与业务基线（bk_biz_id>0）并存以支持样本不足回退
    """

    ticket_type = models.CharField(_("单据类型"), max_length=LEN_NORMAL, help_text=_("如 MYSQL_PARTITION_V2"))
    bk_biz_id = models.IntegerField(
        _("业务ID"),
        default=0,
        help_text=_("CMDB 业务ID；0 表示跨业务全局基线"),
    )
    component_code = models.CharField(
        _("组件代码"), max_length=LEN_MIDDLE, help_text=_("flow tree activity component.code，如 mysql_db_actuator_execute")
    )
    normalized_name = models.CharField(
        _("归一化节点名"),
        max_length=LEN_LONG,
        help_text=_("经 NameCleaner + LLM 归一化后的节点名，作为四维 key 之一"),
    )

    # ==== 正态分布指标（Welford 增量算法维护）====
    #: 有效样本数量；作为可靠性判定的核心依据
    sample_count = models.BigIntegerField(_("样本数量"), default=0, help_text=_("累计有效样本数，用于可靠性判定"))
    mean_seconds = models.FloatField(_("均值(秒)"), default=0.0, help_text=_("Welford 算法维护的耗时均值"))
    stddev_seconds = models.FloatField(_("标准差(秒)"), default=0.0, help_text=_("Welford 算法维护的耗时标准差"))
    m2_accumulator = models.FloatField(
        _("Welford M2 累计量"),
        default=0.0,
        help_text=_("Welford 中间量 sum((x-mean)^2)，用于增量合并；不供上层直接使用"),
    )

    # ==== 分位数指标（每次 rebuild 时按原始样本重排序计算）====
    p50_seconds = models.FloatField(_("P50(秒)"), default=0.0)
    p90_seconds = models.FloatField(_("P90(秒)"), default=0.0)
    p95_seconds = models.FloatField(_("P95(秒)"), default=0.0)
    p99_seconds = models.FloatField(_("P99(秒)"), default=0.0)
    min_seconds = models.FloatField(_("最小值(秒)"), default=0.0)
    max_seconds = models.FloatField(_("最大值(秒)"), default=0.0)

    # ==== 分布形态与可靠性 ====
    distribution_type = models.CharField(
        _("分布形态"),
        max_length=LEN_SHORT,
        choices=DistributionType.choices,
        default=DistributionType.UNRELIABLE.value,
        help_text=_("依据 stddev/mean 与 sample_count 判定；上层应据此决定信任 mean 还是分位数"),
    )
    is_reliable = models.BooleanField(
        _("是否可靠"),
        default=False,
        help_text=_("sample_count >= 可靠阈值 且 分布形态非 UNRELIABLE 时为 True"),
    )

    # ==== 元信息 ====
    last_sample_finished_at = models.DateTimeField(
        _("最新样本完成时间"),
        null=True,
        blank=True,
        help_text=_("已纳入基线的最新一条 flow_node.updated_at；用于诊断增量水位"),
    )
    baseline_version = models.PositiveIntegerField(
        _("基线版本号"),
        default=1,
        help_text=_("每次 rebuild 递增；增量任务不改此值"),
    )

    class Meta(AuditedModel.Meta):
        verbose_name = _("流程节点耗时基线")
        verbose_name_plural = _("流程节点耗时基线")
        unique_together = [("ticket_type", "bk_biz_id", "component_code", "normalized_name")]
        indexes = [
            # 主查询路径：按业务 + 单据类型查所有基线
            models.Index(fields=["bk_biz_id", "ticket_type"]),
            # 全局基线兜底查询路径
            models.Index(fields=["ticket_type", "component_code", "normalized_name"]),
            # 可靠性筛选路径
            models.Index(fields=["is_reliable", "distribution_type"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.ticket_type}/biz={self.bk_biz_id}/{self.component_code}/{self.normalized_name} "
            f"n={self.sample_count} p50={self.p50_seconds} p95={self.p95_seconds}"
        )
