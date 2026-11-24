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
from collections import defaultdict
from datetime import timedelta
from typing import Callable, Dict, List, Optional, Set, Tuple

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.db_meta.api.cluster_state.fields.base import NativeStateField
from backend.db_meta.api.cluster_state.values import StateValue
from backend.db_meta.enums import ClusterStatus, ClusterType, InstancePhase, InstanceStatus, StateValueType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_monitor.models import (
    MySQLDBHAAutofixTicketStageQueue,
    MySQLDBHAEvent,
    TicketQueueCommitException,
    TicketQueueUncommitStatus,
    TicketQueueWaitTimeout,
)
from blue_krill.data_types.enum import EnumField, StrStructuredEnum

logger = logging.getLogger("root")

# 事件被调度后超过这个时间仍未进队列，视为写入队列失败
DISPATCH_TIMEOUT = timedelta(minutes=15)

# 集群状态的查询全部走 dbmeta 只读通道
DBMETA_READONLY = "dbmeta-readonly"


class AFStateChoiceEnum(StrStructuredEnum):
    """集群维度的 DBHA 自愈状态，事件层、队列层、单据层合并，按流转顺序排列"""

    # 事件层，由 MySQLDBHAEvent 推导；label 是展示模板，数量由 EVENT_NUMBER_RULES 计算
    EVENT_REPORTING = EnumField("EVENT_REPORTING", _("机器上报中({})"))
    EVENT_VALIDATE_FAILED = EnumField("EVENT_VALIDATE_FAILED", _("事件校验失败({})"))
    # 已调度、仍在 15 分钟处理窗口内的过渡状态，查询方通常不需要关注
    EVENT_DISPATCHING = EnumField("EVENT_DISPATCHING", _("事件调度中({})"))
    EVENT_DISPATCHED = EnumField("EVENT_DISPATCHED", _("事件已入队({})"))
    EVENT_DISPATCH_TIMEOUT = EnumField("EVENT_DISPATCH_TIMEOUT", _("事件入队超时({})"))

    # 队列层，由 MySQLDBHAAutofixTicketStageQueue 的 status 归并，只覆盖提单前；填入单据数量
    QUEUE_UNCOMMIT = EnumField("QUEUE_UNCOMMIT", _("未提交({})"))
    QUEUE_WAIT_TIMEOUT = EnumField("QUEUE_WAIT_TIMEOUT", _("等待超时({})"))
    QUEUE_COMMIT_EXCEPTION = EnumField("QUEUE_COMMIT_EXCEPTION", _("提交失败({})"))

    # 单据层，提单后的主体是 Ticket；填入 ticket_id
    TICKET_RUNNING = EnumField("TICKET_RUNNING", _("单据 {} 执行中"))
    TICKET_RESOURCE_REPLENISH = EnumField("TICKET_RESOURCE_REPLENISH", _("单据 {} 待补货"))
    TICKET_FAILED = EnumField("TICKET_FAILED", _("单据 {} 失败"))
    TICKET_FINISHED = EnumField("TICKET_FINISHED", _("单据 {} 已结束"))


# 事件状态的数字取法：默认数 event 条数；上报中是机器级，同一台机器的多个实例按 check_id 去重
EVENT_NUMBER_RULES: Dict[AFStateChoiceEnum, Callable[[List[MySQLDBHAEvent]], int]] = {
    AFStateChoiceEnum.EVENT_REPORTING: lambda events: len({event.check_id for event in events}),
}

# 提单后的状态，展示时填 ticket_id；提单前的状态没有单据，填数量
TICKET_STATES = {
    AFStateChoiceEnum.TICKET_RUNNING,
    AFStateChoiceEnum.TICKET_RESOURCE_REPLENISH,
    AFStateChoiceEnum.TICKET_FAILED,
    AFStateChoiceEnum.TICKET_FINISHED,
}


