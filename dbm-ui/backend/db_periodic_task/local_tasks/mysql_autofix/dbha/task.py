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
import threading
import uuid
from collections import defaultdict
from datetime import timedelta
from typing import List, Set

from celery.schedules import crontab
from django.db import transaction
from django.utils import timezone

from backend.components.bkmonitorv3.client import BKMonitorV3EventApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_monitor.constants import MonitorEventType
from backend.db_monitor.dataclass import BaseEventBody, MonitorEvent
from backend.db_monitor.models import (
    MySQLDBHAAutofixTicketPriority,
    MySQLDBHAAutofixTicketStageQueue,
    MySQLDBHAEvent,
    TicketQueueUncommitStatus,
    TicketQueueWaitTimeout,
)
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha import static_validate, tendbcluster, tendbha
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.aggregate_events import aggregate_events
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.commit_ticket import commit_ticket
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.consts import AF_TICKET_RUNNING
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.filter_ready_event import filter_ready_events
from backend.ticket.constants import TicketStatus
from backend.ticket.models import Ticket

logger = logging.getLogger("celery.mysql_dbha_autofix")

mysql_dbha_af_schedule_lock = threading.Lock()


@register_periodic_task(run_every=crontab(minute="*"))
def mysql_dbha_af_tracking_tickets():
    """
    跟踪单据状态
    没必要开事务, 因为只有一次迭代求值
    """
    try:
        af_tickets = MySQLDBHAAutofixTicketStageQueue.objects.only("ticket_id", "status", "cluster_id").filter(
            status__in=AF_TICKET_RUNNING
        )
        logger.info("[tracking] found %d running tickets", af_tickets.count())
    except Exception:  # noqa
        logger.exception("[tracking] failed to query running tickets")
        return

    need_warning: List[MySQLDBHAAutofixTicketStageQueue] = []
    for aftk in af_tickets:
        try:
            tk = Ticket.objects.get(pk=aftk.ticket_id)

            tracked_status = aftk.status
            current_status = tk.status

            # 只有状态变化了才更新, 省点 qps
            if tracked_status != current_status:
                logger.info(
                    "[tracking] ticket_id=%d status changed: %s -> %s, cluster_id=%d",
                    aftk.ticket_id,
                    tracked_status,
                    current_status,
                    aftk.cluster_id,
                )
                aftk.status = tk.status
                aftk.save(update_fields=["status"])

                # 如果单据状态变成了 failed
                if current_status in [TicketStatus.FAILED, TicketStatus.RESOURCE_REPLENISH]:
                    logger.warning(
                        "[tracking] ticket_id=%d failed with status=%s, cluster_id=%d",
                        aftk.ticket_id,
                        current_status,
                        aftk.cluster_id,
                    )
                    need_warning.append(aftk)
        except Exception:  # noqa
            logger.exception(
                "[tracking] failed to process ticket_id=%d, cluster_id=%d", aftk.ticket_id, aftk.cluster_id
            )

    monitor_events = []
    for failed_tk in need_warning:
        try:
            cluster_obj = Cluster.objects.get(pk=failed_tk.cluster_id)

            monitor_events.append(
                MonitorEvent(
                    event_name=MonitorEventType.MYSQL_DBHA_AUTOFIX_TICKET_FAILED,
                    target=cluster_obj.immute_domain,
                    event=BaseEventBody(
                        content=f"{cluster_obj.immute_domain} {failed_tk.machine_type} autofix ticket failed"
                    ),
                    dimension={
                        "appid": cluster_obj.bk_biz_id,
                        "cluster_domain": cluster_obj.immute_domain,
                        "cluster_type": cluster_obj.cluster_type,
                        "bk_cloud_id": cluster_obj.bk_cloud_id,
                        "machine_type": failed_tk.machine_type,
                        "ticket_id": failed_tk.ticket_id,
                        "ticket_status": failed_tk.status,
                    },
                    timestamp=0,
                )
            )
        except Exception:  # noqa
            logger.exception("[tracking] failed to build alert for cluster_id=%d", failed_tk.cluster_id)

    if monitor_events:
        try:
            BKMonitorV3EventApi.send_event(events=monitor_events)
            logger.info("[tracking] sent %d failure alert events", len(monitor_events))
        except Exception:  # noqa
            logger.exception("[tracking] failed to send %d alert events", len(monitor_events))


