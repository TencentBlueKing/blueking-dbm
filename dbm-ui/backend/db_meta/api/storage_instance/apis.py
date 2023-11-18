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
from asyncio.log import logger
from typing import Dict, List

from django.db import transaction
from django.db.models import Q
from django.utils.translation import ugettext as _

from backend.constants import DEFAULT_TIME_ZONE
from backend.db_meta import flatten, request_validator, validators
from backend.db_meta.enums import (
    AccessLayer,
    InstanceRoleInstanceInnerRoleMap,
    InstanceStatus,
    MachineTypeInstanceRoleMap,
)
from backend.db_meta.models import Machine, StorageInstance


@transaction.atomic
def create(
    instances, creator: str = "", time_zone: str = DEFAULT_TIME_ZONE, status: str = InstanceStatus.RUNNING
) -> List[StorageInstance]:
    """
    ToDo meta role 的合法性
    这里没法确定实例的 db module
    """
    instances = request_validator.validated_storage_with_role_list(instances, allow_empty=False, allow_null=False)

    storage_objs = []
    for ins in instances:
        ip = ins["ip"]
        port = ins["port"]
        name = ins.get("name", "")
        version = ins.get("db_version", "")
        is_stand_by = ins.get("is_stand_by", True)

        machine_obj = Machine.objects.get(ip=ip)
        if machine_obj.access_layer != AccessLayer.STORAGE:
            raise Exception("{} is not storage layer".format(ip))

        if ins["instance_role"] not in MachineTypeInstanceRoleMap[machine_obj.machine_type]:
            raise Exception(
                "instance role {} not match to machine type {}".format(ins["instance_role"], machine_obj.machine_type)
            )

        instance_role = ins["instance_role"]
        storage_objs.append(
            StorageInstance.objects.create(
                port=port,
                machine=machine_obj,
                db_module_id=machine_obj.db_module_id,
                bk_biz_id=machine_obj.bk_biz_id,
                # cluster 留空
                access_layer=machine_obj.access_layer,
                machine_type=machine_obj.machine_type,
                instance_role=instance_role,
                instance_inner_role=InstanceRoleInstanceInnerRoleMap[instance_role],
                cluster_type=machine_obj.cluster_type,
                status=status,
                # bind entry 留空
                creator=creator,
                name=name,
                time_zone=time_zone,
                version=version,
                is_stand_by=is_stand_by,
            )
        )
    return storage_objs


@transaction.atomic
def update(instances):
    """
    修改实例的状态和 role
    """
    instances = request_validator.validated_storage_update(instances)

    for ins in instances:
        ip = ins["ip"]
        port = ins["port"]

        ins_obj = StorageInstance.objects.get(machine__ip=ip, port=port)

        new_status = ins.get("status", ins_obj.status)
        new_instance_role = ins.get("instance_role", ins_obj.instance_role)

        ins_obj.instance_role = new_instance_role
        ins_obj.instance_inner_role = InstanceRoleInstanceInnerRoleMap[new_instance_role]
        ins_obj.status = new_status
        ins_obj.save()


def delete(instances):
    """
    根据ip端口删除实例
    """
    for ins in instances:
        ip = ins["ip"]
        port = ins["port"]
        bk_cloud_id = ins["bk_cloud_id"]
        StorageInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip, port=port).delete()
