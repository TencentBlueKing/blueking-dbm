# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

init_flow_node_baseline Django Command：flow 节点耗时基线的存量初始化 / 定点修复入口。

模块职责：
  - 存量初始化：按 ticket_types 范围重建 FlowNodeDurationBaseline（业务级 + 全局基线一起重建）
  - 定点修复：--repair 模式下强制要求 (bk_biz_ids × ticket_types) 非空，仅修复业务级基线（不动全局）
  - 只做参数解析 + 调用 FlowBaselineService；不含任何业务逻辑

设计约束（重要）：
  - rebuild 模式**不允许**按 --bk-biz-id 过滤：全局基线（bk_biz_id=0）是"所有业务合体"口径，
    若只重建部分业务会导致全局基线口径失真。全量业务样本一起聚合是保证全局基线正确的前提。
  - --bk-biz-id 只在 --repair 模式下生效，用于定点修复业务级基线（不涉及全局基线重建）。

使用示例：
  # 全量重建所有 ticket_type（谨慎，样本量大）
  python manage.py init_flow_node_baseline

  # 只重建指定单据类型（推荐做法：一次一个 ticket_type）
  python manage.py init_flow_node_baseline --ticket-type MYSQL_PARTITION_V2

  # 一次重建多个 ticket_type
  python manage.py init_flow_node_baseline --ticket-type MYSQL_PARTITION_V2 --ticket-type SQLSERVER_IMPORT_SQLFILE

  # 指定时间窗
  python manage.py init_flow_node_baseline --since 2026-01-01 --until 2026-06-30

  # 只统计不写库（做容量评估）
  python manage.py init_flow_node_baseline --dry-run

  # 定点修复业务级基线（bk-biz-id 与 ticket-type 必填；不重建全局基线 bk_biz_id=0）
  python manage.py init_flow_node_baseline --repair --bk-biz-id 591 --ticket-type MYSQL_PARTITION_V2

  # 覆盖默认回溯天数（配合 --since 二选一）
  python manage.py init_flow_node_baseline --lookback-days 30

LLM 调用运维预期（首次跑存量前必读）：
  - 存量初始化会通过 NameNormalizer 按需调用 LLM 做名称归一化；调用**仅**发生在
    "新 cleaned_name 且同 (ticket_type, component_code) 下已有归一化类别"的场景。
  - 单次 LLM 调用最坏耗时约 40s（timeout=20s × 重试 2 次），正常 1~5s；
    单分片 LLM 调用数上限受 CATEGORIES_HARD_LIMIT=100 熔断，超限直接抛异常。
  - _do_rebuild 单线程串行执行，LLM 调用天然被串行化，不会打爆上游；
    但总耗时线性增长于 LLM 调用次数——**大规模存量首跑建议按 --ticket-type 分批**。
  - 强烈建议流程：先 --dry-run 做容量评估 → 再挑单个 --ticket-type 小范围跑 → 观察
    FlowNodeNameAlias.needs_review 归一化质量 → 无问题后再扩大范围。
  - 第二次及以后运行几乎不再调 LLM（alias 表命中），耗时主要在样本聚合与 DB 读写。
  - 上游 LLM 抖动会走 LLM_FALLBACK 路径（normalized_name=cleaned_name + needs_review=True），
    不阻塞 rebuild；事后可筛选 needs_review=True 的记录人工核对。
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_services.flow_node_baseline.baseline_service import BaselineRunSummary, FlowBaselineService

logger = logging.getLogger("root")


