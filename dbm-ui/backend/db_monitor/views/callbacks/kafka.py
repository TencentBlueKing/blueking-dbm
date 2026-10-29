# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Kafka 告警回调：告警触发 AI 分析，并将分析结果通过消息推送给告警接收人。

整体链路与 MySQL / Redis 一致：蓝鲸监控回调 -> AlarmCallback.dispatch -> KafkaAlarm.callback
（按策略名关键字 / 级别匹配，并做频率限制）-> celery 异步任务调用 agent -> 推送。
"""
import logging
import struct
import time
import zlib
from typing import Optional

from celery import shared_task
from django.utils.translation import gettext as _

from backend import env
from backend.core.notify.handlers import NotifyAdapter
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_monitor.views.callbacks.base import AlarmCallback
from backend.db_monitor.views.callbacks.mysql import (
    _needs_summary,
    extract_callback_key_info,
    parse_agent_output,
    utc_to_cst_tz,
)
from backend.dbm_aiagent.agent.constants import DBMAgentCode

logger = logging.getLogger("root")

LOG_TAG = "kafka_alarm_analyzer"

# 提示词里点名的 skill 名称，托管在 AIDev 平台，agent 需绑定该 skill
KAFKA_ALARM_ANALYZER_SKILL = "kafka_alarm_analyzer"

# 要求 agent 输出控制在该字符数以内，避免企微推送过长
OUTPUT_MAX_CHARS = 1800

SUMMARY_PROMPT = (
    "Please summarize the following analysis report concisely.\n"
    "Keep the key findings or conclusions or the root cause within 800 characters.\n"
    "The summary will be sent as a WeCom/Markdown notification, so it must be easy to read on mobile, "
    "and do not write one long paragraph, markdown bullet lines is preferred.\n"
    "Return strictly in the following JSON format wrapped by <output></output>:\n"
    "<output>\n"
    '{"share_url": "<if have one>", "summary": "<your summary>"}'
    "</output>\n\n"
    "Original content:\n"
)


def _parse_event_level(raw_level) -> Optional[int]:
    """告警级别统一转 int（回调序列化器里 event 是 DictField，不保证类型，可能是 "1"）。

    解析失败返回 None：匹配时按"不限制级别"处理，与 RedisAlarm 的降级行为一致，
    并打 warning，避免因为类型问题让带级别限制的规则静默不触发。
    """
    if raw_level is None:
        return None
    try:
        return int(raw_level)
    except (TypeError, ValueError):
        logger.warning(_("[KafkaAlarm] 无法解析告警级别: {}，将按不限制级别处理").format(raw_level))
        return None


def _build_alarm_base_info(callback_data: dict) -> dict:
    """从告警回调数据中提取分析和推送需要的基础信息。

    cluster_type / bk_biz_id 优先取告警维度，缺失时通过 cluster_domain 反查集群补齐；
    集群查不到时保持空值，不抛异常，由后续逻辑决定是否跳过。
    """
    callback_message = callback_data.get("callback_message", {})
    event = callback_message.get("event", {})
    dimensions = event.get("dimensions", {})

    alarm_time = callback_message.get("latest_anomaly_record", {}).get("create_time")
    if alarm_time:
        alarm_time = utc_to_cst_tz(alarm_time)

    cluster_domain = dimensions.get("cluster_domain", "")
    cluster_type = dimensions.get("cluster_type", "")
    try:
        bk_biz_id = int(dimensions.get("appid", 0))
    except (TypeError, ValueError):
        bk_biz_id = 0
    if cluster_domain and (not cluster_type or not bk_biz_id):
        cluster = Cluster.objects.filter(immute_domain=cluster_domain).first()
        if cluster:
            cluster_type = cluster_type or cluster.cluster_type
            bk_biz_id = bk_biz_id or cluster.bk_biz_id

    return {
        "bk_biz_id": bk_biz_id,
        "cluster_type": cluster_type,
        "cluster_domain": cluster_domain,
        "dimensions": dimensions,
        "strategy_name": callback_message.get("strategy", {}).get("name", ""),
        "level": _parse_event_level(event.get("level")),
        "alarm_time": alarm_time,
        "appointees": callback_data.get("appointees", []),
    }


class KafkaAlarm(AlarmCallback):
    """Kafka 告警回调处理器"""

    SUPPORTED_CLUSTER_TYPES = {ClusterType.Kafka.value}

    # 处理函数 -> 匹配条件列表的映射
    # keyword: 策略名中的关键字
    # level: 蓝鲸监控告警级别，Kafka 策略模板里 1 为致命，2 为预警（空列表表示不限制）
    # cluster_type: 集群类型列表（空列表表示不限制）
    # ratelimit: 频率限制，格式 "次数 / 小时数"，按 集群域名+处理函数+关键字 计数
    STRATEGY_HANDLERS = {
        "call_kafka_alarm_analyzer": [
            {
                "keyword": "磁盘空间使用率",
                "level": [1, 2],
                "cluster_type": [],
                "ratelimit": "1 / 8",
            },
            {
                # 注意是模板顶层 name 字段 "Kafka under replicated partitions"，不是文件名
                "keyword": "under replicated partitions",
                "level": [2],
                "cluster_type": [],
                "ratelimit": "1 / 8",
            },
            {
                "keyword": "主机 CPU 使用率",
                "level": [2],
                "cluster_type": [],
                "ratelimit": "1 / 8",
            },
            {
                # 消费组延迟没有统一阈值，由业务自建策略，级别不固定，所以不限制级别
                "keyword": "消费组延迟",
                "level": [],
                "cluster_type": [],
                "ratelimit": "1 / 8",
            },
        ],
    }

    @staticmethod
    def _is_match(condition: dict, strategy_name: str, event_level, cluster_type: str) -> bool:
        """判断告警是否命中某个匹配条件。策略名匹配不区分大小写，关键字必须取自策略模板的 name 字段"""
        keyword = condition["keyword"]
        if not keyword or keyword.casefold() not in strategy_name.casefold():
            return False
        level_list = condition.get("level", [])
        if level_list and event_level is not None and event_level not in level_list:
            return False
        cluster_type_list = condition.get("cluster_type", [])
        if cluster_type_list and cluster_type and cluster_type not in cluster_type_list:
            return False
        return True

    @classmethod
    def callback(cls, callback_data: dict):
        """根据策略名、告警级别、集群类型分发到对应的异步处理任务"""
        alarm_base_info = _build_alarm_base_info(callback_data)
        strategy_name = alarm_base_info["strategy_name"]
        event_level = alarm_base_info["level"]
        cluster_type = alarm_base_info["cluster_type"]
        cluster_domain = alarm_base_info["cluster_domain"]

        for handler_name, conditions in cls.STRATEGY_HANDLERS.items():
            for condition in conditions:
                if not cls._is_match(condition, strategy_name, event_level, cluster_type):
                    continue

                # 频率限制检查（超限则跳过当前 handler，不影响其他 handler）
                if not cls.check_rate_limit(
                    cluster_domain, handler_name, condition["keyword"], condition.get("ratelimit", "")
                ):
                    break

                handler = globals().get(handler_name)
                if handler:
                    handler.delay(callback_data, alarm_base_info)
                    logger.info(
                        _("[KafkaAlarm] 策略 '{}' (level={}, cluster_type={}) 分发到异步任务: {}").format(
                            strategy_name, event_level, cluster_type, handler_name
                        )
                    )
                else:
                    logger.warning(_("[KafkaAlarm] 未找到处理函数: {}").format(handler_name))
                # 当前 handler 已匹配到一个 condition 并处理，跳出内层循环继续下一个 handler
                break


def _summarize(agent_output: str) -> tuple:
    """调用摘要 agent 对过长的输出做摘要，返回 (summary, share_url)。

    摘要 agent 要求以 <output>{"share_url": "", "summary": ""}</output> 格式返回；
    摘要失败或格式不符时降级：格式不符用摘要原文，调用失败用原始输出。
    """
    from backend.dbm_aiagent.agent.handlers import AgentHandler

    try:
        summary_result = AgentHandler.ask_agent_with_content(
            agent_code=DBMAgentCode.DBM_AGENT_SUMMARY,
            content=SUMMARY_PROMPT + agent_output,
        )
    except Exception as e:
        logger.exception("[%s] Failed to generate summary, using original: %s", LOG_TAG, e)
        return agent_output, ""

    if not summary_result:
        logger.warning("[%s] Summary agent returned empty, using original output", LOG_TAG)
        return agent_output, ""

    result_json = parse_agent_output(summary_result)
    if result_json and result_json.get("summary"):
        logger.info("[%s] Summary generated successfully, length: %d", LOG_TAG, len(result_json["summary"]))
        return result_json["summary"], result_json.get("share_url", "")

    logger.info("[%s] Summary output not in expected format, using raw summary result", LOG_TAG)
    return summary_result, ""


def _write_report(agent_output: str, summary: str, alarm_base_info: dict, cluster_domain: str) -> str:
    """将 agent 的完整输出写入 AI 分析报告，返回分享链接；写入失败返回空串。"""
    try:
        from backend.db_report.models.ai_analysis_report import AiAnalysisReport

        content_bytes = agent_output.encode("utf-8")
        compressed_content = struct.pack("<I", len(content_bytes)) + zlib.compress(content_bytes)
        report = AiAnalysisReport.objects.create(
            ai_agent=DBMAgentCode.KAFKA_INSPECT,
            format="markdown",
            bk_biz_id=alarm_base_info.get("bk_biz_id", 0),
            cluster_domain=cluster_domain,
            title=_("「DBM」：Kafka 集群 {} 告警 AI 分析报告").format(cluster_domain),
            summary=summary,
            content=compressed_content,
            creator="system",
        )
        share_url = f"{env.BK_SAAS_HOST}/ai-chat/share/{str(report.id)}/"
        logger.info("[%s] Wrote agent output to AiReport, share_url: %s", LOG_TAG, share_url)
        return share_url
    except Exception as e:
        logger.exception("[%s] Failed to write agent output to AiReport: %s", LOG_TAG, e)
        return ""


def _summarize_and_write_report(agent_output: str, alarm_base_info: dict, cluster_domain: str) -> tuple:
    """对过长的 agent 输出做摘要并写入报告，返回 (summary, share_url)。

    摘要 agent 若已返回 share_url 则直接使用，不重复写报告；否则将原文写入报告并生成 share_url。
    """
    summary, share_url = _summarize(agent_output)
    if share_url:
        logger.info("[%s] Got share_url from summary result, skip writing report: %s", LOG_TAG, share_url)
    else:
        share_url = _write_report(agent_output, summary, alarm_base_info, cluster_domain)
    return summary, share_url


@shared_task
def call_kafka_alarm_analyzer(callback_data: dict, alarm_base_info: dict):
    """
    异步任务：Kafka 告警触发 AI 告警分析，并将结果通过消息推送。
    当 agent 输出过长（>1200字符或>1个表格）时，自动做摘要并写入报告。
    """
    if not env.ENABLE_DBM_AI:
        logger.info(_("[{}] ENABLE_DBM_AI 未开启，跳过 AI 分析").format(LOG_TAG))
        return

    cluster_domain = alarm_base_info.get("cluster_domain", "")
    if not cluster_domain:
        logger.warning(_("[{}] 告警事件中缺少 cluster_domain，跳过 AI 分析").format(LOG_TAG))
        return

    # 策略名关键字在其他组件的策略里也可能出现，这里再确认一次确实是 Kafka 集群
    if not Cluster.objects.filter(immute_domain=cluster_domain, cluster_type=ClusterType.Kafka.value).exists():
        logger.warning(_("[{}] 未找到 Kafka 集群: {}，跳过 AI 分析").format(LOG_TAG, cluster_domain))
        return

    try:
        from backend.dbm_aiagent.agent.handlers import AgentHandler

        user_prompt = extract_callback_key_info(callback_data)
        logger.info(_("[{}] 告警触发 AI 分析开始，集群: {}. user prompt: {}").format(LOG_TAG, cluster_domain, user_prompt))
        content = (
            f"使用 {KAFKA_ALARM_ANALYZER_SKILL} 告警分析 skill 来分析一下 db 告警，"
            f"返回输出控制在 {OUTPUT_MAX_CHARS} 字符以内。\n告警内容:\n{user_prompt}"
        )

        start_time = time.monotonic()
        agent_output = AgentHandler.ask_agent_with_content(
            agent_code=DBMAgentCode.KAFKA_INSPECT,
            content=content,
        )
        cost_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            _("[{}] 集群 {} 策略 '{}' AI 分析耗时: {} ms").format(
                LOG_TAG, cluster_domain, alarm_base_info.get("strategy_name", ""), cost_ms
            )
        )

        if not agent_output:
            logger.info(_("[{}] 集群 {} AI 分析无结果，跳过通知").format(LOG_TAG, cluster_domain))
            return

        if _needs_summary(agent_output):
            logger.info(
                "[%s] Agent output too long (len=%d) for cluster %s, generating summary",
                LOG_TAG,
                len(agent_output),
                cluster_domain,
            )
            ai_result, share_url = _summarize_and_write_report(agent_output, alarm_base_info, cluster_domain)
        else:
            ai_result, share_url = agent_output, ""

        logger.info(_("[{}] 集群 {} AI 分析完成，开始推送通知").format(LOG_TAG, cluster_domain))
        NotifyAdapter.send_msg_for_ai_report(
            bk_biz_id=alarm_base_info["bk_biz_id"],
            base_info=alarm_base_info,
            title=_("「DBM」：Kafka 集群 {} 告警 AI 分析结果").format(cluster_domain),
            ai_result=ai_result,
            share_url=share_url,
            receivers=alarm_base_info["appointees"],
        )
    except Exception as e:
        logger.exception(_("[{}] 告警触发 AI 分析失败: {}").format(LOG_TAG, e))
