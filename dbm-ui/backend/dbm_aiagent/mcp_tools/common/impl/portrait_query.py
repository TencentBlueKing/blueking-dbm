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
    - ``discover_dimensions`` 入参为 (bk_biz_id, cluster_domain)，通过 ``resolve_cluster`` 反查
      集群对象并取 db_type，返回该 db_type 下所有 enabled 维度；与写侧 ``ingest_summary``
      保持"集群 -> db_type"唯一事实源
    - ``fetch_summaries`` 的关键语义：**返回时间窗内所有匹配摘要**（不做"每 code 取最新"的聚合），
      Agent 侧可看到多次巡检的时间序列，便于分析变化趋势
    - **时间窗与集群 create_at 合流**：``immute_domain`` 存在被回收再分配的可能，
      若查询区间早于当前集群 ``create_at``，数据可能属于"上一代同域名集群"的巡检遗留（脏数据）；
      故读侧强制以 ``max(since, cluster.create_at)`` 作为 ``effective_since``，
      并把 ``cluster_created_at`` / ``effective_since`` / ``effective_until`` 回显给 Agent
    - "未指定 codes"分支：自动按集群 db_type 取该 DB 下所有 enabled 维度作为默认集合

边界：
    - cluster_domain 找不到对应集群 -> ``status="cluster_not_found"``、db_type=""、summaries=[]，
      Agent 可据此区分「集群不存在」与「集群存在但时间窗无数据」
    - 用户区间完全早于集群创建时间   -> ``status="time_range_before_cluster_created"``、summaries=[]
    - since > until                  -> ``status="invalid_time_range"``、summaries=[]
    - 某 code 时间窗内 0 条数据      -> 该 code 出现在 ``missing_codes`` 中（status 仍为 ok）
    - 某 code 时间窗内 N 条数据      -> 该 code 在 summaries 中出现 N 次；不做去重
