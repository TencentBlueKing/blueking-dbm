# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

流程节点耗时基线增量水位表 model。

模块职责：
  - 记录每个 (ticket_type, bk_biz_id) 维度下"已经处理到的最新样本时间"
  - 每日增量任务基于此水位向后滚动，避免重复计算或遗漏
  - 存量初始化完成后写入初始水位

数据源与约束：
  - 水位字段基于 flow_node.updated_at（视为节点完成时间）
  - 不持久化任何原始样本，仅存时间戳
  - 走 db_report app，自动路由到 report_db 独立数据库
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_NORMAL
from backend.bk_web.models import AuditedModel


class FlowNodeBaselineWatermark(AuditedModel):
    """流程节点基线增量水位表（二维 unique）。

    职责：
      - 每个 (ticket_type, bk_biz_id) 维护一条水位记录
      - 增量任务读取水位作为 since，处理完后向前推进水位

    使用方式：
      - 存量初始化：FlowBaselineService.rebuild() 完成后写入初始水位（等于处理窗口的 until）
      - 每日增量：FlowBaselineService.incremental_run() 读水位 → 采样 → 更新水位
      - 手动修复：DBA 可通过 command 参数指定重置某条水位

    边界：
      - 首次增量运行时若无水位记录，退化为按 default_lookback_days 回溯
      - 水位更新与基线写库应在同一事务内，避免部分成功导致水位错位
    """

    ticket_type = models.CharField(_("单据类型"), max_length=LEN_NORMAL)
    bk_biz_id = models.IntegerField(_("业务ID"), default=0, help_text=_("CMDB 业务ID；0 表示全局基线维度"))

    last_processed_finished_at = models.DateTimeField(
        _("已处理最新样本时间"),
        null=True,
        blank=True,
        help_text=_("已纳入基线的最新一条 flow_node.updated_at；下次增量的 since 起点"),
    )
    last_run_at = models.DateTimeField(
        _("最近一次运行时间"),
        null=True,
        blank=True,
        help_text=_("最近一次增量任务执行完成的时间；用于诊断任务是否卡住"),
    )
    last_run_sample_count = models.IntegerField(
        _("最近一次运行处理样本数"),
        default=0,
        help_text=_("最近一次增量任务处理的样本数量；用于识别异常波动"),
    )

    class Meta(AuditedModel.Meta):
        verbose_name = _("流程节点基线增量水位")
        verbose_name_plural = _("流程节点基线增量水位")
        unique_together = [("ticket_type", "bk_biz_id")]

    def __str__(self) -> str:
        return f"{self.ticket_type}/biz={self.bk_biz_id} watermark={self.last_processed_finished_at}"
