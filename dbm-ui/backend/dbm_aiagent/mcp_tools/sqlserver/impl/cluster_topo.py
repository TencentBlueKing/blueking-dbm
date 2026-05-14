"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Dict

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode


def sqlserver_cluster_topo(cluster_domain: str) -> Dict:
    cluster = Cluster.objects.get(immute_domain=cluster_domain)
    storage_instances = cluster.storageinstance_set.all()

    if cluster.cluster_type == ClusterType.SqlserverHA:
        sync_mode = SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
    else:
        sync_mode = None

    return {
        "cluster_type": cluster.cluster_type.value,
        "cluster_domain": cluster_domain,
        "region": cluster.region,
        "tolerance_level": cluster.disaster_tolerance_level,
        "time_zone": cluster.time_zone,
        "sync_mode": sync_mode,
        "storage": [
            {
                "address": s.ip_port,
                "status": s.status,
                "phase": s.phase,
                "version": s.version,
                "machine_type": s.machine_type,
                "instance_role": s.instance_role,
                "instance_inner_role": s.instance_inner_role,
                "is_stand_by": s.is_stand_by,
                "bk_idc_id": s.machine.bk_idc_id,
                "bk_idc_name": s.machine.bk_idc_name,
                "bk_idc_area_id": s.machine.bk_idc_area_id,
                "bk_idc_area": s.machine.bk_idc_area,
                "bk_sub_zone_id": s.machine.bk_sub_zone_id,
                "bk_sub_zone": s.machine.bk_sub_zone,
            }
            for s in storage_instances
        ],
    }
