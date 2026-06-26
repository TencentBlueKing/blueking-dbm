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

from celery import shared_task
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.core.notify.handlers import NotifyAdapter
from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_monitor.views.callbacks.base import AlarmCallback
from backend.dbm_aiagent.agent.commands.commands import MySQLAlarmAnalyzerCommand, MySQLSlowLogCommand
from backend.dbm_aiagent.agent.handlers import AgentHandler

logger = logging.getLogger("root")


def extract_callback_key_info(callback_data: dict) -> dict:
    """
    从告警回调数据中提取有效信息，去除冗余字段。
    去除: labels, bk_biz_id, bk_biz_name
    latest_anomaly_record 只保留 anomaly_message 和 anomaly_time
    """
    callback_message = callback_data.get("callback_message", {})

    # 提取 latest_anomaly_record 中的关键信息（anomaly_message 和 anomaly_time）
    latest_anomaly_record = callback_message.get("latest_anomaly_record", {})
    origin_alarm = latest_anomaly_record.get("origin_alarm", {})
    anomaly_info = {}
    for _key, anomaly_detail in origin_alarm.get("anomaly", {}).items():
        anomaly_info = {
            "anomaly_message": anomaly_detail.get("anomaly_message", ""),
            "anomaly_time": anomaly_detail.get("anomaly_time", ""),
        }
        break  # 只取第一条异常记录

    # 去除 event 中的 agg_dimensions
    event = callback_message.get("event", {})
    event.pop("agg_dimensions", None)

    # 构建精简后的回调信息
    result = {
        "appointees": callback_data.get("appointees", ""),
        "callback_message": {
            "current_value": callback_message.get("current_value", ""),
            "description": callback_message.get("description", ""),
            "type": callback_message.get("type", ""),
            "latest_anomaly_record": anomaly_info,
            "event": event,
            "strategy": callback_message.get("strategy", {}),
            "related_info": callback_message.get("related_info", {}),
        },
        "alert_info": {},
    }

    return result


class MySQLAlarm(AlarmCallback):
    """MySQL 告警回调处理器，处理所有 MySQL 相关的告警回调"""

    # 策略名关键字 -> 处理函数的映射
    STRATEGY_HANDLERS = {
        "慢查询数量": "call_slowlog_ai_analysis",
        "Threads_running": "call_mysql_alarm_analyzer",
        "连接失败": "call_mysql_alarm_analyzer",
    }

    @classmethod
    def callback(cls, callback_data: dict):
        """根据策略名分发到对应的异步处理任务"""
        strategy_name = callback_data.get("callback_message", {}).get("strategy", {}).get("name", "")

        for keyword, handler_name in cls.STRATEGY_HANDLERS.items():
            if keyword in strategy_name:
                handler = globals().get(handler_name)
                if handler:
                    handler.delay(callback_data)
                    logger.info(_("[MySQLAlarm] 策略 '{}' 分发到异步任务: {}").format(strategy_name, handler_name))
                else:
                    logger.warning(_("[MySQLAlarm] 未找到处理函数: {}").format(handler_name))
                return


