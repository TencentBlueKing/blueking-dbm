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
from backend.flow.engine.bamboo.scene.mongodb.sub_task.base_subtask import BaseSubTask
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoDBNsFilter, MongoNode
from backend.flow.utils.mongodb.mongodb_util import MongoUtil


# BackupSubTask 处理某个Cluster的备份任务.
class RemoveNsSubTask(BaseSubTask):
    """
    payload: 整体的ticket_data
    sub_payload: 这个子任务的ticket_data
    rs:
    backup_dir:
    """

    @classmethod
    def make_kwargs(cls, sub_payload: Dict, exec_node: MongoNode, file_path: str) -> dict:
        ns_filter = sub_payload.get("ns_filter")
        is_partial = MongoDBNsFilter.is_partial(ns_filter)
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(exec_node.ip, exec_node.port, exec_node.bk_cloud_id)
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": exec_node.bk_cloud_id,
            "exec_ip": exec_node.ip,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.RemoveNs,
                "file_path": file_path,
                "exec_account": "root",
                "sudo_account": "mysql",
                "payload": {
                    "ip": exec_node.ip,
                    "port": int(exec_node.port),
                    "adminUsername": dba_user,
                    "adminPassword": dba_pwd,
                    "args": {
                        "drop_type": sub_payload["drop_type"],
                        "dropIndex": sub_payload["drop_index"],
                        "isPartial": is_partial,
                        "nsFilter": sub_payload["ns_filter"],
                    },
                },
            },
        }

    @classmethod
    def remove_ns(
        cls,
        root_id: str,
        ticket_data: Optional[Dict],
        sub_ticket_data: Optional[Dict],
        cluster: MongoDBCluster,
        file_path: str,
    ) -> Tuple[SubBuilder, List]:
        """
        cluster can be  a ReplicaSet or  a ShardedCluster
        """
        # 创建子流程
        sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
        acts_list = []

        connect_node = cluster.get_connect_node()
        if not connect_node:
            raise Exception("no connect node. cluster:{}".format(cluster.name))
        kwargs = cls.make_kwargs(sub_ticket_data, connect_node, file_path)
        acts_list.append(
            {
                "act_name": _("清档-{}:{}".format(connect_node.ip, connect_node.port)),
                "act_component_code": ExecJobComponent2.code,
                "kwargs": kwargs,
            }
        )
        sub_pipeline.add_act(**acts_list)

        sub_pipeline.add_parallel_acts(acts_list=acts_list)
        sub_bk_host_list = []
        for v in acts_list:
            sub_bk_host_list.append({"ip": v["kwargs"]["exec_ip"], "bk_cloud_id": v["kwargs"]["bk_cloud_id"]})

        return sub_pipeline, sub_bk_host_list

    @classmethod
    def remove_ns_act(cls, sub_ticket_data: Optional[Dict], cluster: MongoDBCluster, file_path: str) -> Dict:
        """
        cluster can be  a ReplicaSet or  a ShardedCluster
        """

        connect_node = cluster.get_connect_node()
        if not connect_node:
            raise Exception("no connect node. cluster:{}".format(cluster.name))
        kwargs = cls.make_kwargs(sub_ticket_data, connect_node, file_path)
        return {
            "act_name": _("exec {}:{}".format(connect_node.ip, connect_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": kwargs,
        }
