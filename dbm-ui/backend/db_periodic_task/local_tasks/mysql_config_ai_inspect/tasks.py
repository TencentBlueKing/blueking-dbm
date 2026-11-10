# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import json
import logging
import time
from datetime import datetime, timedelta

from blueapps.core.celery.celery import app
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.local_tasks import start_new_span
from backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.batch import ensure_open_batch
from backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.parse_result import parse_config_ai_inspect_res
from backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.scoring import (
    CATEGORIES,
    CHECK_STATUSES,
    REQUIRED_CHECKS,
    calculate_config_score,
)
from backend.db_report.models.mysql_config_ai_inspect import MysqlConfigAiInspect, MysqlConfigAiInspectStatus
from backend.db_report.portrait import MysqlPortraitDimensionCode, ingest_summary
from backend.db_report.portrait.exceptions import PortraitSDKBaseException
from backend.dbm_aiagent.agent.constants import DEFAULT_AGENT_CHAT_TIMEOUT, DBMAgentCode

logger = logging.getLogger("celery")

MAX_RETRY_COUNT = 3
# soft/hard 略高于 agent invoke_timeout，便于 finally 释放锁
WORKER_SOFT_TIME_LIMIT = DEFAULT_AGENT_CHAT_TIMEOUT + 60
WORKER_HARD_TIME_LIMIT = DEFAULT_AGENT_CHAT_TIMEOUT + 120
# 锁 TTL 覆盖 hard limit，避免 worker 存活期间锁过期
DISPATCH_LOCK_TTL = WORKER_HARD_TIME_LIMIT + 300
# 回收窗口贴近 agent 超时，与锁 TTL 解耦
STALE_RUNNING_SEC = DEFAULT_AGENT_CHAT_TIMEOUT + 120
BATCH_LEASE_TTL = 120

_OUTPUT_SCHEMA = json.dumps(
    {
        "report_id": "<uuid>",
        "share_url": "https://.../ai-chat/share/<uuid>/",
        "summary": "<text>",
        "checks": [{"code": code, "status": "<status>", "reason": "<evidence or reason>"} for code in REQUIRED_CHECKS],
        "findings": [
            {
                "issue_key": "<risk_type:sorted_parameters:role>",
                "category": "<category>",
                "parameters": ["<parameter_name>"],
                "scope": {"role": "<instance_role>", "instances": ["<ip:port>"]},
                "severity": "<high|medium|low>",
                "evidence": "<current values, baseline and runtime context>",
                "impact": "<risk and impact>",
            }
        ],
    }
)
_SCORING_REQUIREMENTS = _(
    "\n评分依据要求：不要自行输出分数，分数由后端计算。checks 必须完整包含所有核心检查项，不能遗漏。"
    "config_rationality 检查配置与规格、角色及资源使用是否匹配；config_consistency 检查主从、同角色或分片差异；"
    "version_compatibility 检查版本及引擎适配。每项 status 只能是 {}，reason 必须提供检查依据或无法检查的原因。"
    "completed 表示已完成检查，不代表没有问题；数据不足必须标记 insufficient_data，禁止推测为检查完成。"
    "仅 TenDBSingle 的 config_consistency 允许标记 not_applicable，并说明没有可比较实例的原因。"
    "findings 必须包含本次完整报告中全部有依据的独立问题，不能只取摘要中的部分问题；确实无问题时返回空列表。"
    "category 只能是 {}。severity 只能是 high、medium、low："
    "high 需要明确的数据可靠性、可用性或严重资源风险证据；medium 为明确的非紧急性能、稳定性或一致性问题；"
    "low 为有依据的轻量优化建议。不能仅凭参数偏离推荐值判高危，必须结合角色、版本、规格及已知业务要求。"
    "未知业务要求或无证据的推测写入报告待确认事项，不纳入扣分；合理的角色差异和业务取舍不算问题。"
    "同一根因、同一角色影响多个实例或分片应合并为一个问题，关联参数造成同一风险也应合并。"
    "issue_key 按风险类型、排序后的参数组、适用角色生成稳定标识，仅使用小写英文字母、数字和 _ . : + -，"
    "不得包含 IP、分片号等实例标识；不同角色的不同风险分别列出。"
    "scope.role 使用实例角色，scope.instances 列出受影响实例；evidence 和 impact 必须非空。"
    "详细建议存入报告，最终返回完整 JSON，不要因摘要字数限制截断 checks 或 findings。"
).format(", ".join(CHECK_STATUSES), ", ".join(CATEGORIES))


def _inspect_lock_key(batch_id: str, cluster_id: int) -> str:
    return f"mysql_config_ai_inspect:{batch_id}:{cluster_id}"


def _batch_lease_key(batch_id: str) -> str:
    return f"mysql_config_ai_inspect:batch_lease:{batch_id}"


def _release_inspect_lock(batch_id: str, cluster_id: int) -> None:
    try:
        cache.delete(_inspect_lock_key(batch_id, cluster_id))
    except Exception:  # noqa
        logger.warning(_("释放配置巡检锁失败: batch_id={} cluster_id={}").format(batch_id, cluster_id))


