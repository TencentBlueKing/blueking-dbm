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
from typing import Dict, List

from django.db import transaction

from backend.constants import DEFAULT_TIME_ZONE
from backend.db_meta import request_validator
from backend.db_meta.enums import (
    AccessLayer,
    ClusterType,
    InstancePhase,
    InstanceRoleInstanceInnerRoleMap,
    InstanceStatus,
    MachineTypeInstanceRoleMap,
)
from backend.db_meta.models import Machine, StorageInstance
from backend.flow.utils.cc_manage import CcManage


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
        phase = ins.get("phase", InstancePhase.ONLINE.value)

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
                phase=phase,
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


@transaction.atomic
def remove_storage_instances(bk_biz_id: int, cluster_type: ClusterType, instances: List[Dict]):
    """
    根据传入的实例信息列表，绑定事务进行清理
    """
    cc_manage = CcManage(bk_biz_id, cluster_type)
    for ins in instances:
        storage = StorageInstance.objects.get(
            machine__bk_cloud_id=ins["bk_cloud_id"], machine__ip=ins["ip"], port=ins["port"]
        )
        cc_manage.delete_service_instance(bk_instance_ids=[storage.bk_instance_id])
        storage.delete(keep_parents=True)

        # 查询实例对应的机器是否存在其他的实例(当前读)，如果不存在，则删除machine表
        remaining_instances = list(
            StorageInstance.objects.select_for_update().filter(
                machine__bk_cloud_id=ins["bk_cloud_id"], machine__ip=ins["ip"]
            )
        )
        if remaining_instances:
            continue

        # 不存在，则清理machine表
        Machine.objects.filter(ip=ins["ip"], bk_cloud_id=ins["bk_cloud_id"]).delete()
        # 转移退回池
        cc_manage.recycle_host([storage.machine.bk_host_id])
