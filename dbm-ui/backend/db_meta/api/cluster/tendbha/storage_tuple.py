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

from django.db import transaction

from backend.db_meta.models import StorageInstance, StorageInstanceTuple

logger = logging.getLogger("root")


@transaction.atomic
def add_storage_tuple(master_ip: str, slave_ip: str, bk_cloud_id: int, port_list: list):
    for port in port_list:
        master_storage = StorageInstance.objects.get(
            machine__ip=master_ip, port=port, machine__bk_cloud_id=bk_cloud_id
        )
        slave_storage = StorageInstance.objects.get(machine__ip=slave_ip, port=port, machine__bk_cloud_id=bk_cloud_id)
        StorageInstanceTuple.objects.create(ejector=master_storage, receiver=slave_storage)


@transaction.atomic
def remove_storage_tuple(master_ip: str, slave_ip: str, bk_cloud_id: int, port_list: list):
    for port in port_list:
        master_storage = StorageInstance.objects.get(
            machine__ip=master_ip, port=port, machine__bk_cloud_id=bk_cloud_id
        )
        slave_storage = StorageInstance.objects.get(machine__ip=slave_ip, port=port, machine__bk_cloud_id=bk_cloud_id)
        StorageInstanceTuple.objects.filter(ejector=master_storage, receiver=slave_storage).delete()
