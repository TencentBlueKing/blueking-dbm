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
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext, MongoDBCluster, ReplicaSet


# BackupSubTask 处理某个Cluster的备份任务.
class RemoveNsSubTask:
    """
    payload: 整体的ticket_data
    sub_payload: 这个子任务的ticket_data
    rs:
    backup_dir:
    """

    @classmethod
    def make_dbactuator_kwargs(cls, payload: Dict, sub_payload: Dict, rs: ReplicaSet, backup_dir: str) -> dict:
        """备份 kwargs"""
        nodes = rs.get_not_backup_nodes()
        if len(nodes) == 0:
            raise Exception("no backup node. rs:{}".format(rs.set_name))

        node = nodes[0]
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": node.bk_cloud_id,
            "exec_ip": node.ip,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.RemoveNs,
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
        cluster can be  a ReplicaSet or  a ShardedCluster
        """

        # 创建子流程
        sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
        acts_list = []
        for rs in cluster.get_shards():
            acts_list.append(
                {
                    "act_name": _("MongoDB-RemoveNs[{}]".format(rs.set_name)),
                    "act_component_code": ExecuteDBActuatorJobComponent.code,
                    "kwargs": cls.make_dbactuator_kwargs(ticket_data, sub_ticket_data, rs, backup_dir),
                }
            )

        sub_pipeline.add_parallel_acts(acts_list=acts_list)
        sub_bk_host_list = []
        for v in acts_list:
            sub_bk_host_list.append({"ip": v["kwargs"]["exec_ip"], "bk_cloud_id": v["kwargs"]["bk_cloud_id"]})

        return sub_pipeline, sub_bk_host_list
