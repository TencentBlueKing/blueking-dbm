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

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.redis.redis_role_check import (
    RedisRoleCheckReportComponent,
    RedisRoleCheckScriptComponent,
)
from backend.flow.utils.redis.redis_context_dataclass import RedisRoleCheckContext

logger = logging.getLogger("flow")

DEFAULT_BATCH_SIZE = 2000


class RedisRoleCheckFlow(object):
    """
    Redis Role Check Flow

    This flow verifies that the actual Redis instance roles match the metadata in db_meta.
    It executes scripts on target machines to query Redis role info and compares with meta.

    Flow structure:
    1. RedisRoleCheckScriptService: Executes scripts for ALL clusters in parallel (via ThreadPoolExecutor)
    2. RedisRoleCheckReportService: Polls ALL jobs in parallel, parses results, writes reports

    The components use ThreadPoolExecutor internally to handle parallelism for >1000 clusters.
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        Initialize the Redis role check flow

        Args:
            root_id: Unique identifier for the flow
            data: {
                "ticket_type": "REDIS_ROLE_CHECK",
                "bk_biz_id": 0,
                "created_by": "system",
                "infos": [
                    {
                        "bk_cloud_id": 0,
                        "cluster_ids": [1, 2, 3]
                    },
                    {
                        "bk_cloud_id": 1,
                        "cluster_ids": [4, 5]
                    }
                ],
                "batch_size": 2000,
                "interval": 5,
                "max_retires": 120
            }
        """
        self.root_id = root_id
        self.ticket_data = data

    def _get_cluster_instances(self, cluster: Cluster) -> List[Dict]:
        """
        Get all storage instances from a cluster with their role information.

        Args:
            cluster: Cluster model instance

        Returns:
            List of instance dicts with ip, port, and meta_role
        """
        instances = []
        for inst in cluster.storageinstance_set.all():
            instances.append(
                {
                    "ip": inst.machine.ip,
                    "port": inst.port,
                    "meta_role": inst.instance_role,
                }
            )
        return instances

    def _get_slave_ip(self, cluster: Cluster) -> Optional[str]:
        """
        Get a slave IP from the cluster for script execution.
        Falls back to master if no slave is available.

        Args:
            cluster: Cluster model instance

        Returns:
            IP address of a slave (or master as fallback), or None if no instances
        """
        # Try to get a slave first
        slave = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value).first()

        if slave:
            return slave.machine.ip

        # Fallback to master if no slave available
        master = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value).first()

        if master:
            return master.machine.ip

        return None

    def _prepare_cluster_data(self, cluster_id: int, bk_cloud_id: int) -> Optional[Dict]:
        """
        Prepare data for a single cluster's role check.

        Args:
            cluster_id: ID of the cluster to check
            bk_cloud_id: BK cloud ID for the cluster

        Returns:
            Dict with exec_ip, instances, cluster_id, bk_cloud_id, cluster_domain
            or None if cluster not found or has no instances
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            logger.warning(f"Cluster {cluster_id} not found, skipping")
            return None

        # Get instances
        instances = self._get_cluster_instances(cluster)
        if not instances:
            logger.warning(f"Cluster {cluster_id} has no instances, skipping")
            return None

        # Get execution IP (prefer slave)
        exec_ip = self._get_slave_ip(cluster)
        if not exec_ip:
            logger.warning(f"Cluster {cluster_id} has no valid execution IP, skipping")
            return None

        return {
            "cluster_id": cluster_id,
            "bk_cloud_id": bk_cloud_id,
            "cluster_domain": cluster.immute_domain,
            "exec_ip": exec_ip,
            "instances": instances,
        }

    def run_flow(self):
        """
        Execute the Redis role check workflow in batches.

        Batches are executed sequentially.
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.ticket_data)

        infos = self.ticket_data.get("infos", [])
        if not infos:
            logger.warning("No cluster infos provided for role check")
            redis_pipeline.run_pipeline()
            return

        # Prepare cluster data from all cloud groups
        cluster_data_list = []
        for info in infos:
            bk_cloud_id = info.get("bk_cloud_id", 0)
            cluster_ids = info.get("cluster_ids", [])

            for cluster_id in cluster_ids:
                cluster_data = self._prepare_cluster_data(cluster_id, bk_cloud_id)
                if cluster_data:
                    cluster_data_list.append(cluster_data)

        if not cluster_data_list:
            logger.warning("No valid clusters to check")
            redis_pipeline.run_pipeline()
            return

        batch_size = self.ticket_data.get("batch_size", DEFAULT_BATCH_SIZE)
        total_clusters = len(cluster_data_list)
        total_batches = (total_clusters + batch_size - 1) // batch_size
        logger.info(f"Starting role check for {total_clusters} clusters in {total_batches} batches")

        interval = self.ticket_data.get("interval", None)
        max_retries = self.ticket_data.get("max_retries", None)

        # Process clusters in batches
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_clusters)
            batch_clusters = cluster_data_list[start_idx:end_idx]
            batch_num = batch_idx + 1

            # Activity 1: Execute scripts for this batch
            redis_pipeline.add_act(
                act_name=_("批次{}/{}: 执行Role检查脚本 ({}个集群)").format(batch_num, total_batches, len(batch_clusters)),
                act_component_code=RedisRoleCheckScriptComponent.code,
                kwargs={
                    "node_name": f"role_check_script_exec_batch_{batch_num}",
                    "clusters": batch_clusters,
                },
            )

            # Activity 2: Poll jobs and write reports for this batch
            redis_pipeline.add_act(
                act_name=_("批次{}/{}: 处理检查结果").format(batch_num, total_batches),
                act_component_code=RedisRoleCheckReportComponent.code,
                kwargs={
                    "node_name": f"role_check_report_batch_{batch_num}",
                    "interval": interval,
                    "max_retries": max_retries,
                },
            )

        redis_pipeline.run_pipeline(init_trans_data_class=RedisRoleCheckContext())