@shared_task
def call_slowlog_ai_analysis(callback_data):
    """
    异步任务：告警触发 AI 慢查询分析，并将结果通过消息推送
    """

    try:
        dimensions = callback_data["callback_message"]["event"]["dimensions"]
        cluster_domain = dimensions.get("cluster_domain", "")
        if not cluster_domain:
            logger.warning(_("[slowlog_ai_analysis] 告警事件中缺少 cluster_domain，跳过 AI 分析"))
            return

        # 通过 cluster_domain 查询集群类型
        cluster = Cluster.objects.filter(immute_domain=cluster_domain).first()
        if not cluster:
            logger.warning(_("[slowlog_ai_analysis] 未找到集群: {}，跳过 AI 分析").format(cluster_domain))
            return

        bk_biz_id = cluster.bk_biz_id
        cluster_type = cluster.cluster_type

        # 确定 instance_role
        instance_role = dimensions.get("instance_role", "")
        if not instance_role or instance_role == "--":
            if cluster_type == ClusterType.TenDBHA:
                instance_role = InstanceRole.BACKEND_MASTER.value
            else:
                instance_role = TenDBClusterSpiderRole.SPIDER_MASTER.value

        # 设置时间窗口为过去 1 小时
        now = timezone.now()
        time_window_start = now - timedelta(hours=1)
        time_window_end = now

        time_window_start_str = time_window_start.replace(microsecond=0).isoformat(sep="T")
        time_window_end_str = time_window_end.replace(microsecond=0).isoformat(sep="T")
    except Exception as e:
        logger.exception(_("[slowlog_ai_analysis] 提取 ai 分析参数失败: {}").format(e))
        return

    try:
        # 调用 AI Agent 进行慢查询分析
        logger.info(_("[slowlog_ai_analysis] 告警触发 AI 慢查询分析，集群: {}").format(cluster_domain))
        result = AgentHandler.ask_agent_with_command(
            command=MySQLSlowLogCommand.command,
            command_params={
                "cluster_domain": cluster_domain,
                "cluster_type": cluster_type,
                "instance_role": instance_role,
                "time_window_start": time_window_start_str,
                "time_window_end": time_window_end_str,
                "limit": 5,
            },
        )

        if not result:
            logger.info(_("[slowlog_ai_analysis] 集群 {} AI 分析无结果，跳过通知").format(cluster_domain))
            return

        logger.info(_("[slowlog_ai_analysis] 集群 {} AI 慢查询分析完成，开始推送通知").format(cluster_domain))

        # 获取接收人：优先使用告警回调中的负责人
        receivers = [r.strip() for r in callback_data.get("appointees", "").split(",") if r.strip()]

        # 调用 NotifyAdapter 发送 AI 分析报告通知
        NotifyAdapter.send_msg_for_ai_report(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            cluster_type=cluster_type,
            time_window_start=time_window_start_str,
            time_window_end=time_window_end_str,
            ai_result=result,
            receivers=receivers or None,
        )
    except Exception as e:
        logger.exception(_("[slowlog_ai_analysis] 告警触发 AI 慢查询分析失败: {}").format(e))


@shared_task
def call_mysql_alarm_analyzer(callback_data):
    """
    异步任务：告警触发 AI 慢查询分析，并将结果通过消息推送
    """

    try:
        dimensions = callback_data["callback_message"]["event"]["dimensions"]
        cluster_domain = dimensions.get("cluster_domain", "")
        if not cluster_domain:
            logger.warning(_("[mysql_alarm_analyzer] 告警事件中缺少 cluster_domain，跳过 AI 分析"))
            return

        # 通过 cluster_domain 查询集群类型
        cluster = Cluster.objects.filter(immute_domain=cluster_domain).first()
        if not cluster:
            logger.warning(_("[mysql_alarm_analyzer] 未找到集群: {}，跳过 AI 分析").format(cluster_domain))
            return

        bk_biz_id = cluster.bk_biz_id
        cluster_type = cluster.cluster_type

        # 确定 instance_role
        instance_role = dimensions.get("instance_role", "")
        if not instance_role or instance_role == "--":
            if cluster_type == ClusterType.TenDBHA:
                instance_role = InstanceRole.BACKEND_MASTER.value
            else:
                instance_role = TenDBClusterSpiderRole.SPIDER_MASTER.value

        # 设置时间窗口为过去 1 小时
        now = timezone.now()
        time_window_start = now - timedelta(hours=1)
        time_window_end = now

        time_window_start_str = time_window_start.replace(microsecond=0).isoformat(sep="T")
        time_window_end_str = time_window_end.replace(microsecond=0).isoformat(sep="T")
    except Exception as e:
        logger.exception(_("[mysql_alarm_analyzer] 提取 ai 分析参数失败: {}").format(e))
        return

    try:
        # 调用 AI Agent 进行慢查询分析
        logger.info(_("[mysql_alarm_analyzer] 告警触发 AI 分析分析，集群: {}").format(cluster_domain))
        result = AgentHandler.ask_agent_with_command(
            command=MySQLAlarmAnalyzerCommand.command,
            command_params={
                "alarm_content": extract_callback_key_info(callback_data["callback_message"]),
            },
        )

        if not result:
            logger.info(_("[mysql_alarm_analyzer] 集群 {} AI 分析无结果，跳过通知").format(cluster_domain))
            return

        logger.info(_("[mysql_alarm_analyzer] 集群 {} AI 分析分析完成，开始推送通知").format(cluster_domain))

        # 获取接收人：优先使用告警回调中的负责人
        receivers = [r.strip() for r in callback_data.get("appointees", "").split(",") if r.strip()]

        # 调用 NotifyAdapter 发送 AI 分析报告通知
        NotifyAdapter.send_msg_for_ai_report(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            cluster_type=cluster_type,
            time_window_start=time_window_start_str,
            time_window_end=time_window_end_str,
            ai_result=result,
            receivers=receivers or None,
        )
    except Exception as e:
        logger.exception(_("[mysql_alarm_analyzer] 告警触发 AI 分析失败: {}").format(e))
