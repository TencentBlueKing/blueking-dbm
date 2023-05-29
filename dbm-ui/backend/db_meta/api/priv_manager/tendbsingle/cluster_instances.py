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

from django.core.exceptions import ObjectDoesNotExist

from backend.db_meta.enums import AccessLayer, ClusterType
from backend.db_meta.exceptions import ClusterEntryNotExistException
from backend.db_meta.models import ClusterEntry


def cluster_instances(entry_name: str):
    try:
        input_entry = ClusterEntry.objects.get(entry=entry_name, cluster__cluster_type=ClusterType.TenDBSingle.value)
        cluster = input_entry.cluster

        storage_instance = cluster.storageinstance_set.first()
        return {
            "bind_to": AccessLayer.STORAGE.value,
            "entry_role": input_entry.role,
            "cluster_type": cluster.cluster_type,
            "bk_biz_id": cluster.bk_biz_id,
            "db_module_id": cluster.db_module_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "immute_domain": cluster.immute_domain,
            "storages": {
                "ip": storage_instance.machine.ip,
                "port": storage_instance.port,
                "instance_inner_role": storage_instance.instance_inner_role,
                "instance_role": storage_instance.instance_role,
                "bk_cloud_id": storage_instance.machine.bk_cloud_id,
                "status": storage_instance.status,
                "bk_instance_id": storage_instance.bk_instance_id,
            },
        }

    except ObjectDoesNotExist:
        raise ClusterEntryNotExistException(entry=entry_name)
