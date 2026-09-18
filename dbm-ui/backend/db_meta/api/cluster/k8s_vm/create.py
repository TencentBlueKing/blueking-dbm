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

from typing import List

from django.db import transaction

from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry


@transaction.atomic
def create(
    name: str,
    alias: str,
    bk_biz_id: int,
    cluster_type: str,
    immute_domain: str,
    major_version: str,
    phase: str,
    status: str,
    region: str,
    creator: str,
    storage_nodes: List[str] = None,
) -> dict:
    cluster_defaults = {
        "name": name,
        "alias": alias,
        "cluster_type": cluster_type,
        "bk_biz_id": bk_biz_id,
        "major_version": major_version,
        "phase": phase,
        "status": status,
        "region": region,
        "storage_nodes": storage_nodes or [],
    }
    cluster, created = Cluster.objects.get_or_create(
        immute_domain=immute_domain, defaults={**cluster_defaults, "creator": creator}
    )
    if not created:
        for field, value in cluster_defaults.items():
            setattr(cluster, field, value)
        cluster.updater = creator
        cluster.save(update_fields=[*cluster_defaults, "updater", "update_at"])

    # vminsert / vmselect / vmstorage 共用统一域名，仅以端口区分，因此只落一条入口记录
    ClusterEntry.objects.get_or_create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.CLBDNS,
        entry=immute_domain,
        defaults={"creator": creator, "role": ClusterEntryRole.MASTER_ENTRY.value},
    )
    return cluster.simple_desc
