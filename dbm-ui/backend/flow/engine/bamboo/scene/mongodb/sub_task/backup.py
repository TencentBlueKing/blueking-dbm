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

from typing import Dict, List, Optional, Tuple

from django.utils.translation import ugettext as _

from backend.flow.consts import MongoDBActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext, MongoDBCluster, ReplicaSet


# BackupSubTask 处理某个Cluster的备份任务.
class BackupSubTask:
    """
    payload: 整体的ticket_data
    sub_payload: 这个子任务的ticket_data
    rs:
    backup_dir:
    """

    def __init__(self):
        pass

    @classmethod
    def make_kwargs(cls, payload: Dict, sub_payload: Dict, rs: ReplicaSet, backup_dir: str) -> dict:
        """备份 kwargs"""
        print("get_backup_node", sub_payload)
        node = rs.get_backup_node()
        if node is None:
            raise Exception("no backup node. rs:{}".format(rs.set_name))

        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": node.bk_cloud_id,
            "exec_ip": node.ip,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.Backup,
                "backup_dir": backup_dir,
                "payload": {
                    "ip": node.ip,
                    "port": node.port,
                    "user": "root",
                    "pass": "root",
                    "authDb": "admin",
                    "ns_filter": sub_payload["ns_filter"],
                },
            },
        }

    @classmethod
    def process_cluster(
        cls,
        root_id: str,
        ticket_data: Optional[Dict],
        sub_ticket_data: Optional[Dict],
        cluster: MongoDBCluster,
        backup_dir: str,
    ) -> Tuple[SubBuilder, List]:
        """
        backup a ReplicaSet or backup a ShardedCluster
        """

        # 创建子流程
        sb = SubBuilder(root_id=root_id, data=ticket_data)
        acts_list = []
        for rs in cluster.get_shards():
            acts_list.append(
                {
                    "act_name": _("MongoDB备份[{}]".format(rs.set_name)),
                    "act_component_code": ExecuteDBActuatorJobComponent.code,
                    "kwargs": cls.make_kwargs(ticket_data, sub_ticket_data, rs, backup_dir),
                }
            )

        sb.add_parallel_acts(acts_list=acts_list)
        sub_bk_host_list = []
        for v in acts_list:
            sub_bk_host_list.append({"ip": v["kwargs"]["exec_ip"], "bk_cloud_id": v["kwargs"]["bk_cloud_id"]})

        return sb, sub_bk_host_list
