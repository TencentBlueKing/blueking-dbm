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
from typing import List

from django.db import transaction

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_monitor.models import (
    MySQLDBHAAutofixTicketPriority,
    MySQLDBHAAutofixTicketStageQueue,
    MySQLDBHAEvent,
    TicketQueueUncommitStatus,
)
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha import static_validate, tendbha
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.aggregate_events import aggregate_events
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.commit_ticket import commit_ticket
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.filter_ready_event import filter_ready_events
from backend.ticket.constants import TicketFlowStatus
from backend.ticket.models import Ticket

logger = logging.getLogger("celery")

mysql_dbha_af_schedule_lock = threading.Lock()


# @register_periodic_task(run_every=crontab(minute="*"))
def mysql_dbha_af_tracking_tickets():
    """
    跟踪单据状态
    没必要开事务, 因为只有一次迭代求值
    """
    af_tickets = MySQLDBHAAutofixTicketStageQueue.objects.only("ticket_id", "status").filter(
        status__in=[TicketFlowStatus.PENDING, TicketFlowStatus.RUNNING, TicketFlowStatus.FAILED]
    )
    for aftk in af_tickets:
        tk = Ticket.objects.get(pk=aftk.ticket_id)
        aftk.status = tk.status
        aftk.save(update_fields=["status"])


# @transaction.atomic
# @register_periodic_task(run_every=crontab(minute="*"))
def mysql_dbha_af_commiter():
    """
    这个函数理论上还挺快的, 应该可以开个事务

    优先级排序还挺复杂的, 单独用一个 task 来做吧
    代码简单些不会烧脑
    共享对齐的原因就是在这里了
    假设有集群
    (A, (B), (C), D)
    这样奇葩的共享机器, 就有点不好搞怎么发起修复单据了
    """
    with transaction.atomic():
        uncommit_tickets = list(MySQLDBHAAutofixTicketStageQueue.objects.filter(status=TicketQueueUncommitStatus))

        # 简单点, 先只考虑只有 p1, p2 的情况
        p1_uncommit_tickets: List[MySQLDBHAAutofixTicketStageQueue] = []
        p2_uncommit_tickets: List[MySQLDBHAAutofixTicketStageQueue] = []
        for ut in uncommit_tickets:
            if ut.priority == MySQLDBHAAutofixTicketPriority.P1.value:
                p1_uncommit_tickets.append(ut)
            elif ut.priority == MySQLDBHAAutofixTicketPriority.P2.value:
                p2_uncommit_tickets.append(ut)
            else:
                raise Exception(ut.priority)

        # 找出还有未完成自愈的集群
        unfinish_cluster_ids = []
        for pt in uncommit_tickets:
            t = MySQLDBHAAutofixTicketStageQueue.objects.filter(
                status__in=[TicketFlowStatus.PENDING, TicketFlowStatus.RUNNING, TicketFlowStatus.FAILED],
                cluster_id=pt.cluster_id,
            )
            if t.exists():
                unfinish_cluster_ids.append(pt.cluster_id)

    # 排除不能只按 cluster_id 排除
    # 得按 queue_uuid 来
    # 因为 queue_uuid 代表唯一的自愈单据
    # 而一个 queue_uuid 可能对应多个集群
    # 所以得用未完成的 cluster_id 反查到关联的待提交单据, 也就是 queue_uuid
    relate_p1_queue_uuid = [ut.queue_uuid for ut in p1_uncommit_tickets if ut.cluster_id in unfinish_cluster_ids]
    p1_uncommit_tickets = [ut for ut in p1_uncommit_tickets if ut.queue_uuid not in relate_p1_queue_uuid]

    relate_p2_queue_uuid = [ut.queue_uuid for ut in p2_uncommit_tickets if ut.cluster_id in unfinish_cluster_ids]
    p2_uncommit_tickets = [ut for ut in p2_uncommit_tickets if ut.queue_uuid not in relate_p2_queue_uuid]

    # 从 p2 里排除掉 p1 相关集群
    p1_relate_cluster_ids = [ut.cluster_id for ut in p1_uncommit_tickets]
    priority_exclude_uuid = [ut.queue_uuid for ut in p2_uncommit_tickets if ut.cluster_id in p1_relate_cluster_ids]
    p2_uncommit_tickets = [ut for ut in p2_uncommit_tickets if ut.queue_uuid not in priority_exclude_uuid]

    # 到这里, p1, p2 应该可以无脑发起单据了
    # 不要放到事务里面去
    commit_ticket(p1_uncommit_tickets)
    commit_ticket(p2_uncommit_tickets)


# @register_periodic_task(run_every=crontab(minute="*"))
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
        try:
            af_uuid = uuid.uuid4().__str__()
            # af_uuid 字段默认是 "", 不要用 is null 查询
            # 给筛出来的 events 打上一个唯一标签, 这样 qs 的惰性求值可以模拟下事务的样子, 不会被新增的 event 污染
            # 后续新增的 event 在这一轮不可见
            MySQLDBHAEvent.objects.filter(af_uuid="").update(af_uuid=af_uuid)

            # 强制求值, 不然后面的 sql 优化简直是灾难
            candidate_events_list = list(MySQLDBHAEvent.objects.filter(af_uuid=af_uuid))

            candidate_events_list = static_validate.validate_event_wait_timeout(candidate_events_list)
            candidate_events_list = static_validate.validate_event_fields(candidate_events_list)
            candidate_events_list = static_validate.validate_target(candidate_events_list)
            # ToDo 这个没写完
            # candidate_events_list = static_validate.validate_machine_share(candidate_events_list)

            MySQLDBHAEvent.objects.filter(af_uuid=af_uuid).update(validated=True)

            # 过滤掉机器所有实例没上报全的 event
            # 被排除的 event 留给下一轮
            candidate_events_list = filter_ready_events(candidate_events_list)

            # cluster_ids -> machine_type -> List[event] 字典
            agg_events = aggregate_events(candidate_events_list)

            for k, v in agg_events.items():
                cluster_ids = json.loads(k)
                cluster_type = Cluster.objects.filter(pk__in=cluster_ids).only("cluster_type").first().cluster_type
                if cluster_type == ClusterType.TenDBSingle:
                    pass
                elif cluster_type == ClusterType.TenDBHA:
                    tendbha.autofix(cluster_ids=cluster_ids, events_by_machine_type=v)
                elif cluster_type == ClusterType.TenDBCluster:
                    pass
                else:
                    pass  # 这里理论上是到达不了的
        finally:
            mysql_dbha_af_schedule_lock.release()
    else:
        raise  # Todo 居然没跑完, 为啥这么慢
