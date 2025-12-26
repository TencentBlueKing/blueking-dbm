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

from backend.db_meta.models import Cluster


def redis_cluster_topo(immute_domain: str) -> Dict:
    cluster_obj = Cluster.objects.get(immute_domain=immute_domain)
    storage_instances = cluster_obj.storageinstance_set.all()
    proxy_instances = cluster_obj.proxyinstance_set.all()

    return {
        "cluster_type": cluster_obj.cluster_type,
        "cluster_domain": immute_domain,
        "proxy": [{"address": "{}:{}".format(s.machine.ip, s.port), "status": s.status} for s in proxy_instances],
        "storage": [{"address": "{}:{}".format(s.machine.ip, s.port), "status": s.status} for s in storage_instances],
    }
