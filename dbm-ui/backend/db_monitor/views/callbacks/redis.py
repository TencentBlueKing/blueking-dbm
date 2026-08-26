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

from celery import shared_task
from django.core.cache import cache
from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_monitor.views.callbacks.base import AlarmCallback
from backend.db_services.redis.autofix.message import send_msg_2_qywx
from backend.dbm_aiagent.agent.commands.commands import (
    RedisLatencyAlarmRootCauseCommand,
    RedisPersistAnomalyRootCauseCommand,
    RedisSingleCpuHighRootCauseCommand,
)

logger = logging.getLogger("root")

# 关联分析的时间窗口（秒），拉取最近 10 分钟内的同类活跃告警
CORRELATION_TIME_WINDOW = 600
# 同策略去重锁 TTL（秒），窗口内只触发一次分析，避免多集群同时告警重复推送
DEDUP_LOCK_TTL = 300


class RedisAlarm(AlarmCallback):
    """Redis 告警回调处理器"""

    # 处理函数 -> 匹配条件列表的映射
    # level: 0-致命, 1-预警, 2-提醒
    STRATEGY_HANDLERS = {
        "call_redis_alarm_correlation_analysis": [
            {
                "keyword": "耗时",
                "level": [0],
                "cluster_type": [],
            },
        ],
        "call_redis_persist_anomaly_analysis": [
            {
                "keyword": "Persist异常",
                "level": [0],
                "cluster_type": [],
            },
        ],
        "call_redis_single_cpu_high_analysis": [
            {
                "keyword": "单核CPU使用率",
                "level": [0],
                "cluster_type": [],
            },
        ],
    }

    @classmethod
    def callback(cls, callback_data: dict):
        """根据策略名、告警级别分发到对应的异步处理任务"""
        callback_message = callback_data.get("callback_message", {})
        strategy_name = callback_message.get("strategy", {}).get("name", "")
        event_level = callback_message.get("event", {}).get("level")

        dimensions = callback_message.get("event", {}).get("dimensions", {})
        cluster_domain = dimensions.get("cluster_domain", "")
        cluster_type = dimensions.get("cluster_type", "")
        bk_biz_id = int(dimensions.get("appid", 0))

        if (not cluster_type or not bk_biz_id) and cluster_domain:
            cluster = Cluster.objects.filter(immute_domain=cluster_domain).first()
            cluster_type = cluster.cluster_type if cluster else None
            bk_biz_id = cluster.bk_biz_id if cluster else bk_biz_id

        alarm_base_info = {
            "bk_biz_id": bk_biz_id,
            "cluster_type": cluster_type,
            "cluster_domain": cluster_domain,
            "dimensions": dimensions,
            "strategy_name": strategy_name,
            "level": event_level,
            "appointees": callback_data.get("appointees", []),
        }

        for handler_name, conditions in cls.STRATEGY_HANDLERS.items():
            for condition in conditions:
                if condition["keyword"] == "" or condition["keyword"] not in strategy_name:
                    continue
                level_list = condition.get("level", [])
                if level_list and event_level is not None and event_level not in level_list:
                    continue
                cluster_type_list = condition.get("cluster_type", [])
                if cluster_type_list and cluster_type and cluster_type not in cluster_type_list:
                    continue

                handler = globals().get(handler_name)
                if handler:
                    handler.delay(callback_data, alarm_base_info)
                    logger.info(
                        _("[RedisAlarm] 策略 '{}' (level={}, cluster_type={}) 分发到异步任务: {}").format(
                            strategy_name, event_level, cluster_type, handler_name
                        )
                    )
                else:
                    logger.warning(_("[RedisAlarm] 未找到处理函数: {}").format(handler_name))
                return


