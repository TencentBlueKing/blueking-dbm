# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 MCP - 读侧业务实现（供 View 调用）。

模块职责：
    - 实现 2 个读侧接口：``discover_dimensions`` / ``fetch_summaries``
    - 屏蔽 ORM 细节，返回可以直接被 Serializer 序列化的 dict / list[dict]

设计要点：
    - 用类 ``PortraitQueryService`` 组织；两个方法均为 classmethod，无状态
    - ``fetch_summaries`` 的关键语义：**返回时间窗内所有匹配摘要**（不做"每 code 取最新"的聚合），
      Agent 侧可看到多次巡检的时间序列，便于分析变化趋势
    - "未指定 codes"分支：自动按集群 db_type 取该 DB 下所有 enabled 维度作为默认集合

边界：
    - cluster_domain 找不到对应集群 -> summaries=[]，missing_codes=输入 codes；不抛异常
    - 某 code 时间窗内 0 条数据     -> 该 code 出现在 missing_codes 中
    - 某 code 时间窗内 N 条数据     -> 该 code 在 summaries 中出现 N 次；不做去重
"""
from datetime import datetime
from typing import Dict, List, Optional

from django.db.models import QuerySet

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.models.portrait_dimension_registry import PortraitDimensionRegistry
from backend.db_report.models.portrait_dimension_summary import PortraitDimensionSummary


class PortraitQueryService:
    """集群画像读侧查询服务。

    职责：
        - 面向 MCP View 层，提供两个读侧方法：维度枚举 + 摘要拉取
        - 内部完成 db_type 反查、注册表 join、时间窗过滤等聚合逻辑

    典型使用（View 层直接调 classmethod）::

        dims = PortraitQueryService.discover_dimensions(db_type="mysql")
        result = PortraitQueryService.fetch_summaries(
            bk_biz_id=100001,
            cluster_domain="a.b.c",
            codes=["slow_query", "config_check"],
            since=t1, until=t2,
        )

    线程安全：是（无实例状态）
    """

    # ------------------------------------------------------------------
    # 工具 1：discover_dimensions
    # ------------------------------------------------------------------

    @classmethod
    def discover_dimensions(cls, db_type: Optional[str] = None) -> Dict:
        """查询当前所有启用中的维度信息（供 Agent 决定采集哪些）。

        :param db_type: 可选按 DB 类型过滤；空 / None 表示不过滤
        :return: dict，形如::

            {"dimensions": [{"db_type": "...", "code": "...", "name": "...", "description": "..."}]}

        边界：
            - 无匹配 -> dimensions=[]
            - 只返回 enabled=True 的维度；enabled=False 的维度对 Agent 完全不可见
        """
        qs: QuerySet = PortraitDimensionRegistry.objects.filter(enabled=True)
        if db_type:
            qs = qs.filter(db_type=db_type)
        qs = qs.order_by("db_type", "code")

        dimensions: List[Dict] = [
            {
                "db_type": obj.db_type,
                "code": obj.code,
                "name": obj.name,
                "description": obj.description or "",
            }
            for obj in qs
        ]
        return {"dimensions": dimensions}

    # ------------------------------------------------------------------
    # 工具 2：fetch_summaries
    # ------------------------------------------------------------------

    @classmethod
    def fetch_summaries(
        cls,
        bk_biz_id: int,
        cluster_domain: str,
        codes: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Dict:
        """按集群 + 维度批量拉取"时间窗内**全部**匹配的巡检摘要"，供 Agent 分析。

        执行流程：
            1) 解析集群 db_type（通过 cluster_domain 反查）；找不到 -> 直接返回空
            2) 确定"目标 codes"：
               - 调用方显式传 codes -> 取交集：codes ∩ (db_type 下 enabled)
               - 未传 codes         -> 取该 db_type 下全部启用维度作为默认集合
            3) 一次 SQL 拉取时间窗内所有匹配记录（按 code 升序 + report_time 升序）
            4) 逐条装配返回；同时统计"时间窗内 0 条数据"的 code 归入 missing_codes

        :param bk_biz_id: 业务 ID（用于强约束数据归属，避免跨业务读取）
        :param cluster_domain: 集群不可变域名
        :param codes: 可选维度短码列表；None / 空列表 表示按 db_type 自动取全部启用维度
        :param since: 可选时间下界（含）
        :param until: 可选时间上界（含）
        :return: dict，形如::

            {
              "bk_biz_id": 100001,
              "cluster_domain": "a.b.c",
              "summaries": [ {db_type, code, name, ...report_time, summary, detail_url}, ... ],
              "missing_codes": ["xxx", ...],
            }

        边界：
            - cluster_domain 未找到集群 -> summaries=[], missing_codes=(codes 或 [])
            - 目标 codes 为空           -> summaries=[], missing_codes=[]
            - 某 code 在时间窗内 0 条   -> 该 code 归入 missing_codes（不出现在 summaries 中）
            - 某 code 在时间窗内 N 条   -> 该 code 在 summaries 中出现 N 次；**不做去重**
            - summaries 按 (code 升序, report_time 升序) 排序，方便 LLM 按时间线阅读
        """
        # 1) 解析集群 db_type
        db_type: Optional[str] = cls._resolve_db_type(bk_biz_id=bk_biz_id, cluster_domain=cluster_domain)
        if db_type is None:
            # 集群不存在或不属于该业务；返回空结构，不抛异常，方便 Agent 兜底
            return {
                "bk_biz_id": bk_biz_id,
                "cluster_domain": cluster_domain,
                "summaries": [],
                "missing_codes": list(codes or []),
            }

        # 2) 确定"目标 codes"：显式传入 vs. 自动取 db_type 下所有 enabled
        registry_map: Dict[str, PortraitDimensionRegistry] = cls._build_registry_map(db_type=db_type, codes=codes)
        target_codes: List[str] = list(registry_map.keys())
        if not target_codes:
            return {
                "bk_biz_id": bk_biz_id,
                "cluster_domain": cluster_domain,
                "summaries": [],
                "missing_codes": list(codes or []),
            }

        # 3) 一次 SQL 拉取时间窗内的全部匹配记录
        rows: List[PortraitDimensionSummary] = cls._query_rows_in_range(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            db_type=db_type,
            codes=target_codes,
            since=since,
            until=until,
        )

        # 4) 逐条装配 + 统计 missing_codes
        summaries: List[Dict] = [
            {
                "db_type": row.db_type,
                "code": row.code,
                "name": registry_map[row.code].name if row.code in registry_map else row.code,
                "bk_biz_id": row.bk_biz_id,
                "cluster_domain": row.cluster_domain,
                "report_time": row.report_time,
                "summary": row.summary or "",
                "detail_url": row.detail_url or "",
            }
            for row in rows
        ]

        hit_codes: set = {item["code"] for item in summaries}
        missing_codes: List[str] = [c for c in target_codes if c not in hit_codes]

        return {
            "bk_biz_id": bk_biz_id,
            "cluster_domain": cluster_domain,
            "summaries": summaries,
            "missing_codes": missing_codes,
        }

    # ------------------------------------------------------------------
    # 私有辅助
    # ------------------------------------------------------------------

    @classmethod
    def _resolve_db_type(cls, bk_biz_id: int, cluster_domain: str) -> Optional[str]:
        """通过 (bk_biz_id, cluster_domain) 反查集群 db_type；找不到返回 None。"""
        cluster: Optional[Cluster] = Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain=cluster_domain).first()
        if cluster is None:
            return None
        return ClusterType.cluster_type_to_db_type(cluster.cluster_type)

    @classmethod
    def _build_registry_map(cls, db_type: str, codes: Optional[List[str]]) -> Dict[str, PortraitDimensionRegistry]:
        """构建 {code: registry_obj} 映射；只包含 enabled=True 的维度。

        - 若 codes 显式传入 -> 交集：codes ∩ (db_type 下 enabled)
        - 若 codes 未传     -> 全量：db_type 下 enabled 的所有维度
        """
        qs: QuerySet = PortraitDimensionRegistry.objects.filter(db_type=db_type, enabled=True)
        if codes:
            qs = qs.filter(code__in=list(codes))
        return {obj.code: obj for obj in qs}

    @classmethod
    def _query_rows_in_range(
        cls,
        bk_biz_id: int,
        cluster_domain: str,
        db_type: str,
        codes: List[str],
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> List[PortraitDimensionSummary]:
        """一次 SQL 拉取时间窗内的**全部**匹配摘要记录，不做聚合、不做去重。

        :param codes: 目标维度短码列表；已在上层做过 enabled 过滤
        :param since: 时间下界（含）；None 表示不限
        :param until: 时间上界（含）；None 表示不限
        :return: List[PortraitDimensionSummary]，按 (code 升序, report_time 升序) 排序
        """
        qs: QuerySet = PortraitDimensionSummary.objects.filter(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            db_type=db_type,
            code__in=codes,
        )
        if since is not None:
            qs = qs.filter(report_time__gte=since)
        if until is not None:
            qs = qs.filter(report_time__lte=until)

        return list(qs.order_by("code", "report_time", "id"))
