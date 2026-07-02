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

from django.db import transaction

from backend.db_meta.enums import ClusterEntryType
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
) -> dict:
    # get_or_create 的 defaults 只需要包含查询字段之外的属性，查询字段命中已存在记录时不会写入 defaults
    cluster, _ = Cluster.objects.get_or_create(
        name=name,
        cluster_type=cluster_type,
        bk_biz_id=bk_biz_id,
        defaults={
            "alias": alias,
            "immute_domain": immute_domain,
            "major_version": major_version,
            "phase": phase,
            "status": status,
            "region": region,
            "creator": creator,
        },
    )

    ClusterEntry.objects.get_or_create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.CLBDNS,
        entry=immute_domain,
        defaults={"creator": creator},
    )
    return cluster.simple_desc
