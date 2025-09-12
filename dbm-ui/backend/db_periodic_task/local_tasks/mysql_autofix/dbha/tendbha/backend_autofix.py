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
from backend.db_meta.models import Cluster
from backend.db_monitor.models import MySQLDBHAAutofixTicketPriority, MySQLDBHAAutofixTicketStageQueue, MySQLDBHAEvent
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
            .filter(is_stand_by=False, instance_role=InstanceRole.BACKEND_SLAVE)
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
                    priority=MySQLDBHAAutofixTicketPriority.P1.value,
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
