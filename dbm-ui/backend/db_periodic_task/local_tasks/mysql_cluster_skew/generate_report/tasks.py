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
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from datetime import timezone as dt_timezone

from blueapps.core.celery.celery import app
from celery.schedules import crontab
from django.core.cache import cache
from django.db.models.functions import Mod
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from backend import env
from backend.configuration.constants import DBType
from backend.constants import DEFAULT_TIME_ZONE_AREA
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks import register_periodic_task, start_new_span
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown
from backend.db_report.models.cluster_skew_detection import ClusterSkewDetection
from backend.db_report.models.mysql_cluster_skew_report import MysqlClusterSkewReport
from backend.db_report.portrait import MysqlPortraitDimensionCode, ingest_summary
from backend.db_report.portrait.exceptions import PortraitSDKBaseException

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


@register_periodic_task(run_every=crontab(minute=3, hour="1,2,3"))
def generate_report():
    """分发 MySQL 集群倾斜报告生成任务。

    调度策略：
    1. 分片：凌晨 1, 2, 3 每小时触发，cluster_id % 3 == 当前小时，每个集群每天只调度一次。
    2. 错峰：countdown 平摊到 30 分钟内，避免瞬时打满 AI；窗口须短于 Redis broker
       visibility_timeout（默认 1h），否则 countdown 任务会被重复投递。
    3. 防重调度：投递前 cache.add 占位，避免同集群同一天重复 apply_async（如 Beat 重复触发）。
       - key 带 schedule_date：「是否已调度」由日期区分，次日自动换新 key，不必把 TTL 绑成 24h 业务周期。
       - TTL 25h：只负责回收 cache 条目；防重语义在 key，不在 TTL 时长。不主动 delete，任务结束也不释锁。
    """
    if not env.ENABLE_DBM_AI:
        logger.warning("ai not enabled")
        return

    try:
        ClusterSkewDetection.objects.using("doris").exists()
    except Exception:  # noqa
        logger.warning("dispatch skip, doris unavailable")
        return

    current_hour = timezone.localtime().hour
    schedule_date = timezone.localdate()
    logger.info(
        "dispatch start: schedule_date=%s current_hour=%d",
        schedule_date,
        current_hour,
    )

    cluster_objs = (
        Cluster.objects.filter(cluster_type__in=[ClusterType.TenDBHA, ClusterType.TenDBCluster])
        .annotate(id_mod_hour=Mod("id", 3))
        .filter(id_mod_hour=current_hour)
    )
    cluster_count = cluster_objs.count()
    logger.info(
        "dispatch batch: cluster_count=%d cluster_id_mod_3=%d",
        cluster_count,
        current_hour,
    )

    scheduled, skipped_lock = 0, 0

    for index, cluster_obj in enumerate(cluster_objs):
        lock_key = f"generate_mysql_skew_report:{cluster_obj.immute_domain}:{schedule_date}"

        # 25h TTL：略长于 1 天，仅清理过期 key；是否与 24h 报告 span 无关
        if not cache.add(lock_key, 1, timeout=3600 * 25):
            skipped_lock += 1
            logger.warning("report skip, lock held: lock_key=%s", lock_key)
            continue

        countdown = calculate_countdown(count=cluster_count, index=index, duration=30 * TimeUnit.MINUTE)

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

    logger.info(
        "dispatch done: scheduled=%d skipped_lock=%d total=%d",
        scheduled,
        skipped_lock,
        cluster_count,
    )