def reclaim_stale_running(batch_id: str) -> int:
    """回收超时仍停留在 running 的行，避免整批永久卡住。"""
    if not batch_id:
        return 0
    cutoff = timezone.now() - timedelta(seconds=STALE_RUNNING_SEC)
    stale_rows = list(
        MysqlConfigAiInspect.objects.filter(
            batch_id=batch_id,
            status=MysqlConfigAiInspectStatus.RUNNING.value,
            update_at__lt=cutoff,
        )
    )
    reclaimed = 0
    for row in stale_rows:
        if _mark_attempt_failed(row, _("执行超时或 Worker 丢失"), row.agent_cost_ms or 0):
            _release_inspect_lock(row.batch_id, row.cluster_id)
            reclaimed += 1
    if reclaimed:
        logger.warning(_("回收超时 running 行: batch_id={} count={}").format(batch_id, reclaimed))
    return reclaimed


def _mark_attempt_failed(row: MysqlConfigAiInspect, error_msg: str, cost_ms: int) -> bool:
    """仅当行仍为 RUNNING 时落失败/重试，避免覆盖并发 SUCCESS。"""
    retry_count = (row.retry_count or 0) + 1
    new_status = (
        MysqlConfigAiInspectStatus.FAILED.value
        if retry_count >= MAX_RETRY_COUNT
        else MysqlConfigAiInspectStatus.PENDING.value
    )
    updated = MysqlConfigAiInspect.objects.filter(id=row.id, status=MysqlConfigAiInspectStatus.RUNNING.value,).update(
        retry_count=retry_count,
        agent_cost_ms=cost_ms,
        error_msg=(error_msg or "")[:2000],
        status=new_status,
        updater="system",
        update_at=timezone.now(),
    )
    if not updated:
        logger.warning(_("配置巡检失败落库跳过(状态已变): id={} domain={}").format(row.id, row.cluster_domain))
        return False

    row.retry_count = retry_count
    row.agent_cost_ms = cost_ms
    row.error_msg = (error_msg or "")[:2000]
    row.status = new_status
    if new_status == MysqlConfigAiInspectStatus.FAILED.value:
        logger.warning(
            _("配置巡检失败达上限: id={} domain={} retry_count={} err={}").format(
                row.id, row.cluster_domain, row.retry_count, row.error_msg
            )
        )
    else:
        logger.warning(
            _("配置巡检失败将重试: id={} domain={} retry_count={} err={}").format(
                row.id, row.cluster_domain, row.retry_count, row.error_msg
            )
        )
    return True


# @register_periodic_task(run_every=crontab(minute="*/5"))
def periodic_mysql_config_ai_inspect():
    """每 5 分钟推进一批次中的一个集群配置 AI 巡检。"""
    if not env.ENABLE_DBM_AI:
        logger.warning(_("ai not enabled"))
        return

    batch_id = ensure_open_batch()
    if not batch_id:
        return

    reclaim_stale_running(batch_id)

    lease_key = _batch_lease_key(batch_id)
    try:
        got_lease = bool(cache.add(lease_key, 1, timeout=BATCH_LEASE_TTL))
    except Exception:  # noqa
        logger.warning(_("获取批次投递锁失败: batch_id={}").format(batch_id))
        return
    if not got_lease:
        logger.info(_("批次 {} 投递锁占用，本拍跳过").format(batch_id))
        return

    try:
        if MysqlConfigAiInspect.objects.filter(
            batch_id=batch_id, status=MysqlConfigAiInspectStatus.RUNNING.value
        ).exists():
            logger.info(_("批次 {} 存在执行中任务，本拍跳过投递").format(batch_id))
            return

        row = (
            MysqlConfigAiInspect.objects.filter(batch_id=batch_id, status=MysqlConfigAiInspectStatus.PENDING.value)
            .order_by("id")
            .first()
        )
        if not row:
            next_batch = ensure_open_batch()
            logger.info(_("批次 {} 已结批，下一批={}").format(batch_id, next_batch))
            return

        lock_key = _inspect_lock_key(row.batch_id, row.cluster_id)
        if not cache.add(lock_key, 1, timeout=DISPATCH_LOCK_TTL):
            logger.warning(_("配置巡检锁占用: lock_key={}").format(lock_key))
            return

        now = timezone.now()
        updated = MysqlConfigAiInspect.objects.filter(
            id=row.id, status=MysqlConfigAiInspectStatus.PENDING.value
        ).update(
            status=MysqlConfigAiInspectStatus.RUNNING.value,
            updater="system",
            update_at=now,
        )
        if not updated:
            cache.delete(lock_key)
            logger.warning(_("配置巡检行状态已变，取消投递: id={}").format(row.id))
            return

        try:
            with start_new_span(run_mysql_config_ai_inspect):
                run_mysql_config_ai_inspect.apply_async(args=[row.id, lock_key])
            logger.info(_("配置巡检已投递: id={} domain={} batch_id={}").format(row.id, row.cluster_domain, batch_id))
        except Exception:  # noqa
            MysqlConfigAiInspect.objects.filter(id=row.id).update(
                status=MysqlConfigAiInspectStatus.PENDING.value,
                updater="system",
                update_at=timezone.now(),
            )
            cache.delete(lock_key)
            logger.exception(_("配置巡检投递失败: id={}").format(row.id))
    finally:
        try:
            cache.delete(lease_key)
        except Exception:  # noqa
            logger.warning(_("释放批次投递锁失败: batch_id={}").format(batch_id))


