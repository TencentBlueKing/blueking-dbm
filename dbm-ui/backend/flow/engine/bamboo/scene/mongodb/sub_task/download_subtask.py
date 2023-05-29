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

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.base_subtask import BaseSubTask
from backend.flow.plugins.components.collections.mongodb.mongo_download_backup_files import (
    MongoDownloadBackupFileComponent,
)
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, ReplicaSet


# Prepare datafile 准备数据文件
class DownloadSubTask(BaseSubTask):
    """
    payload: 整体的ticket_data
    sub_payload: 这个子任务的ticket_data
    rs:
    backup_dir:
    """

    @classmethod
    def make_kwargs(cls, payload: Dict, sub_payload: Dict, rs: ReplicaSet, file_path: str) -> dict:
        print("get_backup_node", sub_payload)
        node = rs.get_not_backup_nodes()[0]
        os_account = PayloadHandler.redis_get_os_account()
        task_id_list = [m.get("task_id") for m in sub_payload["task_ids"]]
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "bk_cloud_id": node.bk_cloud_id,
            "task_ids": task_id_list,
            "dest_ip": node.ip,
            "dest_dir": "/data/dbbak/recover_mg",
            "reason": "mongodb recover setName:{} to {}".format(rs.set_name, node.ip),
            "login_user": os_account["os_user"],
            "login_passwd": os_account["os_password"],
        }

    @classmethod
    def process_cluster(
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
        for rs in cluster.get_shards():
            kwargs = cls.make_kwargs(ticket_data, sub_ticket_data, rs, file_path)
            acts_list.append(
                {
                    "act_name": _("下载备份文件 {} {}".format(rs.set_name, kwargs["dest_ip"])),
                    "act_component_code": MongoDownloadBackupFileComponent.code,
                    "kwargs": kwargs,
                }
            )

        sub_pipeline.add_parallel_acts(acts_list=acts_list)
        sub_bk_host_list = []
        for v in acts_list:
            sub_bk_host_list.append({"ip": v["kwargs"]["dest_ip"], "bk_cloud_id": v["kwargs"]["bk_cloud_id"]})

        return sub_pipeline, sub_bk_host_list
