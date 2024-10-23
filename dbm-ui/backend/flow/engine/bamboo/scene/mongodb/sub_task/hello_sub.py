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
from backend.flow.utils.mongodb.mongodb_repo import MongoNode, ReplicaSet
from backend.flow.utils.mongodb.mongodb_util import MongoUtil


# HelloSubTask 测试用，总是返回成功.
class HelloSubTask(BaseSubTask):
    """
    payload: 整体的ticket_data
    sub_payload: 这个子任务的ticket_data
    rs:
    """

    @classmethod
    def make_kwargs(cls, file_path, exec_node: MongoNode) -> dict:
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(exec_node.ip, exec_node.port, exec_node.bk_cloud_id)
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": exec_node.bk_cloud_id,
            "exec_ip": exec_node.ip,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoHello,
                "file_path": file_path,
                "exec_account": "root",
                "sudo_account": "mysql",
                "payload": {
                    "ip": exec_node.ip,
                    "port": int(exec_node.port),
                    "adminUsername": dba_user,
                    "adminPassword": dba_pwd,
                },
            },
        }

    @classmethod
    def process_node(
        cls,
        root_id: str,
        ticket_data: Optional[Dict],
        sub_ticket_data: Optional[Dict],
        file_path,
        exec_node: MongoNode,
        sub_pipeline: SubBuilder,
        act_name: str,
    ) -> SubBuilder:
        """
        cluster can be  a ReplicaSet or  a ShardedCluster
        """

        # 创建子流程
        if sub_pipeline is None:
            sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

        kwargs = cls.make_kwargs(file_path, exec_node)
        act = {
            "act_name": _("{} {}:{}".format(act_name, exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": kwargs,
        }
        sub_pipeline.add_act(**act)
        return sub_pipeline

    @classmethod
    def process_shard(
        cls,
        root_id: str,
        ticket_data: Optional[Dict],
        sub_ticket_data: Optional[Dict],
        shard: ReplicaSet,
        file_path,
        dest_dir: str,
        exec_node: MongoNode,
        sub_pipeline: SubBuilder,
    ) -> Tuple[SubBuilder, List]:
        """
        cluster can be  a ReplicaSet or  a ShardedCluster
        """

        # 创建子流程
        if sub_pipeline is None:
            sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

        kwargs = cls.make_kwargs(sub_ticket_data, shard, file_path, dest_dir, exec_node)
        act = {
            "act_name": _("Hello {}:{}".format(exec_node.ip, exec_node.port)),
            "act_component_code": ExecJobComponent2.code,
            "kwargs": kwargs,
        }
        sub_pipeline.add_act(**act)
        return sub_pipeline
