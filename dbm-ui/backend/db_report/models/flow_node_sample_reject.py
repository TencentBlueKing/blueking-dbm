# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

流程节点耗时样本"拒绝档案"表 model。

模块职责：
  - 记录采集器在构建耗时样本时因"耗时不合理"被剔除的节点，供 DBA 事后聚焦排查
  - 只记录两类拒绝原因：耗时过短（时钟回拨）/ 耗时过长（节点悬挂或异常）
  - 不参与基线聚合，也不与 FlowNodeDurationBaseline 有任何 FK 关系；仅作只读排查用

数据源与约束：
  - 数据源：由 FlowSampleCollector._build_sample 在过滤链中同步产出
  - 唯一约束：(root_id, node_id) —— 采集器可能因增量补跑对同一节点二次采样，走
    bulk_create(update_conflicts=True) 覆盖为最新一次判定，避免 reject 表膨胀
  - 走 db_report app，自动路由到 report_db 独立数据库
  - 与 FlowNodeDurationBaseline 有意分表：语义完全不同（异常档案 vs 正常基线）
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel


class RejectReason(models.TextChoices):
    """样本被拒绝进入基线的原因枚举。

    只包含"耗时不合理"这一类可排查、可运营的拒绝原因；
    其他内部过滤（tree/node 数据不一致、component_code 缺失等）静默跳过，不入本表。
    """

    #: 耗时 < SAMPLE_MIN_DURATION_SECONDS（默认 1s）；一般由时钟回拨或引擎异常导致
    TOO_SHORT = "too_short", _("耗时过短(疑似时钟回拨)")
    #: 耗时 > SAMPLE_MAX_DURATION_SECONDS（默认 24h）；一般是节点悬挂、超时未清理、组件真的很慢
    TOO_LONG = "too_long", _("耗时过长(疑似节点悬挂)")


class FlowNodeSampleReject(AuditedModel):
    """流程节点耗时样本拒绝档案表。

    职责：
      - 存储被"耗时区间过滤"淘汰的节点原始信息，供 DBA 排查异常单据/异常组件
      - 提供按业务、按组件、按耗时排序的常用查询路径

    使用方式（示例 SQL）：
      - 找最卡的悬挂节点：
          ORDER BY duration_seconds DESC WHERE reject_reason='too_long'
      - 定位老悬挂的组件：
          GROUP BY component_code WHERE reject_reason='too_long'

    边界：
      - 同一 (root_id, node_id) 唯一；重复采样以最近一次判定覆盖旧记录
      - duration_seconds 照实存储原始秒数，不做上限截断（哪怕是 31 天也存原值），
        方便按耗时排序找出"最异常"的节点
    """

    # ==== 溯源坐标（可反查 flow_tree / flow_node 原始记录）====
    root_id = models.CharField(
        _("流程 root_id"),
        max_length=LEN_NORMAL,
        help_text=_("对应 FlowTree.root_id，可用于反查原始流程"),
    )
    node_id = models.CharField(
        _("节点 node_id"),
        max_length=LEN_NORMAL,
        help_text=_("对应 FlowNode.node_id，可用于反查原始节点"),
    )

    # ==== 归类维度（与 FlowNodeDurationBaseline 四维对齐，便于按维度聚合排查）====
    bk_biz_id = models.IntegerField(_("业务ID"), default=0, help_text=_("CMDB 业务ID；0 表示未知/跨业务"))
    ticket_type = models.CharField(
        _("单据类型"),
        max_length=LEN_NORMAL,
        default="",
        help_text=_("如 MYSQL_PARTITION_V2；空表示 flow_tree 未取到"),
    )
    component_code = models.CharField(
        _("组件代码"),
        max_length=LEN_MIDDLE,
        default="",
        help_text=_("flow tree activity component.code；空表示 tree 缺失该字段"),
    )
    raw_name = models.CharField(
        _("原始节点名"),
        max_length=LEN_LONG,
        default="",
        help_text=_("flow tree activity.name 原文，未清洗；仅用于人工识别"),
    )

    # ==== 拒绝证据 ====
    duration_seconds = models.BigIntegerField(
        _("原始耗时(秒)"),
        default=0,
        help_text=_("(node.updated_at - node.started_at) 秒数；照实存储不截断"),
    )
    started_at = models.DateTimeField(
        _("节点开始时间"),
        null=True,
        blank=True,
        help_text=_("对应 FlowNode.started_at；用于时序核对"),
    )
    finished_at = models.DateTimeField(
        _("节点结束时间"),
        null=True,
        blank=True,
        help_text=_("对应 FlowNode.updated_at（最后一次进入 FINISHED）；用于时序核对"),
    )
    reject_reason = models.CharField(
        _("拒绝原因"),
        max_length=LEN_SHORT,
        choices=RejectReason.choices,
        help_text=_("仅两种：too_short(时钟回拨) / too_long(节点悬挂)"),
    )

    class Meta(AuditedModel.Meta):
        verbose_name = _("流程节点样本拒绝档案")
        verbose_name_plural = _("流程节点样本拒绝档案")
        # 同一节点重复采样时以最新一次判定覆盖旧记录，防止 reject 表膨胀
        unique_together = [("root_id", "node_id")]
        indexes = [
            # 排查路径 1：按拒绝原因 + 耗时倒排，找最异常节点
            models.Index(fields=["reject_reason", "duration_seconds"]),
            # 排查路径 2：按业务 + 单据类型聚合排查
            models.Index(fields=["bk_biz_id", "ticket_type"]),
            # 排查路径 3：按组件聚合，定位"哪个组件老出问题"
            models.Index(fields=["component_code"]),
        ]

    def __str__(self) -> str:
        return (
            f"reject[{self.reject_reason}] root={self.root_id} node={self.node_id} "
            f"code={self.component_code} duration={self.duration_seconds}s"
        )