@app.task(soft_time_limit=WORKER_SOFT_TIME_LIMIT, time_limit=WORKER_HARD_TIME_LIMIT)
def run_mysql_config_ai_inspect(row_id: int, lock_key: str):
    """单集群配置 AI 巡检 Worker。"""
    row = None
    try:
        row = MysqlConfigAiInspect.objects.get(id=row_id)
        content = (
            _(
                "bk_biz_id: {}, cluster_type: {}, cluster_id: {}, cluster_domain: {} "
                "对该集群做 MySQL 配置优化分析，完成后给我如下 JSON 格式结果（双引号键名）: "
            ).format(row.bk_biz_id, row.cluster_type, row.cluster_id, row.cluster_domain)
            + _OUTPUT_SCHEMA
            + _SCORING_REQUIREMENTS
        )

        logger.info(_("配置巡检开始调用 agent: id={} domain={}").format(row.id, row.cluster_domain))
        t_start = time.monotonic()
        try:
            from backend.dbm_aiagent.agent.handlers import AgentHandler

            res = AgentHandler.ask_agent_with_content(
                agent_code=DBMAgentCode.MYSQL_CONFIG_PERF_TUNER,
                content=str(content),
                timeout=DEFAULT_AGENT_CHAT_TIMEOUT,
            )
        except Exception as exc:  # noqa
            cost_ms = int((time.monotonic() - t_start) * 1000)
            _mark_attempt_failed(row, str(exc), cost_ms)
            return

        cost_ms = int((time.monotonic() - t_start) * 1000)
        parsed = parse_config_ai_inspect_res(res if isinstance(res, str) else "")
        if not parsed:
            _mark_attempt_failed(row, _("解析 agent 结果失败"), cost_ms)
            logger.warning(
                _("配置巡检解析失败: id={} domain={} cost_ms={} res={}").format(
                    row.id, row.cluster_domain, cost_ms, str(res)[:500]
                )
            )
            return

        score, score_detail = calculate_config_score(parsed, row.cluster_type)
        if score is None:
            logger.warning(
                _("配置巡检评分不可用: id={} domain={} reasons={}").format(row.id, row.cluster_domain, score_detail["errors"])
            )
        updated = MysqlConfigAiInspect.objects.filter(
            id=row.id,
            status=MysqlConfigAiInspectStatus.RUNNING.value,
        ).update(
            status=MysqlConfigAiInspectStatus.SUCCESS.value,
            report_id=parsed["report_id"],
            share_url=parsed["share_url"],
            summary=parsed.get("summary") or "",
            score=score,
            score_detail=score_detail,
            agent_cost_ms=cost_ms,
            error_msg="",
            updater="system",
            update_at=timezone.now(),
        )
        if not updated:
            logger.warning(_("配置巡检成功落库跳过(状态已变): id={} domain={}").format(row.id, row.cluster_domain))
            return

        row.status = MysqlConfigAiInspectStatus.SUCCESS.value
        row.report_id = parsed["report_id"]
        row.share_url = parsed["share_url"]
        row.summary = parsed.get("summary") or ""
        row.score = score
        row.score_detail = score_detail
        row.agent_cost_ms = cost_ms
        logger.info(
            _("配置巡检成功: id={} domain={} cost_ms={} report_id={}").format(
                row.id, row.cluster_domain, cost_ms, row.report_id
            )
        )
        try:
            ingest_summary(
                db_type=DBType.TenDBCluster if row.cluster_type == ClusterType.TenDBCluster else DBType.MySQL,
                dimension=MysqlPortraitDimensionCode.CONFIG_CHECK,
                bk_biz_id=row.bk_biz_id,
                cluster_domain=row.cluster_domain,
                report_time=datetime.now(),
                summary=row.summary or "",
                detail_url=row.share_url,
                score=row.score,
            )
        except PortraitSDKBaseException:
            logger.exception(_("配置巡检上报画像失败: id={} domain={}").format(row.id, row.cluster_domain))
        except Exception:  # noqa
            logger.exception(_("配置巡检上报画像异常: id={} domain={}").format(row.id, row.cluster_domain))
    except MysqlConfigAiInspect.DoesNotExist:
        logger.warning(_("配置巡检行不存在: id={}").format(row_id))
    except Exception:  # noqa
        logger.exception(_("配置巡检 Worker 异常: id={}").format(row_id))
        if row is not None:
            try:
                _mark_attempt_failed(row, _("Worker 内部异常"), row.agent_cost_ms or 0)
            except Exception:  # noqa
                logger.exception(_("配置巡检失败落库异常: id={}").format(row_id))
    finally:
        try:
            cache.delete(lock_key)
        except Exception:  # noqa
            logger.warning(_("释放配置巡检锁失败: lock_key={}").format(lock_key))
