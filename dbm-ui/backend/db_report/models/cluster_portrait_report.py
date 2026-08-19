# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 - 报告基础信息表 Model。

模块职责：
    - 存储「集群画像功能」每一次生成的报告级元信息（一次生成 = 一行）
    - 承接前端 / OpenAPI 检索：按 (集群域名 / 业务 / db_type / 时间窗) 定位一份历史画像报告
    - 与 PortraitDimensionSummary 的关系：
        * PortraitDimensionSummary = 单个维度的一次巡检摘要（细粒度、追加写入、多条）
        * ClusterPortraitReport = 集群画像 Agent 汇总多个维度后产出的「整份报告」的元信息
          （报告正文 body / 各维度明细 由分享链接或详情表承载，本表只保留摘要 + 索引字段）

设计要点：
    - 一条记录 = 一次画像报告的产出快照；不做原地更新（如需重跑视为新报告，新增一行）
    - report_from / report_to 表示画像分析所覆盖的时间窗；create_at 表示报告生成时间
    - summary 存放 LLM 产出的报告级摘要文本（前端卡片展示 / OpenAPI 返回），过长正文走 share_url
    - share_url 存放前端可访问的完整报告页面链接
    - db_type 与 PortraitDimensionRegistry.db_type 语义对齐，方便按 DB 类型筛选

边界：
    - summary 允许为空字符串，视为「本次画像无风险要点」
    - 本表不做去重；同一集群同一时间窗多次生成会有多条记录，前端可按 create_at 倒序取最新
    - 报告详情（各维度 summary、图表、AI 分析明细）不在本表；本表只做「报告索引 + 摘要」

TODO（数据老化 / TTL）：
    - 本表当前为纯追加写入，无自动清理；上线跑通后需评估保留窗口与清理策略
    - 参考 PortraitDimensionSummary 的 TODO 一起实现（django management command + celery beat）
