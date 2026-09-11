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
from typing import Dict, List, Optional

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import MongoDBClusterRole
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_monogs_autofix import mongos_autofix
from backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_replace import cluster_replace
from backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_shard_autofix import shard_autofix
from backend.flow.engine.bamboo.scene.mongodb.sub_task.replicaset_replace import replicaset_replace
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")

# 进 sidecar 的换机类单据（含 AUTOFIX）
_SIDECAR_TICKET_TYPES = {
    TicketType.MONGODB_SHARD_CUTOFF.value,
    TicketType.MONGODB_REPLICASET_CUTOFF.value,
    TicketType.MONGODB_CUTOFF.value,
    TicketType.MONGODB_AUTOFIX.value,
}


def _collect_sidecar_cluster_ids(data: dict) -> List[int]:
    """从换机 payload 收集 sidecar 用 cluster_id。"""
    ticket_type = data.get("ticket_type")
    if ticket_type not in _SIDECAR_TICKET_TYPES:
        return []

    cluster_ids: List[int] = []
    infos = data.get("infos")
    # 分片自愈：infos 为 {MongoShardedCluster: [cluster]}
    if isinstance(infos, dict):
        for cluster in infos.get(ClusterType.MongoShardedCluster.value) or []:
            for role_key in ("mongos", "mongodb", "mongo_config"):
                for host in cluster.get(role_key) or []:
                    for inst in host.get("instances") or []:
                        cid = inst.get("cluster_id")
                        if cid and cid not in cluster_ids:
                            cluster_ids.append(cid)
        return cluster_ids

    if not isinstance(infos, list):
        return []

    if data.get("cluster_type") == ClusterType.MongoShardedCluster.value:
        for cluster in infos:
            cid = cluster.get("cluster_id")
            if cid:
                cluster_ids.append(cid)
        return cluster_ids

    # 副本集 / 默认 list 形态
    for cluster_info in infos:
        cid = cluster_info.get("cluster_id")
        if isinstance(cid, int):
            cluster_ids.append(cid)
        elif isinstance(cid, list):
            cluster_ids.extend(cid)
    return cluster_ids


class MongoMachineReplaceFlow(object):
    """
    MongoDB 整机/故障换机统一编排。

    对接单据：REPLICASET_CUTOFF / SHARD_CUTOFF / CUTOFF / AUTOFIX。
    - 副本集 list payload → replicaset_replace
    - 分片 CUTOFF list payload → cluster_replace
    - 分片 AUTOFIX dict payload → mongos_autofix / shard_autofix
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data or {}
        self.get_kwargs = ActKwargs()
        self.get_kwargs.payload = self.data
        self.get_kwargs.get_file_path()
        # 自愈分片 dict payload 无 instance domain 预检；CUTOFF/RS 需要
        if not self._is_shard_autofix_payload():
            self.get_kwargs.replace_check_instance_domain()

    def _is_shard_autofix_payload(self) -> bool:
        infos = self.data.get("infos")
        return isinstance(infos, dict) and ClusterType.MongoShardedCluster.value in infos

    def multi_host_replace_flow(self):
        """统一换机入口。"""
        if self._is_shard_autofix_payload():
            self._run_shard_autofix_orchestrator()
            return

        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        if self.data.get("cluster_type") == ClusterType.MongoReplicaSet.value:
            for replicaset in self.data["infos"]:
                sub_pipelines.append(
                    replicaset_replace(
                        root_id=self.root_id,
                        ticket_data=self.data,
                        sub_kwargs=self.get_kwargs,
                        info=replicaset,
                        cluster_role="",
                    )
                )
        elif self.data.get("cluster_type") == ClusterType.MongoShardedCluster.value:
            for cluster in self.data["infos"]:
                sub_pipelines.append(
                    cluster_replace(
                        root_id=self.root_id,
                        ticket_data=self.data,
                        sub_kwargs=self.get_kwargs,
                        info=cluster,
                    )
                )

        if sub_pipelines:
            pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        pipeline.run_pipeline_with_sidecar(check_ai_monitor_cluster_list=_collect_sidecar_cluster_ids(self.data))

    def _run_shard_autofix_orchestrator(self):
        """分片自愈编排（原 MongoClusterAutofixFlow），并补 sidecar。"""
        pipeline = Builder(root_id=self.root_id, data=self.data)
        autofix_info = self.data["infos"][ClusterType.MongoShardedCluster.value][0]
        autofix_mongos = autofix_info.get("mongos") or []
        autofix_mongo_config = autofix_info.get("mongo_config") or []
        autofix_mongodb = autofix_info.get("mongodb") or []

        # mongos 优先（自愈假定 DBHA 已处理入口）
        if autofix_mongos:
            sub_pipelines = []
            for mongos_info_by_ip in autofix_mongos:
                for mongos_instance in mongos_info_by_ip["instances"]:
                    self.get_kwargs.db_instance = mongos_instance
                    sub_pipelines.append(
                        mongos_autofix(
                            root_id=self.root_id,
                            ticket_data=self.data,
                            sub_sub_kwargs=self.get_kwargs,
                            info=mongos_info_by_ip,
                        )
                    )
            pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        sub_pipelines = []
        for config_info_by_ip in autofix_mongo_config:
            sub_pipelines.append(
                shard_autofix(
                    root_id=self.root_id,
                    ticket_data=self.data,
                    sub_kwargs=self.get_kwargs,
                    info=config_info_by_ip,
                    cluster_role=MongoDBClusterRole.ConfigSvr.value,
                )
            )
        for shard_info_by_ip in autofix_mongodb:
            sub_pipelines.append(
                shard_autofix(
                    root_id=self.root_id,
                    ticket_data=self.data,
                    sub_kwargs=self.get_kwargs,
                    info=shard_info_by_ip,
                    cluster_role=MongoDBClusterRole.ShardSvr.value,
                )
            )
        if sub_pipelines:
            pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        pipeline.run_pipeline_with_sidecar(check_ai_monitor_cluster_list=_collect_sidecar_cluster_ids(self.data))
