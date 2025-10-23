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
import uuid
from typing import List

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, Machine, StorageInstance
from backend.db_monitor.models import MySQLDBHAAutofixTicketPriority, MySQLDBHAAutofixTicketStageQueue, MySQLDBHAEvent
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.flow.consts import InstanceStatus
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.constants import TicketType


def repair_ro_slaves_replicate(cluster_ids: List[int], machine_type: str, events: List[MySQLDBHAEvent]):
    """
    events 的 check_id 应该是相同的
    表示 cluster_ids 的 master 发生了 dbha
    """
    # 有可能, 共享了 master 机器的集群, 只有部分存在 ro slave
    infos = []
    for ev in events:
        cluster_obj = Cluster.objects.only("pk", "bk_cloud_id").get(pk=ev.cluster_id, cluster_type=ev.cluster_type)
        ro_slaves = (
            cluster_obj.storageinstance_set.select_related("machine")
            .only("port", "machine__ip")
            .filter(is_stand_by=False, instance_role=InstanceRole.BACKEND_SLAVE, status=InstanceStatus.RUNNING)
        )
        if ro_slaves.exists():
            # 不需要考虑一个集群有多个 event 的情况, 因为只会有一个 master
            # 机器连续挂时, 第二次 dbha 是失败的, 不会触发自愈
            # ToDo 理论上, 这里应该检查下 cluster 当前的 master 是不是真的和 event 的 new_master_xx 相同
            infos.append(
                {
                    "bk_cloud_id": cluster_obj.bk_cloud_id,
                    "cluster_id": cluster_obj.pk,
                    "new_master_address": cluster_obj.storageinstance_set.select_related("machine")
                    .only("port", "machine__ip")
                    .get(is_stand_by=True, instance_role=InstanceRole.BACKEND_MASTER)
                    .ip_port,
                    "new_master_log_file": ev.new_master_log_file,
                    "new_master_log_pos": ev.new_master_log_pos,
                    "old_master_address": f"{ev.ip}:{ev.port}",
                    "ro_slave_addresses": [rs.ip_port for rs in ro_slaves],
                    "check_id": ev.check_id,
                }
            )

    if infos:
        dbas = events[0].dbas()
        queue_uuid = uuid.uuid4().__str__()
        ticket_param = {
            "ticket_type": TicketType.MYSQL_DBHA_AF_REPAIR_REPLICATE,
            "creator": dbas[0],
            "helpers": dbas[1:],
            "bk_biz_id": events[0].bk_biz_id,
            "remark": TicketType.MYSQL_DBHA_AF_REPAIR_REPLICATE,
            "details": {"bk_cloud_id": events[0].bk_cloud_id, "infos": infos},
        }

        queue_to_create = []
        for ele in infos:
            queue_to_create.append(
                MySQLDBHAAutofixTicketStageQueue(
                    priority=MySQLDBHAAutofixTicketPriority.P2.value,
                    check_id=ele["check_id"],
                    cluster_id=ele["cluster_id"],
                    machine_type=machine_type,
                    ticket_param=ticket_param,
                    af_uuid=events[0].af_uuid,
                    queue_uuid=queue_uuid,
                )
            )

        # ToDo 异常处理 ?
        MySQLDBHAAutofixTicketStageQueue.objects.bulk_create(queue_to_create)


def replace_slave(cluster_ids: List[int], machine_type: str, events: List[MySQLDBHAEvent]):
    """
    根据平台规范, ro slave 机器必须整机被集群独占, 不存在多实例部署的情况
    如果一台 standby slave 机器和 一台 ro slave 机器同时需要重建
    1. 如果 standby 和 ro 都是独占的, 这里会有 2 台机器的输入
    2. 如果 standby 被共享, 这个函数会被独立调用 2 次

    还有一种情况, 一个集群有 2 台 ro slave 需要重建, 也会有 2 台机器输入

    综合上面的情况, 单据这样安排比较合理
    1. 如果输入是 standby + ro, 可以一个单据重建, 优先级 P2
    2. 如果输入只有 standby, 优先级 P2
    3. 如果输入只有 ro, 可以一个单据重建, 优先级 P3

    ToDo
    这里的单据构造, 仅仅做到了能支持 ro slave 的自愈
    但是当 ro 组这个概念落地, 而且要在组内维持亲和的时候
    这个构造逻辑是不对的
    """
    # 输入的 bk_cloud_id 肯定都是一样的
    bk_cloud_id = events[0].bk_cloud_id
    ips = list({ev.ip for ev in events})
    standby_ro_flags = list(
        set(
            StorageInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip__in=ips).values_list(
                "is_stand_by", flat=True
            )
        )
    )

    if len(standby_ro_flags) == 2:  # standby + ro
        priority = MySQLDBHAAutofixTicketPriority.P2
    else:
        if standby_ro_flags[0]:  # only standby
            priority = MySQLDBHAAutofixTicketPriority.P2
        else:  # only ro
            priority = MySQLDBHAAutofixTicketPriority.P3

    infos = []
    for ip in ips:
        machine_obj = Machine.objects.get(bk_cloud_id=bk_cloud_id, ip=ip)
        ip_events = [ev for ev in events if ev.ip == ip]
        info = {
            "old_nodes": {"old_slave": []},
            "resource_spec": {"new_slave": {"count": 1, "spec_id": machine_obj.spec_id}},
            "cluster_ids": cluster_ids,
        }

        old_slaves = []
        for ev in ip_events:
            old_slaves.append(
                {
                    "bk_biz_id": ev.bk_biz_id,
                    "bk_cloud_id": bk_cloud_id,
                    "bk_host_id": machine_obj.bk_host_id,
                    "ip": ev.ip,
                    # "port": ev.port
                }
            )

        info["old_nodes"]["old_slave"] = old_slaves
        infos.append(info)

    dbas = events[0].dbas()
    queue_uuid = uuid.uuid4().__str__()
    ticket_param = {
        "ticket_type": TicketType.MYSQL_DBHA_AF_BACKEND_REPLACE,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "bk_biz_id": events[0].bk_biz_id,
        "remark": TicketType.MYSQL_DBHA_AF_BACKEND_REPLACE,
        "details": {
            "bk_cloud_id": events[0].bk_cloud_id,
            "bk_biz_id": events[0].bk_biz_id,
            "backup_source": MySQLBackupSource.REMOTE,
            "ip_source": IpSource.RESOURCE_POOL,
            "source_type": SourceType.RESOURCE_AUTO,
            "ip_recycle": HostRecycleSerializer.DEFAULT,
            "disable_manual_confirm": True,
            "infos": infos,
        },
    }

    queue_to_create = []
    for ev in events:
        queue_to_create.append(
            MySQLDBHAAutofixTicketStageQueue(
                priority=priority,
                check_id=ev.check_id,
                cluster_id=ev.cluster_id,
                machine_type=machine_type,
                ticket_param=ticket_param,
                af_uuid=ev.af_uuid,
                queue_uuid=queue_uuid,
            )
        )

    MySQLDBHAAutofixTicketStageQueue.objects.bulk_create(queue_to_create)
