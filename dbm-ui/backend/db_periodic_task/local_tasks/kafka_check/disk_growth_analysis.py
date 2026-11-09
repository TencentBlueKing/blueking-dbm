# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed on the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging
from dataclasses import dataclass
from typing import ClassVar, Optional

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import Cluster
from backend.db_periodic_task.dispatch.config import IdempotenceMode
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.db_report.enums.kafka_disk_growth_sub_type import (
    KafkaDiskGrowthAiStatus,
    KafkaDiskGrowthRule,
    KafkaDiskGrowthRunKind,
)
from backend.db_report.models import KafkaDiskGrowthReport
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.tasks.base import AITask
from backend.dbm_aiagent.tasks.config import AITaskConfig
from backend.dbm_aiagent.tasks.invoker import AgentRequest
from backend.dbm_aiagent.tasks.registry import ai_task

logger = logging.getLogger("celery")

# 报告里最多保存的 AI 结论长度，与 AGENT_RESPONSE_LOG_MAX_CHARS 保持一致
AI_ANALYSIS_MAX_CHARS = 2000

RULE_LABELS = {
    KafkaDiskGrowthRule.CONTINUOUS_NEW_HIGH.value: "持续创新高（日峰值连续多天高于此前7天最高值）",
    KafkaDiskGrowthRule.SINGLE_DAY_JUMP.value: "单日跳涨（当天峰值比此前7天最高值高出很多）",
}
RUN_KIND_LABELS = {
    KafkaDiskGrowthRunKind.MORNING.value: "早间巡检，使用昨天的完整日峰值",
    KafkaDiskGrowthRunKind.AFTERNOON.value: "午后巡检，当天峰值为截至巡检时的值",
}

PROMPT_TEMPLATE = """使用 kafka-alarm-analyzer 告警分析 skill 的磁盘增长分析（巡检触发）来分析以下集群，返回输出控制在 600 字符以内。
集群域名: {domain}
业务ID: {bk_biz_id}
判定日期: {check_day}（{run_kind}）
集群级保留期: {retention}
命中的 broker（磁盘使用率为各挂载点的日峰值）:
{hits}

输出要求（严格遵守）:
1. 第一行: 原因分类: 流量驱动 / 数据累积 / 其他
2. 第二行: 主要topic: <最多3个，用逗号分隔；无法判断时写“未知”并说明原因>
3. 第三行: 建议: <一条可执行的操作>
不要输出 markdown 标题、代码块或多余解释。"""


@dataclass
class KafkaDiskGrowthAnalysisConfig(AITaskConfig):
    task_key: ClassVar[str] = "kafka.disk_growth_analysis"
    idempotence_mode: IdempotenceMode = IdempotenceMode.DEDUPE
    # 一次巡检最多提交给 AI 分析的集群数，防止异常情况下大量派发
    max_submit_per_run: int = 50

    @classmethod
    def validate_raw(cls, raw: dict) -> None:
        super().validate_raw(raw)
        config = cls.from_raw(raw)
        if config.max_submit_per_run < 1:
            raise ValidationError({"config": "max_submit_per_run must be at least 1"})


def build_prompt(item: dict) -> str:
    """把判定结果直接写进提示词，AI 不需要再判断是否在涨，只负责找原因"""
    retention_hours = item.get("retention_hours")
    retention = f"{retention_hours} 小时（topic 可能有单独设置）" if retention_hours else "未知"
    lines = []
    for hit in item.get("hits", []):
        series = " → ".join(str(point["peak"]) for point in hit.get("peaks", []))
        lines.append(
            f"- {hit['ip']} {hit['mount_point']} 规则={RULE_LABELS.get(hit['rule'], hit['rule'])} "
            f"当天峰值={hit['peak']}% 比此前7天最高值高 {hit['excess']} 个点 "
            f"近3天日均涨 {hit['daily_growth']} 个点 最近8天日峰值={series}"
        )
    return PROMPT_TEMPLATE.format(
        domain=item["domain"],
        bk_biz_id=item["bk_biz_id"],
        check_day=item["check_day"],
        run_kind=RUN_KIND_LABELS.get(item["run_kind"], item["run_kind"]),
        retention=retention,
        hits="\n".join(lines),
    )


def update_report_ai_result(report_ids: list, ai_status: str, ai_analysis: str = "") -> None:
    if not report_ids:
        return
    KafkaDiskGrowthReport.objects.filter(id__in=report_ids).update(
        ai_status=ai_status, ai_analysis=ai_analysis[:AI_ANALYSIS_MAX_CHARS], update_at=timezone.now()
    )


@ai_task(agent_code=DBMAgentCode.KAFKA_INSPECT, config_cls=KafkaDiskGrowthAnalysisConfig, db_type="kafka")
class KafkaDiskGrowthAnalysisTask(AITask):
    """对巡检命中的 Kafka 集群做 AI 分析，结果写回对应的巡检报告行"""

    prompt_template = PROMPT_TEMPLATE

    def work_item_id(self, item) -> str:
        return f"kafka_disk_growth:{item['cluster_id']}:{item['check_day']}:{item['run_kind']}"

    def build_request(self, item, *, overrides=None) -> AgentRequest:
        return AgentRequest(content=build_prompt(item))

    def on_before_execute(self, item) -> Optional[str]:
        """排队期间集群可能已下线，此时跳过；框架在跳过时不会调用 on_execute_complete，所以这里直接回写"""
        cluster = Cluster.objects.filter(id=item.get("cluster_id")).first()
        reason = None
        if not cluster:
            reason = "cluster not found"
        elif cluster.phase != ClusterPhase.ONLINE.value:
            reason = f"cluster phase={cluster.phase} is not online"
        if reason:
            update_report_ai_result(item.get("report_ids", []), KafkaDiskGrowthAiStatus.SKIPPED.value, reason)
        return reason

    def on_execute_complete(self, item, outcome, *, job=None) -> None:
        report_ids = item.get("report_ids", [])
        if outcome.outcome == DispatchOutcomeType.SUCCESS:
            response = str(outcome.response or "").strip()
            if response:
                update_report_ai_result(report_ids, KafkaDiskGrowthAiStatus.SUCCESS.value, response)
            else:
                update_report_ai_result(report_ids, KafkaDiskGrowthAiStatus.FAILED.value, _("AI 未返回分析结果"))
            return
        outcome_name = getattr(outcome.outcome, "value", outcome.outcome)
        logger.warning(
            "kafka disk growth analysis not completed: cluster=%s outcome=%s", item.get("domain"), outcome_name
        )
        update_report_ai_result(
            report_ids, KafkaDiskGrowthAiStatus.FAILED.value, _("AI 分析未完成: {}").format(outcome_name)
        )
