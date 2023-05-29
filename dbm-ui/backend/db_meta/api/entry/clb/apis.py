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
def create(domains: List[Dict], creator: str = ""):
    """
    ToDo: 已存在校验
    """

    for dm in domains:
        try:
            c = Cluster.objects.filter(immute_domain=dm["domain"]).get()
            entry = c.clusterentry_set.create(
                cluster_entry_type=ClusterEntryType.CLB,
                entry=dm["clb_ip"],
            )
            entry.clbentrydetail_set.create(
                clb_ip=dm.get("clb_ip"),
                clb_id=dm.get("clb_id", ""),
                listener_id=dm.get("clb_listener_id", ""),
                clb_region=dm.get("clb_region", ""),
                creator=creator,
            )
            proxy_objs = c.proxyinstance_set.all()
            entry.proxyinstance_set.add(*proxy_objs)

        except IntegrityError:
            raise ClusterEntryExistException(cluster=dm["domain"], clb=dm["clb_ip"])
