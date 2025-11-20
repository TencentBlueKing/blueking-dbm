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

from django.db import IntegrityError, transaction

from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster

from ....exceptions import ClusterEntryExistException

logger = logging.getLogger("root")


@transaction.atomic
def es_create(domains: List[Dict], creator: str = ""):

    for dm in domains:
        try:
            c_obj = Cluster.objects.filter(immute_domain=dm["domain"]).get()
            polaris_entry = c_obj.clusterentry_set.create(
                cluster_entry_type=ClusterEntryType.POLARIS,
                entry=dm["polaris_name"],
                creator=creator,
            )
            polaris_entry.polarisentrydetail_set.create(
                polaris_name=dm["polaris_name"],
                polaris_l5=dm.get("polaris_l5", ""),
                polaris_token=dm["polaris_token"],
                alias_token=dm["alias_token"],
                creator=creator,
            )
            dns_entry = c_obj.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.DNS.value).first()
            access_objs = dns_entry.storageinstance_set.all()
            polaris_entry.storageinstance_set.add(*access_objs)
        except IntegrityError:
            raise ClusterEntryExistException(cluster=dm["domain"], polaris_name=dm["polaris_name"])