def _exclude_by_cluster_ids(
    tickets: List[MySQLDBHAAutofixTicketStageQueue], blocked_cluster_ids: Set[int]
) -> List[MySQLDBHAAutofixTicketStageQueue]:
    """
    从 tickets 中排除涉及 blocked_cluster_ids 的整个 queue_uuid.

    一个 queue_uuid 代表一张自愈单据, 可能关联多个集群.
    只要其中任何一个集群命中 blocked_cluster_ids, 整个 queue_uuid 的所有行都要踢掉.
    """
    if not blocked_cluster_ids:
        return tickets

    blocked_uuids = {ut.queue_uuid for ut in tickets if ut.cluster_id in blocked_cluster_ids}
    if blocked_uuids:
        logger.info(
            "[commiter] _exclude_by_cluster_ids: blocked_cluster_ids=%s, excluded queue_uuids=%s",
            blocked_cluster_ids,
            blocked_uuids,
        )
    return [ut for ut in tickets if ut.queue_uuid not in blocked_uuids]


@register_periodic_task(run_every=crontab(minute="*"))
def mysql_dbha_af_commiter():
    """
    按优先级提交自愈单据, 核心规则:
    1. 同集群不并行 —— 集群还有自愈单在跑的, 新单据等待
    2. 高优先低优等 —— P1 涉及的集群, P2/P3 不能同时发起; P2 涉及的集群, P3 不能同时发起

    排除粒度是 queue_uuid(一张单据), 不是单行记录.
    因为一个 queue_uuid 可能对应多个集群(机器共享场景).
    """
    try:
        with transaction.atomic():
            uncommit_tickets = list(MySQLDBHAAutofixTicketStageQueue.objects.filter(status=TicketQueueUncommitStatus))

            # 超过 48 小时未提交的单据标记为超时, 不再参与调度
            timeout_threshold = timezone.now() - timedelta(hours=48)
            timed_out = [ut for ut in uncommit_tickets if ut.create_at < timeout_threshold]
            if timed_out:
                timed_out_uuids = {ut.queue_uuid for ut in timed_out}
                MySQLDBHAAutofixTicketStageQueue.objects.filter(queue_uuid__in=timed_out_uuids).update(
                    status=TicketQueueWaitTimeout
                )
                logger.warning("[commiter] timed out queue_uuids (>48h): %s", timed_out_uuids)
                uncommit_tickets = [ut for ut in uncommit_tickets if ut.queue_uuid not in timed_out_uuids]

            tickets_by_priority = defaultdict(list)
            for ut in uncommit_tickets:
                tickets_by_priority[ut.priority].append(ut)

            p1 = tickets_by_priority[MySQLDBHAAutofixTicketPriority.P1.value]
            p2 = tickets_by_priority[MySQLDBHAAutofixTicketPriority.P2.value]
            p3 = tickets_by_priority[MySQLDBHAAutofixTicketPriority.P3.value]

            logger.info(
                "[commiter] uncommit queue_uuids: p1=%s, p2=%s, p3=%s",
                [ut.queue_uuid for ut in p1],
                [ut.queue_uuid for ut in p2],
                [ut.queue_uuid for ut in p3],
            )

            # 找出还有自愈单在跑的集群
            busy_cluster_ids: Set[int] = set()
            for pt in uncommit_tickets:
                if MySQLDBHAAutofixTicketStageQueue.objects.filter(
                    status__in=AF_TICKET_RUNNING, cluster_id=pt.cluster_id
                ).exists():
                    busy_cluster_ids.add(pt.cluster_id)

            if busy_cluster_ids:
                logger.info("[commiter] clusters with unfinished autofix: %s", busy_cluster_ids)
    except Exception:  # noqa
        logger.exception("[commiter] failed during query/transaction phase")
        return

    # 第一轮排除: 集群还有自愈单在跑 → 关联的 queue_uuid 整体等待
    p1 = _exclude_by_cluster_ids(p1, busy_cluster_ids)
    p2 = _exclude_by_cluster_ids(p2, busy_cluster_ids)
    p3 = _exclude_by_cluster_ids(p3, busy_cluster_ids)
    logger.info(
        "[commiter] after busy-cluster exclusion: p1=%s, p2=%s, p3=%s",
        [ut.queue_uuid for ut in p1],
        [ut.queue_uuid for ut in p2],
        [ut.queue_uuid for ut in p3],
    )

    # 第二轮排除: 高优压低优 —— 同集群只允许最高优先级的单据提交
    p1_cluster_ids = {ut.cluster_id for ut in p1}
    p2 = _exclude_by_cluster_ids(p2, p1_cluster_ids)

    p2_cluster_ids = {ut.cluster_id for ut in p2}
    p3 = _exclude_by_cluster_ids(p3, p1_cluster_ids | p2_cluster_ids)

    logger.info(
        "[commiter] after filtering queue_uuids: p1=%s, p2=%s, p3=%s",
        [ut.queue_uuid for ut in p1],
        [ut.queue_uuid for ut in p2],
        [ut.queue_uuid for ut in p3],
    )

    # 提交单据, 故意不放在事务里 —— 创建 Ticket 是重操作, 不需要整体回滚
    commit_ticket(p1)
    commit_ticket(p2)
    commit_ticket(p3)


