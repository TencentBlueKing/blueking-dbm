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
import logging
from typing import Dict, List, Optional, Tuple

from backend.db_services.mongodb.restore.handlers import MongoDBRestoreHandler
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.base_subtask import BaseSubTask
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, ReplicaSet
from backend.utils import time

# FetchBackupFile 获得备份记录
logger = logging.getLogger("flow")


class FetchBackupRecordSubTask(BaseSubTask):
    """
    payload: 整体的ticket_data
    sub_payload: 这个子任务的ticket_data
    rs:
    backup_dir:
    """

    @classmethod
    def make_kwargs(cls, payload: Dict, sub_payload: Dict, rs: ReplicaSet, file_path, dest_dir: str) -> dict:
        print("get_backup_node", sub_payload)
        node = rs.get_not_backup_nodes()[0]
        os_account = PayloadHandler.redis_get_os_account()
        task_id_list = [m.get("task_id") for m in sub_payload["task_ids"]]
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "bk_cloud_id": node.bk_cloud_id,
            "task_ids": task_id_list,
            "dest_ip": node.ip,
            "dest_dir": dest_dir,
            "reason": "mongodb recover setName:{} to {}".format(rs.set_name, node.ip),
            "login_user": os_account["os_user"],
            "login_passwd": os_account["os_password"],
        }

    @classmethod
    def process_shard(
        cls,
        root_id: str,
        ticket_data: Optional[Dict],
        sub_ticket_data: Optional[Dict],
        cluster: MongoDBCluster,
        shard: ReplicaSet,
    ) -> Tuple[SubBuilder, List]:
        """
        cluster can be  a ReplicaSet or  a ShardedCluster
        """

        cluster_id = cluster.cluster_id
        shard_name = shard.set_name
        ret = cls.fetch_backup_record(cluster_id, shard_name, sub_ticket_data["dst_time"])
        full = ret["full_backup_log"]
        backup_record = [
            {
                "task_id": full["bs_taskid"],
                "file_name": full["file_name"],
                "instance": "{}:{}".format(full["ip"], full["port"]),
            }
        ]
        for incr_log in ret["incr_backup_logs"]:
            backup_record.append(
                {
                    "task_id": incr_log["bs_taskid"],
                    "file_name": incr_log["file_name"],
                    "instance": "{}:{}".format(full["ip"], full["port"]),
                }
            )

        sub_ticket_data["task_ids"] = backup_record

        return

    @classmethod
    def fetch_backup_record(cls, cluster_id, shard_name, dst_time_str: str):
        # fetch_backup_record 目前只能处理replicaset的。 todo : 兼容sharded cluster
        dst_time = time.str2datetime(dst_time_str)
        rec = MongoDBRestoreHandler(cluster_id).query_latest_backup_log(dst_time, shard_name)
        # return {"full_backup_log": latest_full_backup_log, "incr_backup_logs": incr_backup_logs}
        return rec
