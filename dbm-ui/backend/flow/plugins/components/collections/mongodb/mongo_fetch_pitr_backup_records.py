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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.mongodb.mongodb_dataclass as flow_context
from backend.db_services.mongodb.restore.handlers import MongoDBRestoreHandler, to_pitr_task_ids
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.utils import time


class MongoFetchPitrBackupRecords(BaseService):
    """查询源集群各分片的全备+增量链，写入 trans_data.pitr_backup_records。

    把 BKLog 查询从 flow 构建期挪到运行期的一个节点，避免分片数多时串行打日志平台拖慢 pipeline 生成。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        cluster_id = kwargs["src_cluster_id"]
        dst_time = kwargs["dst_time"]
        set_names = kwargs["set_names"]
        picked = MongoDBRestoreHandler(cluster_id).query_latest_backup_logs_by_sets(
            time.str2datetime(dst_time), set_names
        )
        records = {}
        for set_name, rec in picked.items():
            task_ids = to_pitr_task_ids(rec["full_backup_log"], rec["incr_backup_logs"])
            records[set_name] = {"task_ids": task_ids}
        trans_data.set("pitr_backup_records", records)
        data.outputs["trans_data"] = trans_data
        for set_name, rec in records.items():
            self.log_info(
                "pitr backup {} full={} incr={}".format(
                    set_name, rec["task_ids"][0]["file_name"], len(rec["task_ids"]) - 1
                )
            )
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoFetchPitrBackupRecordsComponent(Component):
    name = __name__
    code = "mongo_fetch_pitr_backup_records"
    bound_service = MongoFetchPitrBackupRecords