def resolve_queue_state(status: str) -> AFStateChoiceEnum:
    """queue 记录的 status 归并，只覆盖提单前（ticket_id=0）的场景"""
    if status == TicketQueueUncommitStatus:
        return AFStateChoiceEnum.QUEUE_UNCOMMIT
    if status == TicketQueueWaitTimeout:
        return AFStateChoiceEnum.QUEUE_WAIT_TIMEOUT
    if status == TicketQueueCommitException:
        return AFStateChoiceEnum.QUEUE_COMMIT_EXCEPTION

    raise ValueError(f"unexpected queue status without ticket: {status}")


def resolve_ticket_state(status: str) -> AFStateChoiceEnum:
    """单据状态归并，提单后的主体是 Ticket"""
    # ticket 依赖 db_meta，延迟 import 避免循环引用
    from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketStatus

    # 待补货是资源不足、需要人工介入，和执行态区分开
    if status == TicketStatus.RESOURCE_REPLENISH.value:
        return AFStateChoiceEnum.TICKET_RESOURCE_REPLENISH
    if status == TicketStatus.FAILED.value:
        return AFStateChoiceEnum.TICKET_FAILED
    # AF_TICKET_RUNNING 即 TICKET_RUNNING_STATUS_SET 加上 PENDING，FAILED 与待补货已在前面单独处理
    if status == TicketStatus.PENDING.value or status in TICKET_RUNNING_STATUS_SET:
        return AFStateChoiceEnum.TICKET_RUNNING
    if status in (TicketStatus.SUCCEEDED.value, TicketStatus.REVOKED.value, TicketStatus.TERMINATED.value):
        return AFStateChoiceEnum.TICKET_FINISHED

    raise ValueError(f"unexpected ticket status: {status}")


