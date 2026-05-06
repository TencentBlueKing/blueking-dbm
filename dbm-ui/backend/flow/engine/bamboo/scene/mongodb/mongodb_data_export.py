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
import os
from collections import defaultdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_proxy.models import DBExtension, ExtensionType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.data_export import DataExportSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository
from backend.flow.utils.mongodb.mongodb_util import MongoUtil

logger = logging.getLogger("flow")


class MongoDataExportFlow(object):
    """
    MongoDB数据导出flow

    Flow流程:
        ┌─────────────────────────────────────────────┐
        │   parse_infos()                             │
        │  1. 解析 infos 验证集群                       │
        │  2. 为集群选择访问节点                         │
        │     - ReplicaSet: shard[0] non-backup node  │
        │     - ShardedCluster: mongos[0]             │
        │  3. MongoDB 数据导出中心 IP                   │
        │  4. 获取集群版本用于介质下发                    │
        └─────────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  export_flow()        │
                    │  - Send media         │
                    │  - Export Clusters    │
                    └───────────────────────┘
                                │ Sequentially
                ┌───────────────┴───────────────┐
                ▼                               ▼
        ┌──────────────────┐          ┌──────────────────┐
        │ Cluster 1 Export │          │ Cluster N Export │
        │ SubFlow          │   ...    │ SubFlow          │
        └──────────────────┘          └──────────────────┘
                │                               │
                └───────────────┬───────────────┘
                                ▼
                  ┌──────────────────────────────┐
                  │ DataExportSubTask            │
                  │ .export_cluster_sub_flow()   │
                  │ - Make kwargs                │
                  │ - ExecJobComponent2          │
                  └──────────────────────────────┘

    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        """
        self.root_id = root_id
        self.data = data
        self.center_require_versions = defaultdict(set)
        self.cluster_tasks = {}
        self.parse_infos()

    def parse_infos(self):
        """
        将 infos 解析为 {export_center: {cluster: task_info, version_pkgs: pkgs}}
        """
        get_file_list = GetFileList(db_type=DBType.MongoDB)
        for info in self.data.get("infos", []):
            cluster_id = info["cluster_id"]
            cluster = MongoRepository.fetch_one_cluster(id=cluster_id)
            if not cluster:
                raise Exception(_(f"Cluster not found, id: {cluster_id}"))
            if cluster in self.cluster_tasks:
                raise Exception(_(f"Duplicate cluster_id found: {cluster_id}"))
            MongoBaseFlow.check_cluster_valid(cluster, self.data)

            access_node = self.__get_access_node(cluster)
            export_center_ip = self.__get_export_center_ip(cluster.bk_cloud_id)
            pkgs = get_file_list.mongodb_pkg(db_version=cluster.major_version)

            self.center_require_versions[(export_center_ip, cluster.bk_cloud_id)].update(pkgs)
            self.cluster_tasks[cluster] = {
                "access_node": access_node,
                "export_center_ip": export_center_ip,
                "export_options": info.get("export_options", {}),
                "ns_filter": info["ns_filter"],
                "filename": info["filename"],
                "mongodb_package_name": os.path.basename(pkgs[1]),
            }
        logger.debug("MongoDataExportFlow payload parsed", self.cluster_tasks)

    def export_flow(self):
        """
        mongo_data_export 流程
        """
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        actuator_workdir = MongoUtil().get_mongodb_os_conf()["file_path"]

        acts_list = []
        for (exec_ip, bk_cloud_id), file_list in self.center_require_versions.items():
            acts_list.append(
                SendMedia.act(
                    act_name=_("MongoDB-介质下发-{}".format(exec_ip)),
                    file_list=list(file_list),
                    bk_host_list=[
                        {"ip": exec_ip, "bk_cloud_id": bk_cloud_id},
                    ],
                    file_target_path=actuator_workdir,
                )
            )
        if acts_list:
            main_pipeline.add_parallel_acts(acts_list)

        for cluster, task_info in self.cluster_tasks.items():
            sub_flow_param = {
                "root_id": self.root_id,
                "data": self.data,
                "cluster": cluster,
                "task_info": task_info,
                "file_path": actuator_workdir,
            }
            main_pipeline.add_sub_pipeline(DataExportSubTask.export_cluster_sub_flow(**sub_flow_param))

        main_pipeline.run_pipeline()

    @classmethod
    def __get_access_node(cls, cluster: MongoDBCluster):
        """
        选择集群目标节点
        """
        match cluster.cluster_type:
            case ClusterType.MongoReplicaSet:
                nodes = cluster.get_shards()[0].get_not_backup_nodes()
            case ClusterType.MongoShardedCluster:
                nodes = cluster.get_mongos()
            case _:
                raise Exception(_(f"Unsupported cluster type: {cluster.cluster_type}"))

        if not nodes:
            raise Exception(_(f"cluster: {cluster.immute_domain} has no valid nodes"))
        return nodes[0]

    @classmethod
    def __get_export_center_ip(cls, bk_cloud_id=0) -> str:
        """
        获取中转机器
        """
        try:
            export_center = DBExtension.get_latest_extension(
                bk_cloud_id=bk_cloud_id, extension_type=ExtensionType.MONGODB_EXPORT_CENTER
            )
        except Exception as e:
            raise Exception(_(f"Get export center failed: {str(e)}"))
        return export_center.details["ip"]
