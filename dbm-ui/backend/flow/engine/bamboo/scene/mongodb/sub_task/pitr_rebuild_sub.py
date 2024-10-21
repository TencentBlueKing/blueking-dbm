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

from backend.flow.consts import MongoDBActuatorActionEnum
from backend.flow.engine.bamboo.scene.mongodb.sub_task.base_subtask import BaseSubTask
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoNode
from backend.flow.utils.mongodb.mongodb_util import MongoUtil


# PitrRebuildSubTask 重新构建集群
class PitrRebuildSubTask(BaseSubTask):
    """
    payload: 整体的ticket_data
    sub_payload: 这个子任务的ticket_data
    rs:
    """

    @classmethod
    def make_kwargs(cls, file_path, exec_node: MongoNode, src_shard, dst_shard, src_cluster, dst_cluster) -> dict:
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(exec_node.ip, exec_node.port, exec_node.bk_cloud_id)
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": exec_node.bk_cloud_id,
            "exec_ip": exec_node.ip,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.MongoPitrRebuild,
                "file_path": file_path,
                "exec_account": "root",
                "sudo_account": "mysql",
                "payload": {
                    "ip": exec_node.ip,
                    "port": int(exec_node.port),
                    "adminUsername": dba_user,
                    "adminPassword": dba_pwd,
                    "src_cluster": src_cluster.__json__(),
                    "dst_cluster": dst_cluster.__json__(),
                    "src_shard": src_shard.__json__(),
                    "dst_shard": dst_shard.__json__(),
                },
            },
        }
