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
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from celery import shared_task
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.core.notify.handlers import NotifyAdapter
from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_monitor.views.callbacks.base import AlarmCallback
from backend.db_report.portrait import MysqlPortraitDimensionCode, ingest_summary
from backend.db_report.portrait.exceptions import PortraitSDKBaseException
from backend.dbm_aiagent.agent.constants import DBMAgentCode

logger = logging.getLogger("root")


def utc_to_cst_tz(utc_time_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """将 UTC 时间字符串转换为东八区（CST）时间字符串，带时区后缀"""
    utc_time = datetime.strptime(utc_time_str, fmt).replace(tzinfo=dt_timezone.utc)
    return utc_time.astimezone(dt_timezone(timedelta(hours=8))).strftime(f"{fmt}%z")


def parse_agent_output(text: str) -> dict:
    """
    从 agent 返回的文本中提取 <output>...</output> 标签内的 JSON 内容，解析为 dict。
    如果未找到 <output> 标签或 JSON 解析失败，返回空字典。
    """
    import json
    import re

    pattern = r"<output>\s*(.*?)\s*</output>"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        logger.warning("[parse_agent_output] 未找到 <output>...</output> 标签")
        return {}

    json_str = match.group(1).strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning("[parse_agent_output] JSON 解析失败: {}, 原始内容: {}".format(e, json_str))
        return {}


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
            "anomaly_time": utc_to_cst_tz(anomaly_detail.get("anomaly_time", "")),
            "create_time": utc_to_cst_tz(latest_anomaly_record.get("create_time", "")),
        }
        break  # 只取第一条异常记录

    # 去除 event 中的 agg_dimensions
    event = callback_message.get("event", {})
    event.pop("agg_dimensions", None)
    event["begin_time"] = utc_to_cst_tz(event.get("begin_time", ""))
    event["create_time"] = utc_to_cst_tz(event.get("create_time", ""))

    # 构建精简后的回调信息
    result = {
        "appointees": callback_data.get("appointees", []),
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


def _resolve_cluster_and_role(callback_data: dict, alarm_base_info: dict, log_tag: str) -> tuple:
    """
    从告警回调数据中提取 cluster_domain 和 instance_role。
    返回 (cluster_domain, instance_role)，提取失败时返回 (None, None)。
    """
    try:
        dimensions = callback_data["callback_message"]["event"]["dimensions"]
        cluster_domain = dimensions.get("cluster_domain", "")
        if not cluster_domain:
            logger.warning(_("[{}] 告警事件中缺少 cluster_domain，跳过 AI 分析").format(log_tag))
            return None, None

        # 确定 instance_role
        instance_role = dimensions.get("instance_role", "")
        if not instance_role or instance_role == "--":
            if alarm_base_info.get("cluster_type", "") == ClusterType.TenDBHA:
                instance_role = InstanceRole.BACKEND_MASTER.value
            else:
                instance_role = TenDBClusterSpiderRole.SPIDER_MASTER.value

        return cluster_domain, instance_role
    except Exception as e:
        logger.exception(_("[{}] 提取 ai 分析参数失败: {}").format(log_tag, e))
        return None, None


class MySQLAlarm(AlarmCallback):
    """MySQL 告警回调处理器，处理所有 MySQL 相关的告警回调"""

    # 处理函数 -> 匹配条件列表的映射
    # keyword: 策略名中的关键字
    # level: 告警级别列表（0-致命, 1-预警, 2-提醒）
    # cluster_type: 集群类型列表
    STRATEGY_HANDLERS = {
        "call_slowlog_ai_analysis": [
            {
                "keyword": "慢查询数量",
                "level": [0, 1, 2],
                "cluster_type": [],
            }
        ],
        "call_mysql_conf_analyzer": [
            {
                "keyword": "慢查询数量",
                "level": [0, 1, 2],
                "cluster_type": ["tendbha", "tendbcluster", "tendbsingle"],
            },
            {
                "keyword": "主机内存使用率",
                "level": [0, 1, 2],
                "cluster_type": ["tendbha", "tendbcluster", "tendbsingle"],
            },
            {
                "keyword": "主机 CPU 负载",
                "level": [0, 1, 2],
                "cluster_type": ["tendbha", "tendbcluster", "tendbsingle"],
            },
        ],
        "call_mysql_alarm_analyzer": [
            {
                "keyword": "Threads_running",
                "level": [0, 1],
                "cluster_type": [],
            },
            {
                "keyword": "连接失败",
                "level": [0, 1, 2],
                "cluster_type": [],
            },
            {
                "keyword": "主机 CPU 负载",
                "level": [0, 1],
                "cluster_type": [],
            },
            {
                "keyword": "dbha二次探测失败",
                "level": [0, 1, 2],
                "cluster_type": ["tendbcluster", "tendbha", "tendbsingle"],
            },
        ],
    }

    @classmethod
    def callback(cls, callback_data: dict):
        """根据策略名、告警级别、集群类型分发到对应的异步处理任务"""
        callback_message = callback_data.get("callback_message", {})
        strategy_name = callback_message.get("strategy", {}).get("name", "")
        event_level = callback_message.get("event", {}).get("level")
        alarm_time = callback_message.get("latest_anomaly_record", {}).get("create_time")
        # 将 alarm_time 从 UTC 转换为东八区时间
        if alarm_time:
            alarm_time = utc_to_cst_tz(alarm_time)

        # 优先从 dimensions 中获取 cluster_type，没有则通过 cluster_domain 查询
        dimensions = callback_message.get("event", {}).get("dimensions", {})
        cluster_domain = dimensions.get("cluster_domain")
        cluster_type = dimensions.get("cluster_type", "")
        bk_biz_id = int(dimensions.get("appid", 0))
        if (not cluster_type or not bk_biz_id) and cluster_domain:
            cluster = Cluster.objects.filter(immute_domain=cluster_domain).first()
            cluster_type = cluster.cluster_type if cluster else None
            bk_biz_id = cluster.bk_biz_id

        alarm_base_info = {
            "bk_biz_id": bk_biz_id,
            "cluster_type": cluster_type,
            "cluster_domain": cluster_domain,
            "dimensions": dimensions,
            "strategy_name": strategy_name,
            "level": event_level,
            "alarm_time": alarm_time,
            "appointees": callback_data.get("appointees", []),
        }

        for handler_name, conditions in cls.STRATEGY_HANDLERS.items():
            for condition in conditions:
                # 匹配策略名关键字
                if condition["keyword"] == "" or condition["keyword"] not in strategy_name:
                    continue
                # 匹配告警级别（未设置或为空时不限制）
                level_list = condition.get("level", [])
                if level_list and event_level is not None and event_level not in level_list:
                    continue
                # 匹配集群类型（未设置或为空时不限制）
                cluster_type_list = condition.get("cluster_type", [])
                if cluster_type_list and cluster_type and cluster_type not in cluster_type_list:
                    continue

                handler = globals().get(handler_name)
                if handler:
                    handler.delay(callback_data, alarm_base_info)
                    logger.info(
                        _("[MySQLAlarm] 策略 '{}' (level={}, cluster_type={}) 分发到异步任务: {}").format(
                            strategy_name, event_level, cluster_type, handler_name
                        )
                    )
                else:
                    logger.warning(_("[MySQLAlarm] 未找到处理函数: {}").format(handler_name))
                return


@shared_task
def call_mysql_alarm_analyzer(callback_data: dict, alarm_base_info: dict):
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
    except Exception as e:
        logger.exception(_("[mysql_alarm_analyzer] 提取 ai 分析参数失败: {}").format(e))
        return

    try:
        # 延迟导入，避免监控策略视图在单测收集期强依赖 aidev Agent 包
        from backend.dbm_aiagent.agent.commands.commands import MySQLAlarmAnalyzerCommand
        from backend.dbm_aiagent.agent.handlers import AgentHandler

        # 调用 AI Agent 进行慢查询分析
        user_prompt = extract_callback_key_info(callback_data)
        logger.info(
            _("[mysql_alarm_analyzer] 告警触发 AI 分析开始，集群: {}. user prompt: {}").format(cluster_domain, user_prompt)
        )
        # only return summary that length < 2000, otherwise notify will send failed
        result_summary = AgentHandler.ask_agent_with_command(
            command=MySQLAlarmAnalyzerCommand.command,
            command_params={
                "alarm_content": user_prompt,
            },
        )

        if not result_summary:
            logger.info(_("[mysql_alarm_analyzer] 集群 {} AI 分析无结果，跳过通知").format(cluster_domain))
            return

        logger.info(_("[mysql_alarm_analyzer] 集群 {} AI 分析分析完成，开始推送通知").format(cluster_domain))

        title = _("「DBM」：集群 {} 告警 AI 分析结果").format(cluster_domain)
        # 调用 NotifyAdapter 发送 AI 分析报告通知
        NotifyAdapter.send_msg_for_ai_report(
            bk_biz_id=alarm_base_info["bk_biz_id"],
            base_info=alarm_base_info,
            title=title,
            ai_result=result_summary,
            share_url="",
            receivers=alarm_base_info["appointees"],
        )
    except Exception as e:
        logger.exception(_("[mysql_alarm_analyzer] 告警触发 AI 分析失败: {}").format(e))


def _call_agent_and_notify(
    alarm_base_info: dict,
    cluster_domain: str,
    log_tag: str,
    agent_code: DBMAgentCode,
    content: str,
    title_template: str,
    portrait_dimension: MysqlPortraitDimensionCode,
    timeout: int = 600,
):
    """
    通用的告警触发 AI 分析流程：
    1. 调用 AgentHandler.ask_agent_with_content 获取分析结果
    2. 解析 <output> JSON 结果
    3. 发送通知并上报画像

    Args:
        alarm_base_info: 告警基础信息
        cluster_domain: 集群域名
        log_tag: 日志标签
        agent_code: 智能体编码（DBMAgentCode）
        content: 发送给智能体的提示词内容
        title_template: 通知标题模板，需包含一个 {} 占位符用于填充 cluster_domain
        portrait_dimension: 画像维度编码
        timeout: Agent 调用超时时间（秒）
    """
    try:
        from backend.dbm_aiagent.agent.handlers import AgentHandler

        logger.info(_("[{}] 告警触发 AI 分析，集群: {}").format(log_tag, cluster_domain))
        agent_output = AgentHandler.ask_agent_with_content(
            agent_code=agent_code,
            content=content,
            timeout=timeout,
        )
        if not agent_output:
            logger.info(_("[{}] 集群 {} AI 分析无结果，跳过通知").format(log_tag, cluster_domain))
            return

        result_json = parse_agent_output(agent_output)
        if not result_json:
            logger.info(_("[{}] 集群 {} AI 分析结果解析json失败，跳过通知").format(log_tag, cluster_domain))
            return

        logger.info(_("[{}] 集群 {} AI 分析完成，开始推送通知").format(log_tag, cluster_domain))
        title = _(title_template).format(cluster_domain)

        NotifyAdapter.send_msg_for_ai_report(
            bk_biz_id=alarm_base_info["bk_biz_id"],
            base_info=alarm_base_info,
            title=title,
            ai_result=result_json.get("summary"),
            share_url=result_json.get("share_url"),
            receivers=alarm_base_info["appointees"],
        )
        try:
            ingest_summary(
                db_type=alarm_base_info["cluster_type"],
                dimension=portrait_dimension,
                bk_biz_id=alarm_base_info["bk_biz_id"],
                cluster_domain=alarm_base_info["cluster_domain"],
                report_time=datetime.now(),
                summary=result_json.get("summary"),
                detail_url=result_json.get("share_url"),
            )
        except PortraitSDKBaseException:
            logger.exception(f"[{log_tag}] report {cluster_domain} to portrait failed")
    except Exception as e:
        logger.exception(_("[{}] 告警触发 AI 分析失败: {}").format(log_tag, e))


@shared_task
def call_slowlog_ai_analysis(callback_data: dict, alarm_base_info: dict):
    """
    异步任务：告警触发 AI 慢查询分析，并将结果通过消息推送
    """
    cluster_domain, instance_role = _resolve_cluster_and_role(callback_data, alarm_base_info, "slowlog_ai_analysis")
    if not cluster_domain:
        return

    # 设置时间窗口为过去 1 小时
    now = timezone.now()
    time_window_start = now - timedelta(hours=1)
    time_window_end = now
    time_window_start_str = time_window_start.replace(microsecond=0).isoformat(sep="T")
    time_window_end_str = time_window_end.replace(microsecond=0).isoformat(sep="T")

    _call_agent_and_notify(
        alarm_base_info=alarm_base_info,
        cluster_domain=cluster_domain,
        log_tag="slowlog_ai_analysis",
        agent_code=DBMAgentCode.MYSQL_SLOW_LOGS_QUERY,
        content="""
帮我分析集群 {cluster_domain} 的慢查询
分析的时间窗口：'{time_window_start}' - '{time_window_end}'
最大查询条数：{limit}
instance_role: {instance_role}

返回格式严格是一个 json, 内容包裹在 <output></output> 中. 示例:
<output>
{{
  "share_url": "<dbm 报告url分享地址>",
  "summary": "<agent 分析结果的摘要>"
}}
</output>
        """.format(
            cluster_domain=cluster_domain,
            time_window_start=time_window_start_str,
            time_window_end=time_window_end_str,
            limit=5,
            instance_role=instance_role,
        ),
        title_template="「DBM」：集群 {} 慢查询 AI 分析结果",
        portrait_dimension=MysqlPortraitDimensionCode.SLOW_QUERY,
    )


@shared_task
def call_mysql_conf_analyzer(callback_data: dict, alarm_base_info: dict):
    """
    异步任务：告警触发 AI MySQL 配置优化分析，并将结果通过消息推送
    """
    cluster_domain, instance_role = _resolve_cluster_and_role(callback_data, alarm_base_info, "mysql_conf_analyzer")
    if not cluster_domain:
        return

    _call_agent_and_notify(
        alarm_base_info=alarm_base_info,
        cluster_domain=cluster_domain,
        log_tag="mysql_conf_analyzer",
        agent_code=DBMAgentCode.MYSQL_CONFIG_PERF_TUNER,
        content="""
帮我分析集群 {cluster_domain} 的配置，给出优化建议
instance_role: {instance_role}

返回格式严格是一个 json, 内容包裹在 <output></output> 中. 示例:
<output>
{{
  "share_url": "<dbm 报告url分享地址>",
  "summary": "<agent 分析结果的摘要>"
}}
</output>
        """.format(
            cluster_domain=cluster_domain,
            instance_role=instance_role,
        ),
        title_template="「DBM」：集群 {} 配置优化 AI 分析结果",
        portrait_dimension=MysqlPortraitDimensionCode.CONFIG_CHECK,
    )
