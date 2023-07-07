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
import copy
import logging
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.spider_recover import remote_node_rollback, spider_recover_sub_flow
from backend.flow.utils.spider.tendb_cluster_info import get_rollback_clusters_info
from backend.utils import time

logger = logging.getLogger("flow")


class TenDBRollBackDataFlow(object):
    """
    TenDB 后端节点主从成对迁移
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def tendb_rollback_data(self):
        """
        tendb rollback data
        """
        tendb_rollback_pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.data))
        clusters_info = get_rollback_clusters_info(
            source_cluster_id=self.data["source_cluster_id"], target_cluster_id=self.data["target_cluster_id"]
        )
        rollback_time = time.strptime(self.data["rollback_time"], "%Y-%m-%d %H:%M:%S")
        rollback_handler = FixPointRollbackHandler(self.data["source_cluster_id"])
        backupinfo = rollback_handler.query_latest_backup_log(rollback_time)
        ins_sub_pipeline_list = []
        for spider_node in clusters_info["target_spiders"]:
            spd_cluster = {
                "total_backupinfo": backupinfo["spider_node"],
                "file_target_path": "/data/dbbak/{}/{}".format(self.root_id, spider_node["port"]),
                "ip": spider_node["ip"],
                "port": spider_node["port"],
                "bk_cloud_id": self.data["bk_cloud_id"],
            }
            spd_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            spd_sub_pipeline.add_sub_pipeline(
                sub_flow=spider_recover_sub_flow(
                    root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=spd_cluster
                )
            )
            ins_sub_pipeline_list.append(spd_sub_pipeline.build_sub_process(sub_name=_("恢复spider节点数据")))

        for shard_id, remote_node in clusters_info["shards"].items():
            shd_cluster = {
                "new_master_ip": remote_node["new_master"]["ip"],
                "new_master_port": remote_node["new_master"]["port"],
                "new_slave_ip": remote_node["new_slave"]["ip"],
                "new_master": remote_node["new_master"],
                "new_slave": remote_node["new_slave"],
                "new_slave_port": remote_node["new_slave"]["port"],
                "master_ip": remote_node["master"]["ip"],
                "master_port": remote_node["master"]["port"],
                "slave_ip": remote_node["slave"]["ip"],
                "slave_port": remote_node["slave"]["port"],
                "master": remote_node["master"],
                "slave": remote_node["slave"],
                "backup_target_path": "/data/dbbak/{}/{}".format(self.root_id, remote_node["new_master"]["port"]),
                "cluster_id": self.data["source_cluster_id"],
                "bk_cloud_id": self.data["bk_cloud_id"],
                "total_backupinfo": backupinfo["remote_node"][shard_id],
                "rollback_time": self.data["rollback_time"],
            }

            ins_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            ins_sub_pipeline.add_sub_pipeline(
                sub_flow=remote_node_rollback(
                    root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=shd_cluster
                )
            )
            ins_sub_pipeline_list.append(ins_sub_pipeline.build_sub_process(sub_name=_("恢复remote节点数据")))
        tendb_rollback_pipeline.add_parallel_sub_pipeline(sub_flow_list=ins_sub_pipeline_list)
        tendb_rollback_pipeline.run_pipeline()