@register_periodic_task(run_every=crontab(minute="*"))
def mysql_dbha_af_schedule():
    """
    1. 每个 check_id 代表一台机器
    2. 每个 check_id 可能对应多个集群
    3. 每一轮自愈, 对同一批集群最多可能发起 3 个单据
        * tendbha: [proxy 重建, slave 重建, ro slave 同步关系重建]
        * tendbcluster: [spider 重建, slave 重建]
    4. 自愈单据会有互斥问题, 在某些情况下是不能同时运行的
        * tendbha: 3 类单据完全可以并行
        * tendbcluster: spider 重建必须先做完
    5. 机器共享按 machine type 对齐
        * tendbha 会出现集群 [A, B, C] 的 proxy 需要重建, 同时 [B, C] 的 slave 需要重建
        * tendbcluster 就还好, 目前实际情况好像是完全对齐
    6. 这个调度任务不实际发起单据, 因为优先级实在太难搞了
        * 拼接单据参数, 把相关信息, 带上预定的优先级写到一张表里
        * 由另一个 task 按优先级无脑发起单据

    用 uuid4 生成, uuid1 长太像了, 容易搞错
    """
    if mysql_dbha_af_schedule_lock.acquire(blocking=False):
        af_uuid = uuid.uuid4().__str__()
        try:
            logger.info("[schedule] start, af_uuid=%s", af_uuid)

            # af_uuid 字段默认是 "", 不要用 is null 查询
            # 给筛出来的 events 打上一个唯一标签, 这样 qs 的惰性求值可以模拟下事务的样子, 不会被新增的 event 污染
            # 后续新增的 event 在这一轮不可见
            tagged_count = MySQLDBHAEvent.objects.filter(af_uuid="").update(af_uuid=af_uuid, validated=True)
            logger.info("[schedule] tagged %d new events with af_uuid=%s", tagged_count, af_uuid)

            # 强制求值, 不然后面的 sql 优化简直是灾难
            candidate_events_list = list(MySQLDBHAEvent.objects.filter(af_uuid=af_uuid))
            logger.info("[schedule] candidate events: %d", len(candidate_events_list))

            before_count = len(candidate_events_list)
            candidate_events_list = static_validate.validate_event_wait_timeout(candidate_events_list)
            logger.info(
                "[schedule] after validate_event_wait_timeout: %d -> %d", before_count, len(candidate_events_list)
            )

            before_count = len(candidate_events_list)
            candidate_events_list = static_validate.validate_event_fields(candidate_events_list)
            logger.info("[schedule] after validate_event_fields: %d -> %d", before_count, len(candidate_events_list))

            before_count = len(candidate_events_list)
            candidate_events_list = static_validate.validate_target(candidate_events_list)
            logger.info("[schedule] after validate_target: %d -> %d", before_count, len(candidate_events_list))

            before_count = len(candidate_events_list)
            candidate_events_list = static_validate.validate_spec(candidate_events_list)
            logger.info("[schedule] after validate_spec: %d -> %d", before_count, len(candidate_events_list))
            # ToDo 这个没写完
            # candidate_events_list = static_validate.validate_machine_share(candidate_events_list)

            logger.info("[schedule] after all validations: %d events remain", len(candidate_events_list))

            monitor_events: List[MonitorEvent] = []
            for ev in MySQLDBHAEvent.objects.filter(af_uuid=af_uuid, validated=False):
                monitor_events.append(
                    MonitorEvent(
                        event_name=MonitorEventType.MYSQL_DBHA_AUTOFIX_VALIDATE_FAILED,
                        target=ev.ip,
                        event=BaseEventBody(content=ev.validate_memo),
                        dimension={
                            "bk_cloud_id": ev.bk_cloud_id,
                            "appid": ev.bk_biz_id,
                            "cluster_domain": ev.immute_domain,
                            "machine_type": ev.machine_type,
                            "instance_role": ev.instance_role,
                            "ip": ev.ip,
                            "port": ev.port,
                        },
                        timestamp=0,
                    )
                )

            if monitor_events:
                try:
                    BKMonitorV3EventApi.send_event(events=monitor_events)
                    logger.info("[schedule] sent %d validation failure alerts", len(monitor_events))
                except Exception:  # noqa
                    logger.exception("[schedule] failed to send %d validation failure alerts", len(monitor_events))

            # 过滤掉机器所有实例没上报全的 event
            # 被排除的 event 留给下一轮
            before_count = len(candidate_events_list)
            candidate_events_list = filter_ready_events(candidate_events_list)
            logger.info("[schedule] after filter_ready_events: %d -> %d", before_count, len(candidate_events_list))

            # 根据平台规范, standby backend 可以共享, ro slave 必须独占
            # 当 standby backend 和 ro slave 同时故障时, 因为对应的 cluster_ids 不一样
            # 会放在不同的 key 中独立返回
            # cluster_ids -> machine_type -> List[event] 字典
            agg_events = aggregate_events(candidate_events_list)
            logger.info("[schedule] aggregated into %d groups", len(agg_events))

            for k, v in agg_events.items():
                try:
                    cluster_ids = json.loads(k)
                    cluster_obj = Cluster.objects.filter(pk__in=cluster_ids).only("cluster_type").first()
                    if cluster_obj is None:
                        logger.warning("[schedule] no cluster found for cluster_ids=%s, skipping", cluster_ids)
                        continue
                    cluster_type = cluster_obj.cluster_type
                    logger.info(
                        "[schedule] processing group: cluster_ids=%s, cluster_type=%s, machine_types=%s",
                        cluster_ids,
                        cluster_type,
                        list(v.keys()),
                    )
                    if cluster_type == ClusterType.TenDBSingle:
                        pass
                    elif cluster_type == ClusterType.TenDBHA:
                        tendbha.autofix(cluster_ids=cluster_ids, events_by_machine_type=v)
                    elif cluster_type == ClusterType.TenDBCluster:
                        tendbcluster.autofix(cluster_ids=cluster_ids, events_by_machine_type=v)
                    else:
                        logger.warning(
                            "[schedule] unexpected cluster_type=%s for cluster_ids=%s, skipping",
                            cluster_type,
                            cluster_ids,
                        )
                except Exception:  # noqa
                    logger.exception("[schedule] failed to process group: cluster_ids_key=%s", k)

            logger.info("[schedule] done, af_uuid=%s", af_uuid)
        except Exception:  # noqa
            logger.exception("[schedule] unexpected error, af_uuid=%s", af_uuid)
        finally:
            mysql_dbha_af_schedule_lock.release()
    else:
        logger.warning("[schedule] lock not acquired, previous run still in progress")