@app.task
def _generate_cluster_skew_report(cluster_type: str, domain: str, lock_key: str, bk_biz_id: int):
    from backend.dbm_aiagent.agent.constants import DBMAgentCode
    from backend.dbm_aiagent.agent.handlers import AgentHandler
    from backend.dbm_aiagent.mcp_tools.mysql.impl.query_cluster_skew_data import has_cluster_skew

    logger.info("generate %s skew report start: lock_key=%s", domain, lock_key)
    try:
        # 本地墙钟时间，不带时区，与 Doris detect_time、倾斜检测写入方式一致
        local_today = timezone.localdate()
        report_to_utc = datetime.combine(local_today, dt_time.min)
        report_from_utc = report_to_utc - timedelta(days=1)
        logger.info(
            "generate %s skew report period: lock_key=%s report_from=%s report_to=%s",
            domain,
            lock_key,
            report_from_utc,
            report_to_utc,
        )

        cluster_obj = Cluster.objects.get(immute_domain=domain, cluster_type=cluster_type)
        if not has_cluster_skew(cluster_obj, report_from_utc, report_to_utc):
            logger.info(
                "generate %s skew report skip, no skew: lock_key=%s report_from=%s report_to=%s",
                domain,
                lock_key,
                report_from_utc,
                report_to_utc,
            )
            return

        report_from_str = f"{report_from_utc.strftime('%Y-%m-%d %H:%M:%S')} {DEFAULT_TIME_ZONE_AREA}"
        report_to_str = f"{report_to_utc.strftime('%Y-%m-%d %H:%M:%S')} {DEFAULT_TIME_ZONE_AREA}"

        try:
            report_obj = MysqlClusterSkewReport.objects.create(
                bk_biz_id=bk_biz_id,
                cluster_type=cluster_type,
                cluster_domain=domain,
                report_from=report_from_utc,
                report_to=report_to_utc,
                summary="",
                share_url="",
                creator="system",
                updater="system",
            )
            logger.info(
                "generate %s skew report placeholder created: lock_key=%s id=%s",
                domain,
                lock_key,
                report_obj.id,
            )
        except Exception:  # noqa
            logger.exception("generate %s skew report placeholder create failed: lock_key=%s", domain, lock_key)
            return

        logger.info("generate %s skew report calling agent: lock_key=%s id=%s", domain, lock_key, report_obj.id)
        t_start = time.monotonic()
        res = AgentHandler.ask_agent_with_content(
            agent_code=DBMAgentCode.MYSQL_SKEW_REPORT,
            content=str(
                _(
                    "bk_biz_id: {}, cluster_type:{}, cluster_domain: {} "
                    "生成从 {} 到 {} 的集群倾斜报告, 给我 {{'summary':<内容摘要>, 'share_url':<报告链接>}} 格式的结果"
                ).format(cluster_obj.bk_biz_id, cluster_obj.cluster_type, domain, report_from_str, report_to_str)
            ),
            timeout=300,
        )
        t_done = time.monotonic()
        logger.info(
            "generate %s skew report agent returned: lock_key=%s used_time=%.2fs",
            domain,
            lock_key,
            t_done - t_start,
        )
        report = _parse_skew_report_res(res)
        if report:
            logger.info(
                "generate %s skew report done: lock_key=%s id=%s used_time=%.2fs summary=%s share_url=%s",
                domain,
                lock_key,
                report_obj.id,
                t_done - t_start,
                report["summary"],
                report["share_url"],
            )
            try:
                report_obj.summary = report["summary"]
                report_obj.share_url = report["share_url"]
                report_obj.updater = "system"
                report_obj.save(update_fields=["summary", "share_url", "updater", "update_at"])
                logger.info(
                    "generate %s skew report updated: lock_key=%s id=%s",
                    domain,
                    lock_key,
                    report_obj.id,
                )

                ingest_summary(
                    db_type=DBType.TenDBCluster
                    if cluster_obj.cluster_type == ClusterType.TenDBCluster
                    else DBType.MySQL,
                    dimension=MysqlPortraitDimensionCode.CLUSTER_SKEW,
                    bk_biz_id=cluster_obj.bk_biz_id,
                    cluster_domain=cluster_obj.immute_domain,
                    report_time=datetime.now(),
                    summary=report_obj.summary,
                    detail_url=report_obj.share_url,
                )
            except PortraitSDKBaseException:
                logger.exception(f"report {cluster_obj.immute_domain} skew to portrait failed")
            except Exception:  # noqa
                logger.exception(
                    "generate %s skew report update failed: lock_key=%s id=%s",
                    domain,
                    lock_key,
                    report_obj.id,
                )
        else:
            logger.warning(
                "generate %s skew report parse failed: lock_key=%s id=%s used_time=%.2fs res=%s",
                domain,
                lock_key,
                report_obj.id,
                t_done - t_start,
                res,
            )
    except Exception:  # noqa
        logger.exception("generate %s skew report failed: lock_key=%s", domain, lock_key)
