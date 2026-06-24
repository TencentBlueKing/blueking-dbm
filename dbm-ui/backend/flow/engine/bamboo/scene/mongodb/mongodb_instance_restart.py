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
from datetime import datetime, timezone
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.sub_task.rolling_restart import (
    build_mongos_restart_subflow,
    build_rs_restart_subflow,
)
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.utils.mongodb.mongodb_util import MongoUtil
from backend.flow.utils.mongodb.restart_target_resolver import (
    ClusterRestartPlan,
    InstanceRestartPayloadSerializer,
    batch_get_restart_node_credentials,
    collect_hosts,
    group_restart_targets_by_cluster,
    order_rs_members,
    resolve_restart_targets_from_infos,
)

logger = logging.getLogger("flow")


class MongoRestartInstanceFlow:
    """MongoDB instance restart: serial within RS; sharded cluster shards -> config -> mongos."""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.payload = data or {}
        self._validate_payload()

    def _validate_payload(self):
        uid = self.payload.get("uid")
        if uid is None or (isinstance(uid, str) and not uid.strip()):
            self.payload["uid"] = (
                f"mongo-instance-restart-{self.payload.get('bk_biz_id', 0)}-"
                f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-"
                f"{self.root_id[:8]}"
            )
        serializer = InstanceRestartPayloadSerializer(data=self.payload)
        serializer.is_valid(raise_exception=True)
        self.payload = serializer.validated_data

    @staticmethod
    def _build_rs_parallel_pipes(
        root_id: str,
        ticket_data: dict,
        file_path: str,
        rs_map: Dict[str, List],
        force: bool,
        credentials_map: dict,
    ) -> List:
        pipes = []
        for rs_key, members in rs_map.items():
            ordered_members = order_rs_members(members, force=force)
            rs_name = ordered_members[0].set_name if ordered_members else rs_key
            pipes.append(
                build_rs_restart_subflow(
                    root_id=root_id,
                    ticket_data=ticket_data,
                    file_path=file_path,
                    rs_name=rs_name,
                    members=ordered_members,
                    force=force,
                    credentials_map=credentials_map,
                )
            )
        return pipes

    def _build_sharded_cluster_subflow(
        self,
        plan: ClusterRestartPlan,
        actuator_workdir: str,
        force: bool,
        credentials_map: dict,
    ):
        cluster_sb = SubBuilder(root_id=self.root_id, data=self.payload)

        shard_pipes = self._build_rs_parallel_pipes(
            self.root_id, self.payload, actuator_workdir, plan.shard_rs, force, credentials_map
        )
        if shard_pipes:
            cluster_sb.add_parallel_sub_pipeline(sub_flow_list=shard_pipes)

        for rs_key, members in plan.config_rs.items():
            ordered_members = order_rs_members(members, force=force)
            rs_name = ordered_members[0].set_name if ordered_members else rs_key
            cluster_sb.add_sub_pipeline(
                sub_flow=build_rs_restart_subflow(
                    root_id=self.root_id,
                    ticket_data=self.payload,
                    file_path=actuator_workdir,
                    rs_name=rs_name,
                    members=ordered_members,
                    force=force,
                    credentials_map=credentials_map,
                )
            )

        mongos_pipes = []
        for mongos in sorted(plan.mongos, key=lambda n: (n.ip, n.port)):
            mongos_pipes.append(
                build_mongos_restart_subflow(
                    root_id=self.root_id,
                    ticket_data=self.payload,
                    file_path=actuator_workdir,
                    target=mongos,
                    force=force,
                    credentials_map=credentials_map,
                )
            )
        if mongos_pipes:
            cluster_sb.add_parallel_sub_pipeline(sub_flow_list=mongos_pipes)

        return cluster_sb.build_sub_process(sub_name=_("MongoDB-分片集群重启-cluster_id:{}").format(plan.cluster_id))

    def start(self):
        force = bool(self.payload.get("force", False))
        targets = resolve_restart_targets_from_infos(
            self.payload["infos"],
            bk_biz_id=self.payload["bk_biz_id"],
            bk_cloud_id=self.payload["bk_cloud_id"],
        )
        credentials_map = batch_get_restart_node_credentials(targets)
        cluster_plans = group_restart_targets_by_cluster(targets)

        pipeline = Builder(root_id=self.root_id, data=self.payload)
        actuator_workdir = MongoUtil().get_mongodb_os_conf()["file_path"]
        file_list = GetFileList(db_type=DBType.MongoDB).mongodb_actuator_pkg()
        bk_host_list = collect_hosts(targets)
        if file_list and bk_host_list:
            pipeline.add_act(
                **SendMedia.act(
                    act_name=_("MongoDB-重启介质下发"),
                    file_list=file_list,
                    bk_host_list=bk_host_list,
                    file_target_path=actuator_workdir,
                )
            )

        top_parallel_pipes: List = []
        for plan in cluster_plans.values():
            if plan.cluster_type == ClusterType.MongoShardedCluster.value:
                top_parallel_pipes.append(
                    self._build_sharded_cluster_subflow(plan, actuator_workdir, force, credentials_map)
                )
            else:
                top_parallel_pipes.extend(
                    self._build_rs_parallel_pipes(
                        self.root_id, self.payload, actuator_workdir, plan.shard_rs, force, credentials_map
                    )
                )

        if not top_parallel_pipes:
            raise ValueError(_("no MongoDB instances to restart"))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=top_parallel_pipes)
        pipeline.run_pipeline()

    def multi_instance_restart_flow(self):
        """multi instance restart流程（兼容旧 controller 调用）"""
        self.start()
