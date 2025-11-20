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

from django.db import IntegrityError, transaction

from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster

from ....exceptions import ClusterEntryExistException

logger = logging.getLogger("root")


@transaction.atomic
def es_create(domain: str, clb_ip: str, clb_id: str, clb_listener_id: str, clb_region: str, creator: str = ""):

    try:
        c = Cluster.objects.filter(immute_domain=domain).get()
        clb_entry = c.clusterentry_set.create(
            cluster_entry_type=ClusterEntryType.CLB,
            entry=clb_ip,
            creator=creator,
        )
        clb_entry.clbentrydetail_set.create(
            clb_ip=clb_ip,
            clb_id=clb_id,
            listener_id=clb_listener_id,
            clb_region=clb_region,
            creator=creator,
        )
        dns_entry = c.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.DNS.value).first()
        access_objs = dns_entry.storageinstance_set.all()
        clb_entry.storageinstance_set.add(*access_objs)
    except IntegrityError:
        raise ClusterEntryExistException(cluster=domain, clb=clb_ip)