class DBHAAFStateField(NativeStateField):
    """集群维度的 DBHA 自愈状态：事件层、队列层、单据层归并后的取值列表"""

    key = "dbha_af_state"
    name = _("DBHA 自愈状态")
    help_text = _("DBHA 自愈状态，取自 MySQLDBHAEvent，提单后的状态取自 MySQLDBHAAutofixTicketStageQueue 及关联单据")
    value_type = StateValueType.MULTI.value
    default_value = []
    filterable = False
    writable = False
    choices = AFStateChoiceEnum.get_choices()

    @classmethod
    def abnormal_cluster_ids(cls, cluster_ids: Optional[Set[int]] = None) -> Set[int]:
        """需要关注自愈的集群：异常状态的 TenDBHA / TenDBCluster；不传 cluster_ids 时为全量"""
        clusters = Cluster.objects.using(DBMETA_READONLY).filter(
            status=ClusterStatus.ABNORMAL,
            cluster_type__in=[ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value],
        )
        if cluster_ids is not None:
            clusters = clusters.filter(pk__in=cluster_ids)
        return set(clusters.values_list("pk", flat=True))

    @classmethod
    def unavailable_instances(cls, cluster_ids: Set[int]) -> Set[Tuple[int, str, int]]:
        """异常集群下仍不可用的在线实例，(cluster_id, ip, port) 即唯一标识"""
        storage_keys = (
            StorageInstance.objects.using(DBMETA_READONLY)
            .filter(
                cluster__pk__in=cluster_ids,
                status=InstanceStatus.UNAVAILABLE,
                phase=InstancePhase.ONLINE,
            )
            .values_list("cluster__id", "machine__ip", "port")
        )
        proxy_keys = (
            ProxyInstance.objects.using(DBMETA_READONLY)
            .filter(
                cluster__pk__in=cluster_ids,
                status=InstanceStatus.UNAVAILABLE,
                phase=InstancePhase.ONLINE,
            )
            .values_list("cluster__id", "machine__ip", "port")
        )
        return set(storage_keys) | set(proxy_keys)

    @staticmethod
    def resolve_event_state(
        event: MySQLDBHAEvent,
        queued_keys: Set[Tuple[str, int, int]],
        dispatch_deadline,
    ) -> AFStateChoiceEnum:
        """单个事件的状态，四种情况各返回一种取值"""
        # validated=False：校验没通过，af_uuid 必然非空，事件属于终态，不会再被任何一轮调度
        if not event.validated:
            return AFStateChoiceEnum.EVENT_VALIDATE_FAILED

        # validated=True 且 af_uuid=""：事件已上报但未被任何一轮 schedule 认领，
        # 可能是刚上报，也可能是同机实例没报齐、被 filter_ready_events 重置回来的
        if not event.af_uuid:
            return AFStateChoiceEnum.EVENT_REPORTING

        # validated=True、af_uuid 非空，且队列里存在 (af_uuid, check_id, cluster_id) 对应的行：
        # 事件已经写入队列，后续状态由基于 queue 的状态机接管
        if (event.af_uuid, event.check_id, event.cluster_id) in queued_keys:
            return AFStateChoiceEnum.EVENT_DISPATCHED

        # validated=True、af_uuid 非空，队列里没有对应行，且 create_at 已超过 15 分钟：
        # 说明 schedule 调度过程中写队列失败，事件卡在调度阶段
        if event.create_at < dispatch_deadline:
            return AFStateChoiceEnum.EVENT_DISPATCH_TIMEOUT

        # validated=True、af_uuid 非空，队列里没有对应行，但 create_at 还在 15 分钟内：
        # 属于正常处理窗口，当前这轮 schedule 还没跑完，是过渡状态，不需要关注
        return AFStateChoiceEnum.EVENT_DISPATCHING

    def resolve_event_states(
        self,
        abnormal_cluster_ids: Set[int],
        unavailable_instance_keys: Set[Tuple[int, str, int]],
        unavailable_ips: Set[str],
    ) -> Tuple[Dict[int, Dict[str, List[MySQLDBHAEvent]]], Set[Tuple[str, int, int]]]:
        """
        事件层状态，{cluster_id: {state: [event]}}，同一状态的 event 归在一起；
        同时返回已入队事件的 (af_uuid, check_id, cluster_id)，这些事件的后续状态由队列层接管，不在事件层计值
        """
        # 先按集群和 IP 粗筛，避免拉出全部历史事件
        candidate_events = list(
            MySQLDBHAEvent.objects.using(DBMETA_READONLY).filter(
                cluster_id__in=abnormal_cluster_ids, ip__in=unavailable_ips
            )
        )

        # 已写入队列的事件，(af_uuid, check_id, cluster_id) 与事件一一对应
        queued_keys = set(
            MySQLDBHAAutofixTicketStageQueue.objects.using(DBMETA_READONLY)
            .filter(af_uuid__in={event.af_uuid for event in candidate_events if event.af_uuid})
            .values_list("af_uuid", "check_id", "cluster_id")
        )

        dispatch_deadline = timezone.now() - DISPATCH_TIMEOUT
        # {cluster_id: {state: [event]}}，同一状态的 event 收集在一起
        state_events = defaultdict(lambda: defaultdict(list))
        dispatched_keys = set()
        for event in candidate_events:
            # 事件对应的实例已经恢复，事件是历史残留，不再计入集群状态
            if (event.cluster_id, event.ip, event.port) not in unavailable_instance_keys:
                continue

            state = self.resolve_event_state(event, queued_keys, dispatch_deadline)
            # 已入队的事件，后续状态由 queue / 单据接管，不再看事件层
            if state == AFStateChoiceEnum.EVENT_DISPATCHED:
                dispatched_keys.add((event.af_uuid, event.check_id, event.cluster_id))
                continue

            state_events[event.cluster_id][state].append(event)

        return state_events, dispatched_keys

    @staticmethod
    def resolve_queue_states(dispatched_keys: Set[Tuple[str, int, int]]) -> Dict[int, Dict[str, List[str]]]:
        """
        已入队事件的队列层 / 单据层状态，{cluster_id: {state: [queue_uuid]}}。
        queue_uuid 与单据 1:1，机器共享场景下同一 queue_uuid 有多行，按 queue_uuid 去重
        """
        queue_rows = {}
        for row in (
            MySQLDBHAAutofixTicketStageQueue.objects.using(DBMETA_READONLY)
            .filter(
                af_uuid__in={af_uuid for af_uuid, _check_id, _cluster_id in dispatched_keys},
                check_id__in={check_id for _af_uuid, check_id, _cluster_id in dispatched_keys},
                cluster_id__in={cluster_id for _af_uuid, _check_id, cluster_id in dispatched_keys},
            )
            .values("queue_uuid", "af_uuid", "check_id", "cluster_id", "ticket_id", "status")
        ):
            # 同一 af_uuid / check_id 下可能挂着别的集群，按三元组精确匹配
            if (row["af_uuid"], row["check_id"], row["cluster_id"]) in dispatched_keys:
                queue_rows.setdefault(row["queue_uuid"], row)

        # 提单后 queue.status 停在 PENDING 不再更新，单据的实际进展只能看 Ticket
        ticket_status = {}
        ticket_ids = {row["ticket_id"] for row in queue_rows.values() if row["ticket_id"]}
        if ticket_ids:
            from backend.ticket.models import Ticket

            ticket_status = dict(
                Ticket.objects.using(DBMETA_READONLY).filter(id__in=ticket_ids).values_list("id", "status")
            )

        cluster_queues = defaultdict(lambda: defaultdict(list))
        for row in queue_rows.values():
            if not row["ticket_id"]:
                cluster_queues[row["cluster_id"]][resolve_queue_state(row["status"])].append(row["queue_uuid"])
                continue

            status = ticket_status.get(row["ticket_id"])
            if status is None:
                # 单据被删除属于历史脏数据，拿不到进展时跳过，避免读出错误状态
                logger.warning("dbha af queue %s ticket %s not found", row["queue_uuid"], row["ticket_id"])
                continue
            cluster_queues[row["cluster_id"]][resolve_ticket_state(status)].append(row["ticket_id"])

        return cluster_queues

    def batch_get(self, cluster_ids: List[int]) -> Dict[int, StateValue]:
        """整页集群一次读完：事件层与队列层各自归并后合并，没有事件的集群为空列表"""
        abnormal_cluster_ids = self.abnormal_cluster_ids(cluster_ids)
        unavailable_instance_keys = self.unavailable_instances(abnormal_cluster_ids)
        unavailable_ips = {ip for _, ip, _ in unavailable_instance_keys}

        event_states, dispatched_keys = self.resolve_event_states(
            abnormal_cluster_ids, unavailable_instance_keys, unavailable_ips
        )
        queue_states = self.resolve_queue_states(dispatched_keys)

        res = {}
        for cluster_id in cluster_ids:
            events_by_state = event_states[cluster_id]
            queue_items_by_state = queue_states.get(cluster_id, {})

            # 事件层：数字按 EVENT_NUMBER_RULES 取，没配置的状态默认数 event 条数
            display_texts = []
            for state, events in events_by_state.items():
                number = EVENT_NUMBER_RULES.get(state, len)(events)
                display_texts.append(str(AFStateChoiceEnum.get_choice_label(state)).format(number))

            # 队列层：提单前填数量，提单后逐张单据填 ticket_id
            for state, items in queue_items_by_state.items():
                label = str(AFStateChoiceEnum.get_choice_label(state))
                if state in TICKET_STATES:
                    display_texts.extend(label.format(ticket_id) for ticket_id in items)
                else:
                    display_texts.append(label.format(len(items)))

            res[cluster_id] = StateValue(
                value=list(events_by_state) + list(queue_items_by_state),
                display=",".join(display_texts),
            )

        return res
