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
from collections import defaultdict
from typing import Dict, List

from django.db.models import QuerySet

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster

logger = logging.getLogger("root")


def tendis_cluster(clusters: QuerySet) -> List[Dict]:
    cluster_list: List[Cluster] = list(
        clusters.prefetch_related(
            "proxyinstance_set",
            "storageinstance_set",
            "clusterentry_set",
            "nosqlstoragesetdtl_set",
        )
    )

    cluster_results = []
    for cluster in cluster_list:
        proxyinstance_set = []
        proxy_ports = defaultdict(int)
        proxy_ips = defaultdict(int)

        for proxy_obj in cluster.proxyinstance_set.all():
            proxyinstance_set.append("{}{}{}".format(proxy_obj.machine.ip, IP_PORT_DIVIDER, proxy_obj.port))
            proxy_ips[proxy_obj.machine.ip] += 1
            proxy_ports[proxy_obj.port] += 1

        master_instance_set = []
        slave_instance_set = []
        master_ips = defaultdict(int)
        slave_ips = defaultdict(int)

        if (
            cluster.cluster_type == ClusterType.TendisTwemproxyRedisInstance
            or cluster.cluster_type == ClusterType.TendisTwemproxyTendisplusIns
            or cluster.cluster_type == ClusterType.TwemproxyTendisSSDInstance
        ):
            for seg_obj in cluster.nosqlstoragesetdtl_set.all().order_by("seg_range"):
                master_instance_set.append(
                    "{}{}{} {}".format(
                        seg_obj.instance.machine.ip, IP_PORT_DIVIDER, seg_obj.instance.port, seg_obj.seg_range
                    )
                )
                master_ips[seg_obj.instance.machine.ip] += 1

                slave = seg_obj.instance.as_ejector.get().receiver
                slave_instance_set.append(
                    "{}{}{} {}".format(slave.machine.ip, IP_PORT_DIVIDER, slave.port, seg_obj.seg_range)
                )
                slave_ips[slave.machine.ip] += 1
        else:
            for storage_obj in cluster.storageinstance_set.all():
                if storage_obj.instance_role == InstanceRole.REDIS_MASTER:
                    master_instance_set.append(
                        "{}{}{}".format(storage_obj.machine.ip, IP_PORT_DIVIDER, storage_obj.port)
                    )
                    master_ips[storage_obj.machine.ip] += 1
                elif storage_obj.instance_role == InstanceRole.REDIS_SLAVE:
                    slave_instance_set.append(
                        "{}{}{}".format(storage_obj.machine.ip, IP_PORT_DIVIDER, storage_obj.port)
                    )
                    slave_ips[storage_obj.machine.ip] += 1

        clusterentry_set = get_cluster_entry(cluster)

        cluster_results.append(
            {
                "id": cluster.id,
                "bk_biz_id": cluster.bk_biz_id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "db_module_id": cluster.db_module_id,
                "name": cluster.name,
                "alias": cluster.alias,
                "immute_domain": cluster.immute_domain,
                "cluster_type": cluster.cluster_type,
                "major_version": cluster.major_version,
                "region": cluster.region,
                "{}_set".format(MachineType.TWEMPROXY): proxyinstance_set,
                "{}_set".format(InstanceRole.REDIS_MASTER): master_instance_set,
                "{}_set".format(InstanceRole.REDIS_SLAVE): slave_instance_set,
                "{}_ports".format(MachineType.TWEMPROXY): list(proxy_ports.keys()),
                "{}_ips_set".format(MachineType.TWEMPROXY): list(proxy_ips.keys()),
                "{}_ips_set".format(InstanceRole.REDIS_MASTER): list(master_ips.keys()),
                "{}_ips_set".format(InstanceRole.REDIS_SLAVE): list(slave_ips.keys()),
                "clusterentry_set": dict(clusterentry_set),
            }
        )

    return cluster_results


def get_cluster_entry(cluster: QuerySet) -> List[Dict]:
    clusterentry_set = defaultdict(list)
    for cluster_entry in cluster.clusterentry_set.all():
        if cluster_entry.cluster_entry_type == ClusterEntryType.DNS:
            clusterentry_set[cluster_entry.cluster_entry_type].append({"domain": cluster_entry.entry})
        elif cluster_entry.cluster_entry_type == ClusterEntryType.CLB:
            clb_detail = cluster_entry.clbentrydetail_set.get()
            clusterentry_set[cluster_entry.cluster_entry_type].append(
                {
                    "clb_ip": clb_detail.clb_ip,
                    "clb_id": clb_detail.clb_id,
                    "listener_id": clb_detail.listener_id,
                    "clb_region": clb_detail.clb_region,
                }
            )
        elif cluster_entry.cluster_entry_type == ClusterEntryType.POLARIS:
            polaris_detail = cluster_entry.polarisentrydetail_set.get()
            clusterentry_set[cluster_entry.cluster_entry_type].append(
                {
                    "polaris_name": polaris_detail.polaris_name,
                    "polaris_l5": polaris_detail.polaris_l5,
                    "polaris_token": polaris_detail.polaris_token,
                    "alias_token": polaris_detail.alias_token,
                }
            )
        else:
            clusterentry_set[cluster_entry.cluster_entry_type].append(cluster_entry.entry)

    return clusterentry_set
