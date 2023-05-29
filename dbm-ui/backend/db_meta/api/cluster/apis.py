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
from typing import Dict, List

from django.db.models import Q

from backend.db_meta import request_validator
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry

logger = logging.getLogger("root")


def query_instances(ip: str) -> Dict:
    ip = request_validator.validated_ip(ip)

    queries = Q(**{"storageinstance__machine__ip": ip}) | Q(**{"proxyinstance__machine__ip": ip})
    qs = Cluster.objects.filter(queries)

    if qs.exists():
        cluster = qs.first()
        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": cluster.bk_biz_id,
            "db_module_id": cluster.db_module_id,
            "cluster_type": cluster.cluster_type,
        }
    else:
        return {}


def domain_exists(domains: List[str]) -> Dict[str, bool]:
    domains = request_validator.validated_domain_list(domains, allow_empty=False)

    res = {}
    for dm in domains:
        res[dm] = False
    for obj in ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS, entry__in=domains):
        res[obj.entry] = True

    return res
