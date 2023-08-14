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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import RollbackType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBackupInfoFailedException
from backend.flow.engine.bamboo.scene.spider.spider_recover import remote_node_rollback, spider_recover_sub_flow
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs
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
        # 先查询恢复介质
        # todo 备份查不到的问题
        rollback_time = time.strptime(self.data["rollback_time"], "%Y-%m-%d %H:%M:%S")
        rollback_handler = FixPointRollbackHandler(self.data["source_cluster_id"])
        if self.data["rollback_type"] == RollbackType.REMOTE_AND_BACKUPID.value:
            backup_info = self.data["backupinfo"]
        else:
            backup_info = rollback_handler.query_latest_backup_log(rollback_time)
            if backup_info is None:
                logger.error("cluster {} backup info not exists".format(self.data["source_cluster_id"]))
                raise TendbGetBackupInfoFailedException(
                    message=_("获取实例 {} 的备份信息失败".format(self.data["source_cluster_id"]))
                )

        # 下发 actuator
        tendb_rollback_pipeline.add_act(
            act_name=_("下发actuator工具 {}".format(clusters_info["ip_list"])),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=self.data["bk_cloud_id"],
                    exec_ip=clusters_info["ip_list"],
                    file_list=GetFileList(DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        ins_sub_pipeline_list = []
        for spider_node in clusters_info["target_spiders"]:
            spd_cluster = {
                "backupinfo": backup_info["spider_node"],
                # "file_target_path": "/data/dbbak/{}/{}".format(self.root_id, spider_node["port"]),
                "file_target_path": "/home/mysql/install",
                "rollback_ip": spider_node["ip"],
                "rollback_port": spider_node["port"],
                "instance": spider_node["instance"],
                "bk_cloud_id": self.data["bk_cloud_id"],
                "cluster_id": self.data["source_cluster_id"],
                "rollback_time": self.data["rollback_time"],
                "rollback_type": self.data["rollback_type"],
            }
            spd_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            spd_sub_pipeline.add_sub_pipeline(
                sub_flow=spider_recover_sub_flow(
                    root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster=spd_cluster
                )
            )
            ins_sub_pipeline_list.append(spd_sub_pipeline.build_sub_process(sub_name=_("恢复spider节点数据")))
        for shard_id, remote_node in clusters_info["shards"].items():
            shd_cluster = {
                "shard_id": shard_id,
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
                # "file_target_path": "/data/dbbak/{}/{}".format(self.root_id, remote_node["new_master"]["port"]),
                "file_target_path": "/home/mysql/install",
                "cluster_id": self.data["source_cluster_id"],
                "bk_cloud_id": self.data["bk_cloud_id"],
                "backupinfo": backup_info["remote_node"][str(shard_id)],
                "rollback_time": self.data["rollback_time"],
                "rollback_type": self.data["rollback_type"],
            }

            ins_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            ins_sub_pipeline.add_sub_pipeline(
                sub_flow=remote_node_rollback(
                    root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster=shd_cluster
                )
            )
            ins_sub_pipeline_list.append(ins_sub_pipeline.build_sub_process(sub_name=_("恢复remote节点数据")))
        tendb_rollback_pipeline.add_parallel_sub_pipeline(sub_flow_list=ins_sub_pipeline_list)
        tendb_rollback_pipeline.run_pipeline()
