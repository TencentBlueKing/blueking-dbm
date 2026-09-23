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
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.db_services.mongodb.restore.handlers import MongoDBRestoreHandler, to_pitr_task_ids
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.base_subtask import BaseSubTask
from backend.flow.plugins.components.collections.mongodb.mongo_fetch_pitr_backup_records import (
    MongoFetchPitrBackupRecordsComponent,
)
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
    def process_cluster(
        cls,
        root_id: str,
        ticket_data: Optional[Dict],
        sub_ticket_data: Optional[Dict],
        src_cluster: MongoDBCluster,
        src_shards: List[ReplicaSet],
        sub_pipeline: SubBuilder,
    ):
        """在 restore_shards 之前插入一个节点：一次性查询所有分片的备份记录。"""
        kwargs = {
            "set_trans_data_dataclass": CommonContext.__name__,
            "src_cluster_id": src_cluster.cluster_id,
            "dst_time": sub_ticket_data["dst_time"],
            "set_names": [shard.set_name for shard in src_shards],
        }
        sub_pipeline.add_act(
            act_name=_("查询备份记录 {} shards").format(len(kwargs["set_names"])),
            act_component_code=MongoFetchPitrBackupRecordsComponent.code,
            kwargs=kwargs,
        )

    @classmethod
    def process_shard(
        cls,
        root_id: str,
        ticket_data: Optional[Dict],
        sub_ticket_data: Optional[Dict],
        cluster: MongoDBCluster,
        shard: ReplicaSet,
    ):
        """保留给单据校验等单分片查询。PITR flow 构建期不再调用。"""
        cluster_id = cluster.cluster_id
        shard_name = shard.set_name
        ret = cls.fetch_backup_record(cluster_id, shard_name, sub_ticket_data["dst_time"])
        full = ret["full_backup_log"]
        sub_ticket_data["task_ids"] = to_pitr_task_ids(full, ret["incr_backup_logs"])
        return

    @classmethod
    def fetch_backup_record(cls, cluster_id, shard_name, dst_time_str: str):
        dst_time = time.str2datetime(dst_time_str)
        rec = MongoDBRestoreHandler(cluster_id).query_latest_backup_log(dst_time, shard_name)
        return rec
