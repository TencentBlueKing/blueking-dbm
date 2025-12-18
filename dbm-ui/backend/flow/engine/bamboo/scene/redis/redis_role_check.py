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
import json
import logging
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.delay import DelayComponent
from backend.flow.plugins.components.collections.redis.redis_role_check import (
    RedisRoleCheckReportComponent,
    RedisRoleCheckScriptComponent,
)
from backend.flow.utils.redis.redis_context_dataclass import RedisRoleCheckContext
from backend.utils.redis import RedisConn

logger = logging.getLogger("flow")

DEFAULT_BATCH_SIZE = 2000
DEFAULT_BATCH_INTERVAL = 10  # seconds to wait between batches

# Redis Hash key pattern (must match check_role.py)
REDIS_ROLE_CHECK_CANDIDATES_KEY = "dbm:redis_role_check:candidates:{root_id}"
REDIS_ROLE_CHECK_META_FIELD = "_meta"


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
                "candidates_key": "redis_key_for_candidates",
                "batch_size": 100,
                "batch_interval": 10,  # seconds to wait between batches
                "interval": 5,
                "max_retries": 120
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

    def _load_candidates_from_redis_hash(self, candidates_key: str) -> List[Dict]:
        """
        Load candidate cluster infos from Redis Hash.

        The Redis Hash structure:
        - Field "_meta": {"total_cloud_groups": int, "total_clusters": int, "created_at": str}
        - Field "<bk_cloud_id>": [cluster_id1, cluster_id2, ...] (JSON array)

        This is more efficient than storing everything in one JSON string,
        especially for 10,000+ clusters across multiple cloud groups.

        Args:
            candidates_key: Redis key where candidates hash is stored

        Returns:
            List of cluster info dicts [{"bk_cloud_id": x, "cluster_ids": [...]}, ...]
        """
        try:
            # Get all fields from the hash
            hash_data = RedisConn.hgetall(candidates_key)
            if not hash_data:
                logger.warning(f"No data found in Redis Hash for key: {candidates_key}")
                return []

            infos = []
            meta = None

            for field, value in hash_data.items():
                # Handle bytes if redis returns bytes
                field_str = field.decode() if isinstance(field, bytes) else field
                value_str = value.decode() if isinstance(value, bytes) else value

                if field_str == REDIS_ROLE_CHECK_META_FIELD:
                    meta = json.loads(value_str)
                else:
                    # Field is bk_cloud_id, value is cluster_ids JSON array
                    bk_cloud_id = int(field_str)
                    cluster_ids = json.loads(value_str)
                    infos.append({"bk_cloud_id": bk_cloud_id, "cluster_ids": cluster_ids})

            if meta:
                logger.info(
                    f"Loaded {meta.get('total_cloud_groups', len(infos))} cloud groups "
                    f"({meta.get('total_clusters', 'unknown')} clusters) from Redis Hash: {candidates_key}"
                )
            else:
                logger.info(f"Loaded {len(infos)} cloud groups from Redis Hash: {candidates_key}")

            # Clean up the key after loading
            RedisConn.delete(candidates_key)
            return infos

        except Exception as e:
            logger.exception(f"Failed to load candidates from Redis Hash: {e}")
            return []

    def run_flow(self):
        """
        Execute the Redis role check workflow in batches.

        Batches are executed sequentially with optional intervals between batches.
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.ticket_data)

        # Load candidates from Redis Hash using the key
        candidates_key = self.ticket_data.get("candidates_key", "")
        if candidates_key:
            # Try Hash format first (new format), then fallback to legacy JSON string
            infos = self._load_candidates_from_redis_hash(candidates_key)
        else:
            # Fallback to infos in ticket_data for backward compatibility
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
        batch_interval = self.ticket_data.get("batch_interval", DEFAULT_BATCH_INTERVAL)
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

            # Activity 3: Add delay between batches (except for the last batch)
            # Using DelayComponent instead of time.sleep() to avoid blocking Celery workers
            if batch_idx < total_batches - 1 and batch_interval > 0:
                redis_pipeline.add_act(
                    act_name=_("批次{}/{}: 等待{}秒后继续下一批次").format(batch_num, total_batches, batch_interval),
                    act_component_code=DelayComponent.code,
                    kwargs={"delay_seconds": batch_interval},
                )

        redis_pipeline.run_pipeline(init_trans_data_class=RedisRoleCheckContext())
