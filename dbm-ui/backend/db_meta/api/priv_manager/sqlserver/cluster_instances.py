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

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from backend.db_meta.exceptions import ClusterEntryNotExistException, DBMetaException
from backend.db_meta.models import Cluster, ClusterEntry

logger = logging.getLogger()


@transaction.atomic
def cluster_instances(immute_domain: str, cluster_type: str):
    try:
        input_entry = ClusterEntry.objects.get(entry=immute_domain, cluster__cluster_type=cluster_type)
    except ObjectDoesNotExist:
        raise ClusterEntryNotExistException(entry=immute_domain)

    try:
        cluster = Cluster.objects.get(immute_domain=immute_domain)
        res = _cluster_instance(cluster)
        res["bind_to"] = input_entry.storageinstance_set.first().access_layer

    except ObjectDoesNotExist:
        raise DBMetaException("cluster info failed")

    return res


def _cluster_instance(cluster: Cluster):

    storages = []
    for s in cluster.storageinstance_set.all():
        storages.append(
            {
                "ip": s.machine.ip,
                "port": s.port,
                "instance_role": s.instance_role,
                "bk_cloud_id": s.machine.bk_cloud_id,
                "status": s.status,
            }
        )

    return {
        "proxies": [],
        "storages": storages,
        "cluster_type": cluster.cluster_type,
        "bk_biz_id": cluster.bk_biz_id,
        "db_module_id": cluster.db_module_id,
        "bk_cloud_id": cluster.bk_cloud_id,
    }
