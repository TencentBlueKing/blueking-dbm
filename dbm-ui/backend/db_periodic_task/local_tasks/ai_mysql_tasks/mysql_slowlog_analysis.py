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
import logging
from datetime import timedelta

from celery.schedules import crontab
from django.db.models import Count
from django.utils import timezone

from backend import env
from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.mysql_backup.check_ignore import CheckIgnore
from backend.db_report.enums import AiAnalysisSubType
from backend.db_report.models.mysql_slowlog_ai_analysis import MysqlSlowlogAiAnalysis
from backend.db_report.models.mysql_slowlog_detail import MysqlSlowlogDetail
from backend.dbm_aiagent.agent.commands.commands import MySQLSlowLogCommand

logger = logging.getLogger("root")

# 慢查询数量阈值，超过该值的集群才进入分析
SLOW_QUERY_COUNT_THRESHOLD = 10


@register_periodic_task(run_every=crontab(minute=0))
def periodic_mysql_slowlog_ai_analysis():
    """周期任务：从慢日志详情表中查询过去 1 小时内慢查询数量超过阈值的集群，进行 AI 分析"""
    if not env.ENABLE_DBM_AI:
        return

    from backend.dbm_aiagent.agent.handlers import AgentHandler

    now = timezone.now()
    time_window_start = now - timedelta(hours=1)
    time_window_end = now

    # 从慢日志详情表中查询过去 1 小时内有慢查询的集群，按 bk_biz_id, cluster_domain, cluster_type 分组
    # 仅慢查询数量超过阈值的集群才进入分析
    try:
        slow_clusters = (
            MysqlSlowlogDetail.objects.filter(
                dteventtimestamp__gt=time_window_start, dteventtimestamp__lte=time_window_end
            )
            .values("bk_biz_id", "cluster_domain", "cluster_type")
            .annotate(slow_count=Count("*"))
            .filter(slow_count__gt=SLOW_QUERY_COUNT_THRESHOLD)
        )
    except Exception as e:
        logger.exception(f"[mysql_slowlog_ai_analysis] query slow clusters failed: {e}")
        return
    logger.info(
        f"[mysql_slowlog_ai_analysis] start analysis, found {len(slow_clusters)} clusters "
        f"with slow queries > {SLOW_QUERY_COUNT_THRESHOLD} in the past 1 hour"
    )

    # 初始化忽略检查器
    ignore_checker = CheckIgnore(subtype=AiAnalysisSubType.SlowlogAnalysis)

    for cluster_info in slow_clusters:
        bk_biz_id = cluster_info["bk_biz_id"]
        cluster_domain = cluster_info["cluster_domain"]
        cluster_type = cluster_info["cluster_type"]
        try:
            # 检查是否需要跳过该集群
            if ignore_checker.should_ignore_check_cluster(bk_biz_id, cluster_domain, cluster_type):
                continue

            logger.info(
                f"[mysql_slowlog_ai_analysis] analyzing cluster: {cluster_domain} "
                f"(slow_count={cluster_info['slow_count']})"
            )

            if cluster_type == ClusterType.TenDBHA:
                instance_role = InstanceRole.BACKEND_MASTER.value
            else:
                instance_role = TenDBClusterSpiderRole.SPIDER_MASTER.value
            # 调用 AI Agent 进行慢查询分析
            result = AgentHandler.ask_agent_with_command(
                command=MySQLSlowLogCommand.command,
                command_params={
                    "cluster_domain": cluster_domain,
                    "cluster_type": cluster_type,
                    "instance_role": instance_role,
                    "time_window_start": time_window_start.replace(microsecond=0).isoformat(sep="T"),
                    "time_window_end": time_window_end.replace(microsecond=0).isoformat(sep="T"),
                    "limit": 10,
                },
            )

            if not result:
                logger.info(
                    f"[mysql_slowlog_ai_analysis] cluster {cluster_domain} " f"AI analysis returned no result, skipped"
                )
                continue

            # 将分析结果写入 MysqlSlowlogAiAnalysis 表
            MysqlSlowlogAiAnalysis.objects.create(
                bk_biz_id=bk_biz_id,
                cluster_type=cluster_type,
                cluster_domain=cluster_domain,
                instance_role=instance_role,
                time_window_start=time_window_start,
                time_window_end=time_window_end,
                instance="",
                analyze_time=now,
                analyze_result=result,
            )

            logger.info(f"[mysql_slowlog_ai_analysis] cluster {cluster_domain} analysis completed, result saved")

        except Exception as e:
            logger.exception(f"[mysql_slowlog_ai_analysis] cluster {cluster_domain} analysis failed: {e}")
            continue

    logger.info("[mysql_slowlog_ai_analysis] all clusters analysis completed")