class Command(BaseCommand):
    """flow 节点耗时基线存量/修复 Django Command。

    职责：
      - 解析命令行参数（时间窗、biz、ticket_type、模式、dry_run 等）
      - 校验参数合法性：
          * --repair 强制要求 --bk-biz-id 与 --ticket-type 非空
          * 非 --repair（rebuild）模式禁止使用 --bk-biz-id（避免污染全局基线）
      - 委托给 FlowBaselineService.rebuild() 或 .repair()
      - 打印结构化运行摘要，供人工审阅与日志留痕

    使用方式：
      python manage.py init_flow_node_baseline [OPTIONS]

    线程安全：Django Command 单进程执行，不涉及并发
    副作用：
      - 触发对 FlowNodeDurationBaseline / FlowNodeNameAlias / FlowNodeBaselineWatermark 的读写
      - 触发对 LLM 的调用（NameNormalizer 内部按需调用）
    边界：
      - --repair 且未指定 --bk-biz-id 或 --ticket-type → 抛 CommandError
      - 非 --repair 模式使用 --bk-biz-id → 抛 CommandError
      - --since 与 --lookback-days 都指定 → 优先使用 --since，忽略 --lookback-days
      - --since / --until 格式非法 → 抛 CommandError
    """

    help = _(
        "flow 节点耗时基线存量初始化 / 定点修复入口。" "rebuild 模式仅支持 --ticket-type 过滤（保证全局基线口径正确）；" "--bk-biz-id 仅在 --repair 模式下生效。"
    )

    #: 时间字符串支持的输入格式；按顺序尝试解析
    _DATE_INPUT_FORMATS: List[str] = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    def add_arguments(self, parser: CommandParser) -> None:
        """注册命令行参数。"""
        parser.add_argument(
            "--bk-biz-id",
            dest="bk_biz_ids",
            type=int,
            action="append",
            default=None,
            help=_(
                "要处理的业务 ID；**仅在 --repair 模式下生效**，可重复传入指定多个"
                "（--bk-biz-id 591 --bk-biz-id 105）。"
                "rebuild 模式禁止使用此参数：全局基线 bk_biz_id=0 是所有业务合体口径，"
                "只重建部分业务会导致全局基线失真。"
            ),
        )
        parser.add_argument(
            "--ticket-type",
            dest="ticket_types",
            type=str,
            action="append",
            default=None,
            help=_("要处理的单据类型；可重复传入指定多个（--ticket-type MYSQL_PARTITION_V2 ...），不传表示全部"),
        )
        parser.add_argument(
            "--since",
            dest="since",
            type=str,
            default=None,
            help=_("时间窗起点，支持 'YYYY-MM-DD HH:MM:SS' / 'YYYY-MM-DD' 等格式；与 --lookback-days 二选一"),
        )
        parser.add_argument(
            "--until",
            dest="until",
            type=str,
            default=None,
            help=_("时间窗终点，格式同 --since；不传默认使用当前时间"),
        )
        parser.add_argument(
            "--lookback-days",
            dest="lookback_days",
            type=int,
            default=None,
            help=_("回溯天数；与 --since 互斥，若同时指定优先 --since"),
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            default=False,
            help=_("只统计不写库；用于容量评估或参数试跑"),
        )
        parser.add_argument(
            "--repair",
            dest="repair",
            action="store_true",
            default=False,
            help=_("定点修复模式；此模式下 --bk-biz-id 与 --ticket-type 必填，仅重建业务级基线，不动全局基线"),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Command 入口：解析参数 → 校验 → 委托 Service → 打印摘要。"""
        bk_biz_ids: Optional[List[int]] = self._normalize_int_list(options.get("bk_biz_ids"))
        ticket_types: Optional[List[str]] = self._normalize_str_list(options.get("ticket_types"))
        since: Optional[datetime] = self._parse_datetime(options.get("since"), field_name="--since")
        until: Optional[datetime] = self._parse_datetime(options.get("until"), field_name="--until")
        lookback_days: Optional[int] = options.get("lookback_days")
        dry_run: bool = bool(options.get("dry_run"))
        repair: bool = bool(options.get("repair"))

        # since 优先于 lookback_days
        if since is None and lookback_days is not None:
            if lookback_days <= 0:
                raise CommandError("--lookback-days must be > 0")
            since = timezone.now() - timedelta(days=lookback_days)

        # 时间窗合法性校验
        if since is not None and until is not None and since >= until:
            raise CommandError(f"invalid time range: since={since} must be < until={until}")

        # rebuild 模式禁止 --bk-biz-id：避免只重建部分业务导致全局基线口径失真
        if not repair and bk_biz_ids:
            raise CommandError(
                "--bk-biz-id is only allowed under --repair mode. "
                "rebuild must cover all businesses to keep the global baseline (bk_biz_id=0) consistent. "
                "If you really want to fix a specific business, use "
                "'--repair --bk-biz-id X --ticket-type Y' instead."
            )

        service: FlowBaselineService = FlowBaselineService()

        try:
            if repair:
                # 定点修复：强制要求非空过滤范围
                if not bk_biz_ids:
                    raise CommandError("--repair mode requires at least one --bk-biz-id")
                if not ticket_types:
                    raise CommandError("--repair mode requires at least one --ticket-type")
                self.stdout.write(
                    self.style.WARNING(
                        f"[REPAIR] bk_biz_ids={bk_biz_ids} ticket_types={ticket_types} "
                        f"since={since} until={until} (business-level only, global baseline untouched)"
                    )
                )
                summary: BaselineRunSummary = service.repair(
                    bk_biz_ids=bk_biz_ids,
                    ticket_types=ticket_types,
                    since=since,
                    until=until,
                )
            else:
                # 全量或按 ticket_type 范围重建；不接受 --bk-biz-id
                self.stdout.write(
                    self.style.WARNING(
                        f"[REBUILD] ticket_types={ticket_types or 'ALL'} "
                        f"since={since or 'default'} until={until or 'now'} dry_run={dry_run}"
                    )
                )
                summary = service.rebuild(
                    ticket_types=ticket_types,
                    since=since,
                    until=until,
                    dry_run=dry_run,
                )
        except CommandError:
            raise
        except Exception as err:
            logger.exception("[init_flow_node_baseline] unexpected error: %s", err)
            raise CommandError(f"unexpected error: {err}") from err

        self._print_summary(summary)

    # =========================================================================
    # 私有辅助
    # =========================================================================

    @staticmethod
    def _normalize_int_list(value: Optional[List[int]]) -> Optional[List[int]]:
        """将 argparse action='append' 的可空 list 规整为 None 或去重后的 list。"""
        if not value:
            return None
        return sorted({int(v) for v in value})

    @staticmethod
    def _normalize_str_list(value: Optional[List[str]]) -> Optional[List[str]]:
        """将 argparse action='append' 的可空 list 规整为 None 或去重去空后的 list。"""
        if not value:
            return None
        return sorted({v.strip() for v in value if v and v.strip()})

    def _parse_datetime(self, raw: Optional[str], field_name: str) -> Optional[datetime]:
        """按 _DATE_INPUT_FORMATS 尝试解析用户输入；失败抛 CommandError。

        :param raw: 命令行原始字符串；None 或空串直接返回 None
        :param field_name: 字段名（用于错误信息）
        :return: aware datetime（tzinfo 使用 Django 当前时区）
        边界：
          - None / 空字符串 → 返回 None
          - 无法匹配任一格式 → 抛 CommandError
        """
        if raw is None:
            return None
        text: str = str(raw).strip()
        if not text:
            return None

        for fmt in self._DATE_INPUT_FORMATS:
            try:
                naive: datetime = datetime.strptime(text, fmt)
                # 转为 aware datetime，避免 Django 时区警告
                return timezone.make_aware(naive, timezone=timezone.get_current_timezone())
            except ValueError:
                continue

        raise CommandError(f"{field_name} format invalid: {raw!r}; supported formats: {self._DATE_INPUT_FORMATS}")

    def _print_summary(self, summary: BaselineRunSummary) -> None:
        """把运行摘要以人类可读格式打印到 stdout。"""
        data: Dict = summary.as_dict()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS(_("  flow_node_baseline 运行摘要")))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"  mode                  : {data['mode']}")
        self.stdout.write(f"  since                 : {data['since']}")
        self.stdout.write(f"  until                 : {data['until']}")
        self.stdout.write(f"  shards_processed      : {data['shards_processed']}")
        self.stdout.write(f"  samples_collected     : {data['samples_collected']}")
        self.stdout.write(f"  samples_accumulated   : {data['samples_accumulated']}")
        self.stdout.write(f"  buckets_written       : {data['buckets_written']}")
        self.stdout.write(f"  failure_count         : {data['failure_count']}")

        if data["failures"]:
            self.stdout.write(self.style.WARNING("  failures (top 20):"))
            for line in data["failures"]:
                self.stdout.write(f"    - {line}")

        self.stdout.write(self.style.SUCCESS("=" * 70))