"""
from datetime import datetime
from typing import Optional

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.configuration.constants import DBType


class ClusterPortraitReport(AuditedModel):
    """集群画像 - 报告基础信息表。

    职责：
        - 记录每一次「集群画像报告」的生成快照（元信息 + 摘要 + 分享链接）
        - 前端画像报告列表 / 详情跳转的检索入口

    典型使用：
        - 画像生成 Pipeline：报告产出后追加一条，写入摘要与 share_url
        - 前端 / OpenAPI：按 cluster_domain / bk_biz_id / db_type + 时间范围 分页查询历史报告
        - 集群画像 Agent：可反查历史报告，用于横向对比与趋势分析

    边界：
        - 不做原地更新；重跑视为新报告
        - summary 为空字符串 = 本次画像无风险要点，仍是一条有效记录
        - 报告全文 / 明细不在本表，走 share_url 或专用详情表
    """

    #: 业务 ID；用于按业务隔离查询与鉴权
    bk_biz_id = models.IntegerField(
        default=0,
        verbose_name=_("业务ID"),
        help_text=_("CMDB 业务 ID"),
    )

    #: 数据库类型；choices 引用 DBType 枚举，与画像注册表 db_type 对齐
    db_type = models.CharField(
        max_length=32,
        choices=DBType.get_choices(),
        default="",
        verbose_name=_("数据库类型"),
        help_text=_("集群所属 DB 类型，与 tb_portrait_dimension_registry.db_type 对齐"),
    )

    #: 集群不可变域名；集群画像的核心检索键
    cluster_domain = models.CharField(
        max_length=255,
        default="",
        verbose_name=_("集群域名"),
        help_text=_("集群不可变主域名，作为画像报告的主检索键"),
    )

    #: 画像分析所覆盖的时间窗起点
    report_from_time = models.DateTimeField(
        verbose_name=_("报告时间段起始"),
        help_text=_("本次画像分析所覆盖的时间窗起点（业务时间）"),
    )

    #: 画像分析所覆盖的时间窗终点
    report_to_time = models.DateTimeField(
        verbose_name=_("报告时间段结束"),
        help_text=_("本次画像分析所覆盖的时间窗终点（业务时间）"),
    )

    #: 报告级摘要文本；由集群画像 Agent / LLM 产出，前端卡片直接引用
    summary = models.TextField(
        default="",
        blank=True,
        verbose_name=_("报告摘要"),
        help_text=_("本次画像报告的整体摘要文本；空字符串代表无风险要点"),
    )

    #: 报告分享链接；前端可访问的完整报告页面 URL
    share_url = models.CharField(
        max_length=512,
        default="",
        blank=True,
        verbose_name=_("报告分享链接"),
        help_text=_("前端可访问的完整画像报告页面链接"),
    )

    #: 报告健康分；-1 = 未上报 / 分数系统未开启；正常取值 0~100（越高越健康）
    #  语义：
    #    * -1：本次生成未产出分数（例如：Agent 未启用打分环节 / 打分失败 / 分数系统灰度未覆盖）
    #    *  0~100：由集群画像 Agent 产出的综合健康分，前端卡片可直接展示
    #  取值范围校验（不在 DB 层做 CheckConstraint，交由写入方 / Serializer 校验，保持与其他表一致的柔性策略）
    score = models.IntegerField(
        default=-1,
        verbose_name=_("报告健康分"),
        help_text=_("报告综合健康分；-1 表示未上报或分数系统未开启，正常范围 0~100"),
    )

    class Meta:
        # 与 db_report 其它 model 保持一致的命名风格：tb_ 前缀 + 小写下划线
        db_table = "tb_cluster_portrait_report"
        verbose_name = _("集群画像-报告基础信息")
        verbose_name_plural = _("集群画像-报告基础信息")
        indexes = [
            # 主查询路径：按 (集群 + 报告起始时间倒序) 拉某集群的历史画像报告
            models.Index(
                fields=["cluster_domain", "report_from_time"],
                name="idx_portrait_rep_domain_from",
            ),
            # 业务维度聚合：按 (业务 + db_type + 时间) 拉某业务下所有画像报告
            models.Index(
                fields=["bk_biz_id", "db_type", "report_from_time"],
                name="idx_portrait_rep_biz_dbtype",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.db_type}:{self.cluster_domain}#{self.report_from_time}~{self.report_to_time}"

    # ------------------------------------------------------------------
    # 专属写入方法（供画像生成 Pipeline 调用）
    #
    # 使用姿势（两阶段写入）：
    #   1) 报告开始生成前：
    #        rid = ClusterPortraitReport.init_record(bk_biz_id=..., cluster_domain=..., db_type=..., creator=...)
    #   2) 报告生成结束后：
    #        ClusterPortraitReport.fill_report_result(
    #            record_id=rid, summary=..., share_url=..., score=..., updater=...,
    #        )
    #
    # 为什么放 classmethod 而不是实例方法：
    #   - 两个入口都是「无实例上下文」场景（初始化时还没有对象；补齐时只有 id）
    #   - 使用 filter().update() 做局部字段更新，避免并发覆盖其他字段
    # ------------------------------------------------------------------

    @classmethod
    def init_record(
        cls,
        bk_biz_id: int,
        cluster_domain: str,
        db_type: str,
        creator: str,
    ) -> int:
        """初始化一条画像报告占位记录（报告生成前调用）。

        设计要点 / 怎么做：
          - 仅写入索引字段（业务/集群/db_type）与 creator；其余业务字段（summary / share_url / score）
            走 model 默认值（空字符串 / -1）
          - report_from_time 以「本次报告生成开始时刻」为准（即调用本方法时的当前时间）
          - report_to_time 先落一个占位值（同当前时间），等 fill_report_result 阶段再改写为
            「报告生成完成时刻」——这样即便中途异常，也不会留下空指针字段
          - updater 与 creator 一致（首次落库，尚无更新人）

        :param bk_biz_id: 业务 ID，必填；用于按业务隔离
        :param cluster_domain: 集群不可变域名，必填；作为主检索键
        :param db_type: 集群 DB 类型，必填；应为 DBType 枚举值
        :param creator: 创建人 username，必填；由 AuditedModel 语义约束不可为空
        :return: 新建记录的主键 id（int）

        边界 / 异常：
          - 若入参不满足 DB 层约束（如 bk_biz_id 非 int）→ 直接抛出 Django ORM 原生异常，
            调用方自行处理（本方法不吞异常，保证问题可追溯）
        """
        # 报告开始时间：调用本方法即视为「报告生成动作」开始
        now: datetime = timezone.now()
        obj = cls.objects.create(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            db_type=db_type,
            report_from_time=now,
            # 占位：与 report_from_time 相同；fill_report_result 阶段再改写为真实完成时刻
            report_to_time=now,
            creator=creator,
            updater=creator,
        )
        return obj.id

    @classmethod
    def fill_report_result(
        cls,
        record_id: int,
        summary: str,
        share_url: str,
        score: int,
        updater: str,
        report_to_time: Optional[datetime] = None,
    ) -> int:
        """补齐画像报告生成结果字段（报告生成完成后调用）。

        设计要点 / 怎么做：
          - 通过 record_id 精确定位由 init_record 产出的占位记录
          - 使用 filter().update() 做原子的字段级更新，避免并发场景下覆盖其它字段
          - 同步改写 report_to_time 为「报告生成完成时刻」；不传则取 timezone.now()
          - .update() 不会触发 auto_now，因此显式写 update_at，保持审计字段语义

        :param record_id: init_record 返回的主键 id，必填
        :param summary: 报告级摘要文本；允许传空字符串（视为无风险要点）
        :param share_url: 前端可访问的完整报告页面 URL；允许空字符串
        :param score: 报告健康分；-1 表示未上报 / 分数系统未开启；正常范围 0~100
        :param updater: 更新人 username，必填
        :param report_to_time: 可选；报告完成的业务时间，默认 timezone.now()
        :return: 实际更新的行数；正常为 1；为 0 表示 record_id 不存在

        边界 / 异常：
          - record_id 不存在 → 返回 0，不抛异常（由调用方决定告警/重试策略）
          - score 取值范围校验交由写入方 / Serializer，此处不再拦截，保持柔性
        """
        finished_at: datetime = report_to_time or timezone.now()
        # 使用 filter().update() 而非 obj.save()：只更新 5 个业务字段 + 审计时间，避免竞态覆盖
        updated_rows: int = cls.objects.filter(id=record_id).update(
            summary=summary,
            share_url=share_url,
            score=score,
            report_to_time=finished_at,
            updater=updater,
            # .update() 不触发 auto_now，需显式赋值以保持 update_at 语义
            update_at=finished_at,
        )
        return updated_rows
