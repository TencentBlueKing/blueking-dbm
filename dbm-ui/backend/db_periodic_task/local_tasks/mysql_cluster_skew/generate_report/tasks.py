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
import re
import time
from datetime import timedelta
from datetime import timezone as dt_timezone

from blueapps.core.celery.celery import app
from celery.schedules import crontab
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from backend import env
from backend.constants import DEFAULT_TIME_ZONE_AREA
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks import register_periodic_task, start_new_span
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown
from backend.db_report.models.cluster_skew_detection import ClusterSkewDetection
from backend.db_report.models.mysql_cluster_skew_report import MysqlClusterSkewReport
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.agent.handlers import AgentHandler
from backend.dbm_aiagent.mcp_tools.mysql.impl.query_cluster_skew_data import has_cluster_skew

logger = logging.getLogger("celery.generate_mysql_skew_report")

_SKEW_REPORT_RESULT_SCHEMA = {
    "type": "object",
    "required": ["summary", "share_url"],
    "properties": {
        "summary": {"type": "string", "description": "内容摘要"},
        "share_url": {"type": "string", "description": "报告链接"},
    },
}

_SKEW_REPORT_SHARE_URL_RE = re.compile(
    rf"{re.escape(env.BK_SAAS_HOST.rstrip('/'))}/ai-chat/share/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/?",
    re.IGNORECASE,
)


def _localize_time(dt_utc):
    local_dt = timezone.localtime(dt_utc.replace(tzinfo=dt_timezone.utc))
    return f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} {DEFAULT_TIME_ZONE_AREA}"


def _parse_skew_report_res(res: str):
    try:
        report = json.loads(res)
        validate(instance=report, schema=_SKEW_REPORT_RESULT_SCHEMA)
        return report
    except (json.JSONDecodeError, ValidationError):
        pass

    match = _SKEW_REPORT_SHARE_URL_RE.search(res)
    if not match:
        return None

    share_url = f"{env.BK_SAAS_HOST.rstrip('/')}/ai-chat/share/{match.group(1)}/"
    summary = (res[: match.start()] + res[match.end() :]).strip()
    return {"summary": summary, "share_url": share_url}


@register_periodic_task(run_every=crontab(minute=3, hour=2))
def generate_report():
    if not env.ENABLE_DBM_AI:
        logger.warning("ai not enabled")
        return

    try:
        ClusterSkewDetection.objects.using("doris").exists()
    except Exception:  # noqa
        logger.warning("dispatch skip, doris unavailable")
        return

    cluster_objs = Cluster.objects.filter(cluster_type__in=[ClusterType.TenDBHA, ClusterType.TenDBCluster])
    cluster_count = cluster_objs.count()

    scheduled, skipped_lock = 0, 0

    for index, cluster_obj in enumerate(cluster_objs):
        lock_key = f"generate_mysql_skew_report:{cluster_obj.immute_domain}"

        if not cache.add(lock_key, 1, timeout=3600 * 13):
            skipped_lock += 1
            logger.warning("report skip, lock held: lock_key=%s", lock_key)
            continue

        countdown = calculate_countdown(count=cluster_count, index=index, duration=12 * TimeUnit.HOUR)

        try:
            with start_new_span(_generate_cluster_skew_report):
                _generate_cluster_skew_report.apply_async(
                    args=[
                        cluster_obj.cluster_type,
                        cluster_obj.immute_domain,
                        lock_key,
                        cluster_obj.bk_biz_id,
                    ],
                    countdown=countdown,
                )
            scheduled += 1
            logger.info(
                "report scheduled: lock_key=%s cluster_domain=%s countdown=%ds",
                lock_key,
                cluster_obj.immute_domain,
                countdown,
            )
        except Exception:  # noqa
            logger.exception("report schedule failed: lock_key=%s", lock_key)
            cache.delete(lock_key)

    logger.info(
        "dispatch done: scheduled=%d skipped_lock=%d total=%d",
        scheduled,
        skipped_lock,
        cluster_count,
    )


@app.task
def _generate_cluster_skew_report(cluster_type: str, domain: str, lock_key: str, bk_biz_id: int):
    logger.info("generate %s skew report start: lock_key=%s", domain, lock_key)
    try:
        # UTC naive，与 Doris detect_time 一致，用于查询和落库
        report_to_utc = timezone.now().replace(tzinfo=None)
        report_from_utc = report_to_utc - timedelta(hours=24)
        report_from_utc -= timedelta(hours=1)
        report_to_utc += timedelta(hours=1)

        cluster_obj = Cluster.objects.get(immute_domain=domain, cluster_type=cluster_type)
        if not has_cluster_skew(cluster_obj, report_from_utc, report_to_utc):
            logger.info("generate %s skew report skip, no skew: lock_key=%s", domain, lock_key)
            return

        report_from_str = _localize_time(report_from_utc)
        report_to_str = _localize_time(report_to_utc)
        t_start = time.monotonic()
        res = AgentHandler.ask_agent_with_content(
            agent_code=DBMAgentCode.MYSQL_WORKBENCH,
            content=str(
                _("{} 生成从 {} 到 {} 的集群倾斜报告, 给我 {{'summary':<内容摘要>, 'share_url':<报告链接>}} 格式的结果").format(
                    domain, report_from_str, report_to_str
                )
            ),
            timeout=300,
        )
        t_done = time.monotonic()
        report = _parse_skew_report_res(res)
        if report:
            logger.info(
                "generate %s skew report done: lock_key=%s used_time=%.2fs summary=%s share_url=%s",
                domain,
                lock_key,
                t_done - t_start,
                report["summary"],
                report["share_url"],
            )
            try:
                MysqlClusterSkewReport.objects.create(
                    bk_biz_id=bk_biz_id,
                    cluster_type=cluster_type,
                    cluster_domain=domain,
                    report_from=report_from_utc,
                    report_to=report_to_utc,
                    summary=report["summary"],
                    share_url=report["share_url"],
                    creator="system",
                    updater="system",
                )
            except Exception:  # noqa
                logger.exception("generate %s skew report save failed: lock_key=%s", domain, lock_key)
        else:
            logger.warning(
                "generate %s skew report parse failed: lock_key=%s used_time=%.2fs res=%s",
                domain,
                lock_key,
                t_done - t_start,
                res,
            )
    except Exception:  # noqa
        logger.exception("generate %s skew report failed: lock_key=%s", domain, lock_key)
    finally:
        if cache.get(lock_key) == 1:
            cache.delete(lock_key)