"""
from datetime import datetime
from itertools import groupby
from typing import Dict, List, Optional, Tuple

from django.db.models import QuerySet

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.enums import SummaryFetchStrategy
from backend.db_report.models.portrait_dimension_registry import PortraitDimensionRegistry
from backend.db_report.models.portrait_dimension_summary import PortraitDimensionSummary


class PortraitQueryService:
    """集群画像读侧查询服务。

    职责：
        - 面向 MCP View 层，提供两个读侧方法：维度枚举 + 摘要拉取
        - 内部完成集群元数据反查、注册表 join、时间窗与集群创建时间合流、脏数据过滤等聚合逻辑

    典型使用（View 层直接调 classmethod）::

        dims = PortraitQueryService.discover_dimensions(
            bk_biz_id=100001, cluster_domain="a.b.c",
        )
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
    def discover_dimensions(cls, bk_biz_id: int, cluster_domain: str) -> Dict:
        """按 (bk_biz_id, cluster_domain) 反查集群 db_type，返回该集群 db_type 下所有启用中的维度。

        设计要点 / 怎么做：
            - 数据源：``PortraitDimensionRegistry`` 表（enabled=True 过滤）
            - db_type 由服务端通过 ``resolve_cluster`` 反查集群对象后取 ``cluster_type`` 归一化得到，
              与 ``ingest_summary`` / ``fetch_summaries`` 共用同一事实源，避免口径不一致
            - 出参通过 ``status`` 字段表达可预期分支（cluster_not_found），不抛异常

        :param bk_biz_id: 业务 ID（正整数）
        :param cluster_domain: 集群不可变主域名（``immute_domain``）
        :return: dict，形如::

            {
              "status": "ok",
              "db_type": "mysql",
              "dimensions": [{"db_type": "...", "dimension_code": "...", "name": "...", "description": "..."}]
            }

        边界：
            - 集群不存在或不属于该业务 -> ``status="cluster_not_found"``、db_type=""、dimensions=[]
            - 该 db_type 下 0 条启用维度 -> ``status="ok"``、dimensions=[]（不算失败）
            - 只返回 enabled=True 的维度；enabled=False 的维度对 Agent 完全不可见

        注意：
            出参字典中**不使用** ``code`` 作为键名，改用 ``dimension_code``；
            原因是外层 ``BKAPIRenderer`` 若在返回体顶层看到 ``code`` 键会走"用户自定义标准返回"
            短路分支，导致 Go MCP 网关 unmarshal ``code``(int) 失败。为保持读写侧字段命名一致，
            嵌套元素中也统一使用 ``dimension_code``。
        """
        # 1) 反查集群对象；找不到集群直接返回 cluster_not_found 分支
        cluster: Optional[Cluster] = cls.resolve_cluster(bk_biz_id=bk_biz_id, cluster_domain=cluster_domain)
        if cluster is None:
            return {"status": "cluster_not_found", "db_type": "", "dimensions": []}

        db_type: str = ClusterType.cluster_type_to_db_type(cluster.cluster_type)

        # 2) 按 db_type 过滤该 DB 下所有 enabled 维度
        qs: QuerySet = PortraitDimensionRegistry.objects.filter(enabled=True, db_type=db_type)
        # 注意：order_by("code") 中的 "code" 是 ORM 字段名（数据库列），不是出参 dict 键
        qs = qs.order_by("code")

        dimensions: List[Dict] = [
            {
                "db_type": obj.db_type,
                "dimension_code": obj.code,
                "name": obj.name,
                "description": obj.description or "",
                "weight": obj.weight,
                "summary_fetch_strategy": obj.summary_fetch_strategy or SummaryFetchStrategy.ALL.value,
            }
            for obj in qs
        ]
        return {"status": "ok", "db_type": db_type, "dimensions": dimensions}

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
            1) 通过 ``resolve_cluster`` 反查集群对象，取 ``cluster.cluster_type`` 归一化为 db_type，
               同时拿到 ``cluster.create_at`` 作为"当前集群巡检数据的物理下界"；
               集群不存在 -> ``status="cluster_not_found"``
            2) **时间窗与集群创建时间合流**（见 :meth:`_reconcile_time_range`）：
               - 用户未传 ``since`` 或 ``since < cluster.create_at``：``effective_since = cluster.create_at``
               - 用户传的 ``until < cluster.create_at``：整段区间都是脏数据
                 -> ``status="time_range_before_cluster_created"``
               - ``since > until`` -> ``status="invalid_time_range"``
               - 其它 -> 原样使用；出参回显 ``effective_since`` / ``effective_until``，方便 Agent 感知
            3) 确定"目标 codes"：
               - 调用方显式传 codes -> 取交集：codes ∩ (db_type 下 enabled)
               - 未传 codes         -> 取该 db_type 下全部启用维度作为默认集合
            4) 一次 SQL 拉取 effective 时间窗内所有匹配记录（按 code 升序 + report_time 升序）
            5) 按每个维度的 ``summary_fetch_strategy`` 过滤：all 保留全部 / last 取最新一条 / first 取最老一条
            6) 逐条装配返回；同时统计"时间窗内 0 条数据"的 code 归入 missing_codes

        :param bk_biz_id: 业务 ID（用于强约束数据归属，避免跨业务读取）
        :param cluster_domain: 集群不可变域名
        :param codes: 可选维度短码列表（对应 MCP 入参 ``dimension_codes``）；
                      None / 空列表 表示按 db_type 自动取全部启用维度
        :param since: 可选时间下界（含）；将与集群 ``create_at`` 合流，避免读取上一代同域名集群的脏数据
        :param until: 可选时间上界（含）
        :return: dict，形如::

            {
              "status": "ok" | "cluster_not_found" | "time_range_before_cluster_created" | "invalid_time_range",
              "db_type": "mysql",                    # 失败分支为空串
              "bk_biz_id": 100001,
              "cluster_domain": "a.b.c",
              "cluster_created_at": <datetime>,      # cluster_not_found 分支为 None
              "effective_since": <datetime>,         # 服务端实际用于查询的下界；集群缺失分支为 None
              "effective_until": <datetime|None>,    # 服务端实际用于查询的上界；不限则为 None
              "summaries": [...],
              "missing_codes": [...],
            }

        边界（Agent 判断口径）：
            - ``status="cluster_not_found"``                -> 集群不存在或不属于该业务
            - ``status="time_range_before_cluster_created"``-> 用户区间完全早于集群创建时间；无有效数据
            - ``status="invalid_time_range"``               -> since > until，语义不成立
            - ``status="ok"`` + ``summaries=[]``            -> 集群存在但 effective 时间窗内 0 条数据
            - ``status="ok"`` + 某 code 在 ``missing_codes``-> 该 code 在 effective 时间窗内 0 条数据
            - ``effective_since`` != 用户传的 ``since``     -> 说明被服务端上调至 ``cluster.create_at``（脏数据过滤）
            - summaries 按 (code 升序, report_time 升序) 排序，方便 LLM 按时间线阅读
        """
        # 1) 反查集群对象；找不到集群时明确通过 status=cluster_not_found 告知 Agent
        cluster: Optional[Cluster] = cls.resolve_cluster(bk_biz_id=bk_biz_id, cluster_domain=cluster_domain)
        if cluster is None:
            return {
                "status": "cluster_not_found",
                "db_type": "",
                "bk_biz_id": bk_biz_id,
                "cluster_domain": cluster_domain,
                "cluster_created_at": None,
                "effective_since": None,
                "effective_until": None,
                "summaries": [],
                "missing_codes": list(codes or []),
            }

        db_type: str = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
        cluster_created_at: datetime = cluster.create_at

        # 2) 时间窗与集群创建时间合流：屏蔽上一代同域名集群的脏数据
        effective_since, effective_until, time_status = cls._reconcile_time_range(
            cluster_created_at=cluster_created_at,
            since=since,
            until=until,
        )
        if time_status != "ok":
            # invalid_time_range / time_range_before_cluster_created：直接短路返回
            return {
                "status": time_status,
                "db_type": db_type,
                "bk_biz_id": bk_biz_id,
                "cluster_domain": cluster_domain,
                "cluster_created_at": cluster_created_at,
                "effective_since": effective_since,
                "effective_until": effective_until,
                "summaries": [],
                "missing_codes": list(codes or []),
            }

        # 3) 确定"目标 codes"：显式传入 vs. 自动取 db_type 下所有 enabled
        registry_map: Dict[str, PortraitDimensionRegistry] = cls._build_registry_map(db_type=db_type, codes=codes)
        target_codes: List[str] = list(registry_map.keys())
        if not target_codes:
            # 集群存在但目标 codes 集合为空（如 codes 与 enabled 维度无交集）
            return {
                "status": "ok",
                "db_type": db_type,
                "bk_biz_id": bk_biz_id,
                "cluster_domain": cluster_domain,
                "cluster_created_at": cluster_created_at,
                "effective_since": effective_since,
                "effective_until": effective_until,
                "summaries": [],
                "missing_codes": list(codes or []),
            }

        # 4) 一次 SQL 拉取 effective 时间窗内的全部匹配记录
        rows: List[PortraitDimensionSummary] = cls._query_rows_in_range(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            db_type=db_type,
            codes=target_codes,
            since=effective_since,
            until=effective_until,
        )

        # 5) 按每个维度的 summary_fetch_strategy 过滤：
        #    all  -> 保留全部；last -> 每组取最新一条；first -> 每组取最老一条
        rows = cls._filter_rows_by_strategy(rows=rows, registry_map=registry_map)

        # 6) 逐条装配 + 统计 missing_codes
        #    注意：row.code 是 ORM 字段读取，保持不变；出参 dict 键名统一为 dimension_code
        summaries: List[Dict] = [
            {
                "db_type": row.db_type,
                "dimension_code": row.code,
                "name": registry_map[row.code].name if row.code in registry_map else row.code,
                "bk_biz_id": row.bk_biz_id,
                "cluster_domain": row.cluster_domain,
                "report_time": row.report_time,
                "summary": row.summary or "",
                "detail_url": row.detail_url or "",
                "score": row.score,
            }
            for row in rows
        ]

        hit_codes: set = {item["dimension_code"] for item in summaries}
        missing_codes: List[str] = [c for c in target_codes if c not in hit_codes]

        return {
            "status": "ok",
            "db_type": db_type,
            "bk_biz_id": bk_biz_id,
            "cluster_domain": cluster_domain,
            "cluster_created_at": cluster_created_at,
            "effective_since": effective_since,
            "effective_until": effective_until,
            "summaries": summaries,
            "missing_codes": missing_codes,
        }

    # ------------------------------------------------------------------
    # 私有辅助
    # ------------------------------------------------------------------

    @classmethod
    def resolve_cluster(cls, bk_biz_id: int, cluster_domain: str) -> Optional[Cluster]:
        """通过 (bk_biz_id, cluster_domain) 反查集群对象。

        设计要点 / 怎么做：
            - 数据源：``Cluster`` 表；按 ``bk_biz_id + immute_domain`` 唯一定位集群
            - 返回完整的 ``Cluster`` ORM 对象，让调用方按需取 ``cluster_type`` / ``create_at`` 等字段，
              避免为每个新字段都新增一个反查方法；也避免二次访问 DB
            - 找不到集群使用 ``.filter().first()`` 返回 ``None``（**不** 用 ``.get()``，避免 ``DoesNotExist``）

        作为 ``PortraitQueryService`` 的**公开工具方法**：读侧 ``discover_dimensions`` /
        ``fetch_summaries`` 与写侧 ``PortraitIngestService.ingest_summary`` 均依赖本方法反查，
        保持"集群 -> 元数据"的唯一事实源，避免调用方与集群元数据口径不一致。

        典型使用::

            cluster = PortraitQueryService.resolve_cluster(bk_biz_id, cluster_domain)
            if cluster is None:
                ...  # cluster_not_found
            db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
            created_at = cluster.create_at

        :param bk_biz_id: 业务 ID（正整数）
        :param cluster_domain: 集群不可变主域名（``immute_domain``）
        :return: ``Cluster`` ORM 对象；集群不存在或不属于该业务时返回 ``None``
        边界 / 异常：
            - 集群不存在或 bk_biz_id 不匹配 -> 返回 ``None``（不抛异常，由调用方按语义处理）
            - ORM 层不可预期异常 -> 原样抛出，由框架 500 兜底
        """
        return Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain=cluster_domain).first()

    @classmethod
    def _reconcile_time_range(
        cls,
        cluster_created_at: datetime,
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> Tuple[datetime, Optional[datetime], str]:
        """把用户传入的时间窗与集群创建时间合流，规避"上一代同域名集群"的脏数据。

        设计要点 / 怎么做：
            - ``immute_domain`` 存在被回收再分配的可能：即同一个域名早于当前集群 ``create_at``
              的巡检数据，大概率属于上一代同名集群，不应回给 Agent
            - 规则（从严到宽）：
                1. ``since`` 与 ``until`` 都存在，且 ``since > until``
                   -> ``invalid_time_range``；effective 值原样返回给出参回显
                2. ``until`` 存在且 ``until < cluster_created_at``
                   -> ``time_range_before_cluster_created``；整段都是脏数据
                3. ``since`` 缺失 或 ``since < cluster_created_at``
                   -> **静默上调** ``effective_since = cluster_created_at``；status=ok
                4. 其它 -> effective 值原样透传；status=ok

        :param cluster_created_at: 集群创建时间（``Cluster.create_at``，非空）
        :param since: 用户传入的时间下界（含）；可为 ``None``
        :param until: 用户传入的时间上界（含）；可为 ``None``
        :return: (effective_since, effective_until, status)
                 - effective_since: 服务端实际使用的下界（保证 >= cluster_created_at）
                 - effective_until: 服务端实际使用的上界（原样透传，可能为 None）
                 - status: 三种可能值："ok" / "invalid_time_range" / "time_range_before_cluster_created"
        边界 / 异常：
            - 本方法只做时间比较，不访问 DB，无副作用
            - ``cluster_created_at`` 必须为 ``datetime``（由调用方保证）
        """
        # 规则 1：显式非法区间；两者都存在时才判断
        if since is not None and until is not None and since > until:
            # effective_since 兜底为 cluster_created_at，避免把用户的非法值透传出去
            return max(since, cluster_created_at), until, "invalid_time_range"

        # 规则 2：用户区间完全早于集群创建时间
        if until is not None and until < cluster_created_at:
            return cluster_created_at, until, "time_range_before_cluster_created"

        # 规则 3：since 缺失 / since < cluster_created_at -> 静默上调
        if since is None or since < cluster_created_at:
            return cluster_created_at, until, "ok"

        # 规则 4：其它情况原样透传
        return since, until, "ok"

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
        :param since: 时间下界（含）；None 表示不限（fetch_summaries 层已保证不为 None）
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

    @classmethod
    def _filter_rows_by_strategy(
        cls,
        rows: List[PortraitDimensionSummary],
        registry_map: Dict[str, PortraitDimensionRegistry],
    ) -> List[PortraitDimensionSummary]:
        """依据每个维度的 ``summary_fetch_strategy`` 过滤时间窗内拉取到的摘要记录。

        前置条件：
            - ``rows`` 已按 ``(code 升序, report_time 升序, id 升序)`` 排序，保证同 ``code`` 的记录连续，
              从而 ``itertools.groupby`` 能正确分组；
            - 同 ``code`` 分组内，首条即"最老一条"、末条即"最新一条"（report_time 与 id 双升序兜底）。

        过滤规则：
            - ``all``（或 ``None`` / 未知值，兜底按 ``all`` 处理）：保留该维度全部记录
            - ``last`` ：只保留该维度最新一条记录
            - ``first``：只保留该维度最老一条记录

        :param rows: 时间窗内拉取到的全部摘要记录（已按 code 升序）
        :param registry_map: {code: registry_obj} 映射；策略取自 ``registry_obj.summary_fetch_strategy``
        :return: 过滤后的记录列表，顺序保持与原 ``rows`` 一致
        """
        filtered_rows: List[PortraitDimensionSummary] = []
        for _code, group_iter in groupby(rows, key=lambda r: r.code):
            code_rows: List[PortraitDimensionSummary] = list(group_iter)
            strategy: Optional[str] = getattr(registry_map.get(_code), "summary_fetch_strategy", None)
            strategy = strategy or SummaryFetchStrategy.ALL.value

            if strategy == SummaryFetchStrategy.LAST.value:
                filtered_rows.append(code_rows[-1])
            elif strategy == SummaryFetchStrategy.FIRST.value:
                filtered_rows.append(code_rows[0])
            else:  # ALL（含 None 兜底）
                filtered_rows.extend(code_rows)

        return filtered_rows
