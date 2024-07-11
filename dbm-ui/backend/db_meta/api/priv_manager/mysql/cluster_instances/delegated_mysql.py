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

from backend.db_meta.enums import AccessLayer, ClusterType
from backend.db_meta.exceptions import ClusterEntryNotExistException
from backend.db_meta.models import ClusterEntry


def delegated_mysql(entry_name: str):
    try:
        input_entry = ClusterEntry.objects.get(
            entry=entry_name, cluster__cluster_type=ClusterType.DelegatedMySQL.value
        )
        cluster = input_entry.cluster
        return {
            "bind_to": AccessLayer.STORAGE.value,
            "entry_role": input_entry.role,
            "cluster_type": cluster.cluster_type,
            "bk_biz_id": cluster.bk_biz_id,
            "db_module_id": cluster.db_module_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "immute_domain": cluster.immute_domain,
            "storages": [],
        }
    except ClusterEntry.DoesNotExist:
        raise ClusterEntryNotExistException(entry=entry_name)
