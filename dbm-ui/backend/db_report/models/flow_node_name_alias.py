# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

流程节点 name 归一化映射表 model。

模块职责：
  - 缓存 (ticket_type, component_code, cleaned_name) → normalized_name 的映射结果
  - 作为 LLM 语义匹配结果的持久化载体：LLM 判断只做一次，之后纯查表
  - 记录归一化来源与人工修正状态，支持 DBA 审阅和覆盖

数据源与约束：
  - cleaned_name：由 NameCleaner 通过正则清洗（去 IP/端口/hex/时间戳）产出
  - normalized_name：LLM 语义聚类的代表名，或首次出现时直接采用 cleaned_name
  - 走 db_report app，自动路由到 report_db 独立数据库
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel


class NameMatchSource(models.TextChoices):
    """归一化决策来源标记，用于事后审计与效果评估。"""

    #: 该 (tt, code) 下首次出现，直接以 cleaned_name 作为 normalized_name
    FIRST_SEEN = "first_seen", _("首次出现")
    #: LLM 判定与已有类别语义相同，归入已有类别
    LLM_MATCHED = "llm_matched", _("LLM 匹配已有类别")
    #: LLM 判定与所有已有类别都不同，创建新类别
    LLM_NEW_CLUSTER = "llm_new_cluster", _("LLM 创建新类别")
    #: LLM 调用失败降级：直接以 cleaned_name 作为 normalized_name，标记 needs_review
    LLM_FALLBACK = "llm_fallback", _("LLM 失败降级")
    #: DBA 人工设定，manual_locked 通常为 True
    MANUAL = "manual", _("人工设定")


class FlowNodeNameAlias(AuditedModel):
    """流程节点 name 归一化映射表（三维 unique）。

    职责：
      - 记录同一 (ticket_type, component_code) 下每个清洗后 name 归属于哪个归一化 name
      - 支撑"精准匹配加速"：新样本查表命中即返回，未命中才调 LLM
      - 支持人工审阅与锁定：manual_locked=True 后不再被 LLM 覆盖

    使用方式：
      - 归一化写入路径：NameNormalizer.normalize() 未命中时写入
      - 归一化读取路径：NameNormalizer.normalize() 首先查此表
      - 人工审阅路径：DBA 修改 normalized_name 并置 manual_locked=True

    边界：
      - unique_together 保证同一 (tt, code, cleaned_name) 只有一条记录
      - manual_locked=True 的记录，任何自动流程都不得覆盖 normalized_name
      - hit_count 用于观测热度，不参与业务判定
    """

    ticket_type = models.CharField(_("单据类型"), max_length=LEN_NORMAL)
    component_code = models.CharField(_("组件代码"), max_length=LEN_MIDDLE)
    cleaned_name = models.CharField(
        _("清洗后节点名"),
        max_length=LEN_LONG,
        help_text=_("原始 name 经 NameCleaner 正则清洗后的字符串（IP/端口/hex 已参数化）"),
    )

    normalized_name = models.CharField(
        _("归一化节点名"),
        max_length=LEN_LONG,
        help_text=_("最终归入的语义类别代表名；等于自身表示自成一类"),
    )
    match_source = models.CharField(
        _("归一化来源"),
        max_length=LEN_SHORT,
        choices=NameMatchSource.choices,
        default=NameMatchSource.FIRST_SEEN.value,
        help_text=_("记录此条映射如何生成，供审阅与效果评估"),
    )

    # ==== LLM 相关（仅 LLM 决策路径填充）====
    llm_confidence = models.FloatField(
        _("LLM 置信度"),
        null=True,
        blank=True,
        help_text=_("LLM 输出的 confidence 字段，取值 0~1；非 LLM 决策为 NULL"),
    )
    llm_reasoning = models.TextField(
        _("LLM 判定理由"),
        default="",
        blank=True,
        help_text=_("LLM 输出的 reasoning 文本，供人工审阅；非 LLM 决策为空串"),
    )

    # ==== 审阅与锁定 ====
    needs_review = models.BooleanField(
        _("需要人工审阅"),
        default=False,
        help_text=_("LLM 降级或低置信度时置 True，DBA 审阅确认后可置 False"),
    )
    manual_locked = models.BooleanField(
        _("人工锁定"),
        default=False,
        help_text=_("True 时任何自动流程不得覆盖 normalized_name"),
    )

    # ==== 观测指标 ====
    hit_count = models.BigIntegerField(
        _("命中次数"),
        default=0,
        help_text=_("此映射被查询命中的累计次数，用于热点观测；不参与业务判定"),
    )
    last_hit_at = models.DateTimeField(
        _("最近命中时间"),
        null=True,
        blank=True,
        help_text=_("最近一次被查询命中的时间；用于识别陈旧映射"),
    )

    class Meta(AuditedModel.Meta):
        verbose_name = _("流程节点名称归一化映射")
        verbose_name_plural = _("流程节点名称归一化映射")
        unique_together = [("ticket_type", "component_code", "cleaned_name")]
        indexes = [
            # 主查询路径：查同 (tt, code) 下所有已有归一化类别
            models.Index(fields=["ticket_type", "component_code", "normalized_name"]),
            # 审阅路径：找出所有需要人工审阅的记录
            models.Index(fields=["needs_review", "manual_locked"]),
        ]

    def __str__(self) -> str:
        return f"{self.ticket_type}/{self.component_code}/{self.cleaned_name} -> {self.normalized_name}"
