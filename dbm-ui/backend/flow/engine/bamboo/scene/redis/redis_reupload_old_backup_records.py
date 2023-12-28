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

import logging.config

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.redis.atom_jobs.reupload_old_backup_records import (
    RedisReuploadOldBackupRecordsAtomJob,
)
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisReuploadOldBackupRecordsFlow(object):
    """
    redis 重新上报备份记录
    self.data (Dict):
    {
        "uid": "2022051612120001",
        "created_by":"admin",
        "ticket_type":"REDIS_SLOTS_MIGRATE",
        "bk_biz_id": "3",
        "bk_cloud_id": 0,
        "cluster_domain":"cache.test.test.db",
        "cluster_type":"TwemproxyRedisInstance",
        "server_shards":{
            "a.a.a.a:30000":"0-14999",
            "a.a.a.a:30001":"15000-29999",
            "a.a.a.a:30002":"30000-44999"
        },
        "ndays": 7,
        "infos":[
            {
                "server_ip": "a.a.a.a",
                "server_ports":[30000,30001,30002],
                "meta_role":"redis_slave"
            },
            {
                "server_ip": "b.b.b.b",
                "server_ports":[30000,30001,30002],
                "meta_role":"redis_slave"
            }
        ]
    }
    """

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data

    def reupload_old_backup_records_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True
            act_kwargs.cluster = {}
            sub_pipelines.append(
                RedisReuploadOldBackupRecordsAtomJob(
                    self.root_id,
                    self.data,
                    act_kwargs,
                    {
                        "bk_biz_id": self.data["bk_biz_id"],
                        "bk_cloud_id": self.data["bk_cloud_id"],
                        "server_ip": info["server_ip"],
                        "server_ports": info["server_ports"],
                        "cluster_domain": self.data["cluster_domain"],
                        "cluster_type": self.data["cluster_type"],
                        "meta_role": info["meta_role"],
                        "server_shards": self.data["server_shards"],
                        "ndays": self.data["ndays"],
                    },
                )
            )
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