@shared_task
def call_redis_alarm_correlation_analysis(callback_data: dict, alarm_base_info: dict):
    """
    异步任务：L0 延迟告警触发跨集群关联性分析。
    拉取同策略名的全量活跃告警，交给 AI Agent 判断是否为网络/机房级别的共性问题。
    """
    strategy_name = alarm_base_info.get("strategy_name", "")
    cluster_domain = alarm_base_info.get("cluster_domain", "")

    if not cluster_domain:
        logger.warning(_("[redis_alarm_correlation] 告警事件中缺少 cluster_domain，跳过分析"))
        return

    # 同策略去重：5 分钟内只做一次分析，避免多集群同时告警重复推送
    lock_key = f"redis_latency_analysis_lock:{strategy_name}"
    if cache.get(lock_key):
        logger.info(_("[redis_alarm_correlation] 策略 '{}' 分析冷却中，跳过").format(strategy_name))
        return

    try:
        # 拉取最近 CORRELATION_TIME_WINDOW 秒内同策略名的全量活跃告警
        now = int(time.time())
        search_params = {
            "query_string": f'strategy_name: "{strategy_name}"',
            "status": ["ABNORMAL"],
            "start_time": now - CORRELATION_TIME_WINDOW,
            "end_time": now,
            "page": 1,
            "page_size": 100,
        }
        alert_result = BKMonitorV3Api.search_alert(search_params, use_admin=True)
        alerts = alert_result.get("alerts", []) if isinstance(alert_result, dict) else []
    except Exception as e:
        logger.exception(_("[redis_alarm_correlation] 拉取关联告警失败: {}").format(e))
        return

    # 提取所有受影响的集群域名（去重）
    cluster_domains = set()
    for alert in alerts:
        alert_dimensions = alert.get("dimensions", {})
        # 兼容 dimensions 为列表格式（蓝鲸监控 search_alert 返回格式）
        if isinstance(alert_dimensions, list):
            alert_dimensions = {d.get("key"): d.get("value") for d in alert_dimensions}
        domain = alert_dimensions.get("cluster_domain", "")
        if domain:
            cluster_domains.add(domain)

    affected_clusters = len(cluster_domains)

    logger.info(
        _("[redis_alarm_correlation] 策略 '{}' 涉及集群数: {}，集群列表: {}").format(
            strategy_name, affected_clusters, cluster_domains
        )
    )

    if not env.ENABLE_DBM_AI:
        logger.info(_("[redis_alarm_correlation] ENABLE_DBM_AI 未开启，跳过 AI 关联分析"))
        return

    try:
        # 设置去重锁，防止后续同策略告警重复触发
        cache.set(lock_key, 1, DEDUP_LOCK_TTL)

        correlation_input = {
            "strategy_name": strategy_name,
            "cluster_domains": list(cluster_domains),
        }

        from backend.dbm_aiagent.agent.handlers import AgentHandler

        result_summary = AgentHandler.ask_agent_with_command(
            command=RedisLatencyAlarmRootCauseCommand.command,
            command_params=correlation_input,
        )

        if not result_summary:
            logger.info(_("[redis_alarm_correlation] 集群 {} AI 分析无结果，跳过通知").format(cluster_domain))
            return

        logger.info(_("[redis_alarm_correlation] 集群 {} AI 关联分析完成，开始推送通知").format(cluster_domain))

        title = _("{} - Redis 延迟告警关联分析").format(cluster_domain)
        msgs = {
            "BKID": alarm_base_info["bk_biz_id"],
            _("集群类型"): alarm_base_info.get("cluster_type", ClusterType.RedisInstance.value),
            _("触发集群"): cluster_domain,
            _("受影响集群数"): len(cluster_domains),
            _("受影响集群列表"): json.dumps(sorted(cluster_domains), ensure_ascii=False),
            _("受影响集群明细"): "\n".join(f"- {d}" for d in sorted(cluster_domains)),
            _("AI分析结论"): result_summary,
        }
        send_msg_2_qywx(title, msgs)
    except Exception as e:
        logger.exception(_("[redis_alarm_correlation] AI 关联分析失败: {}").format(e))


@shared_task
def call_redis_persist_anomaly_analysis(callback_data: dict, alarm_base_info: dict):
    """
    异步任务：Persist 异常告警触发 AI 分析，判断是否为母鸡（宿主机）故障导致。
    """
    cluster_domain = alarm_base_info.get("cluster_domain", "")

    if not cluster_domain:
        logger.warning(_("[redis_persist_anomaly] 告警事件中缺少 cluster_domain，跳过分析"))
        return

    if not env.ENABLE_DBM_AI:
        logger.info(_("[redis_persist_anomaly] ENABLE_DBM_AI 未开启，跳过 AI 分析"))
        return

    try:
        from backend.dbm_aiagent.agent.handlers import AgentHandler

        result_summary = AgentHandler.ask_agent_with_command(
            command=RedisPersistAnomalyRootCauseCommand.command,
            command_params={
                "cluster_domain": cluster_domain,
            },
        )

        if not result_summary:
            logger.info(_("[redis_persist_anomaly] 集群 {} AI 分析无结果，跳过通知").format(cluster_domain))
            return

        logger.info(_("[redis_persist_anomaly] 集群 {} AI 分析完成，开始推送通知").format(cluster_domain))

        title = _("{} - Redis Persist 异常告警分析").format(cluster_domain)
        msgs = {
            "BKID": alarm_base_info["bk_biz_id"],
            _("集群类型"): alarm_base_info.get("cluster_type", ClusterType.RedisInstance.value),
            _("触发集群"): cluster_domain,
            _("AI分析结论"): result_summary,
        }
        send_msg_2_qywx(title, msgs)
    except Exception as e:
        logger.exception(_("[redis_persist_anomaly] AI 分析失败: {}").format(e))


@shared_task
def call_redis_single_cpu_high_analysis(callback_data: dict, alarm_base_info: dict):
    """
    异步任务：单核 CPU 使用率过高告警触发 AI 分析，判断是负载不均还是热 Key 导致。
    """
    cluster_domain = alarm_base_info.get("cluster_domain", "")

    if not cluster_domain:
        logger.warning(_("[redis_single_cpu_high] 告警事件中缺少 cluster_domain，跳过分析"))
        return

    if not env.ENABLE_DBM_AI:
        logger.info(_("[redis_single_cpu_high] ENABLE_DBM_AI 未开启，跳过 AI 分析"))
        return

    try:
        from backend.dbm_aiagent.agent.handlers import AgentHandler

        result_summary = AgentHandler.ask_agent_with_command(
            command=RedisSingleCpuHighRootCauseCommand.command,
            command_params={
                "cluster_domain": cluster_domain,
            },
        )

        if not result_summary:
            logger.info(_("[redis_single_cpu_high] 集群 {} AI 分析无结果，跳过通知").format(cluster_domain))
            return

        logger.info(_("[redis_single_cpu_high] 集群 {} AI 分析完成，开始推送通知").format(cluster_domain))

        title = _("{} - Redis 单核 CPU 使用率告警分析").format(cluster_domain)
        msgs = {
            "BKID": alarm_base_info["bk_biz_id"],
            _("集群类型"): alarm_base_info.get("cluster_type", ClusterType.RedisInstance.value),
            _("触发集群"): cluster_domain,
            _("AI分析结论"): result_summary,
        }
        send_msg_2_qywx(title, msgs)
    except Exception as e:
        logger.exception(_("[redis_single_cpu_high] AI 分析失败: {}").format(e))
