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
def create(instances, creator: str = "", time_zone: str = DEFAULT_TIME_ZONE, status: str = InstanceStatus.RUNNING):
    """
    ToDo meta role 的合法性
    这里没法确定实例的 db module
    """
    instances = request_validator.validated_storage_with_role_list(instances, allow_empty=False, allow_null=False)

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


def query(
    addresses: List[str] = None,
    bk_biz_ids: List[int] = None,
    instance_roles: List[str] = None,
    db_module_ids: List[int] = None,
    statuses: List[str] = None,
):
    """
    这个接口可能是比较常用的
    address 中的实例保持使用习惯格式为 ip#port
    """
    bk_biz_ids = request_validator.validated_integer_list(bk_biz_ids)
    instance_roles = request_validator.validated_str_list(instance_roles)
    db_module_ids = request_validator.validated_integer_list(db_module_ids)
    statuses = request_validator.validated_str_list(statuses)
    addresses = request_validator.validated_str_list(addresses)
    # 这个 address 的校验比较特殊, 第一次按字符串校验顺道做下 strip 和 lstrip
    # 同时也会检查 '' 这样的空字符串
    # 下面这个循环再挨个检查每个 address, 因为 '1.1.1.1a' 这东西居然是个合法的域名
    # 挨个检查的策略是
    # 是不是个 ip ?
    # 是不是个 ip:port ?
    # 剩下的全当域名看
    # 这里这样做没啥问题, 因为这是个查询接口, 一个各方面都不正常的域名也只是会有个空结果而已
    queries = Q()
    if addresses:
        for ad in addresses:
            if validators.ipv4(ad) or validators.ipv6(ad):
                queries |= Q(**{"machine__ip": ad})
            elif validators.instance(ad):
                queries |= Q(**{"machine__ip": ad.split(":")[0], "port": ad.split(":")[1]})
            elif validators.domain(ad):
                queries |= Q(**{"cluster__clusterentry__entry": ad})
            else:
                logger.warning("{} is not a valid ip, instance or domain".format(ad))

    if bk_biz_ids:
        queries &= Q(**{"bk_biz_id__in": bk_biz_ids})

    if instance_roles:
        queries &= Q(**{"instance_role__in": instance_roles})

    if statuses:
        queries &= Q(**{"status__in": statuses})

    if db_module_ids:
        queries &= Q(**{"db_module_id__in": db_module_ids})

    return flatten.storage_instance(StorageInstance.objects.filter(queries))


def list_title() -> Dict:
    return {
        "port": _("端口"),
        "ip": _("IP 地址"),
        "db_module_id": _("DB 模块 ID"),
        "bk_biz_id": _("业务 ID"),
        "cluster": _("集群"),
        "access_layer": _("拓扑层级"),
        "machine_type": _("机器类型"),
        "instance_role": _("角色"),
        "instance_inner_role": _("系统角色"),
        "cluster_type": _("集群类型"),
        "status": _("状态"),
        "receiver": _("同步后继"),
        "ejector": _("同步上联"),
        "bind_entry": _("绑定入口"),
        "proxyinstance_set": _("接入层列表"),
        "bk_idc_city_id": _("IDC 城市 ID"),
        "bk_idc_city_name": _("IDC 城市名"),
        "logical_city_id": _("逻辑城市 ID"),
        "logical_city_name": _("逻辑城市名"),
        "bk_os_name": _("操作系统"),
        "bk_idc_area": _("区域"),
        "bk_idc_area_id": _("区域 ID"),
        "bk_sub_zone": _("子 Zone"),
        "bk_sub_zone_id": _("子 Zone ID"),
        "bk_rack": _("机架"),
        "bk_rack_id": _("机架 ID"),
        "bk_svr_device_cls_name": _("标准设备类型"),
        "bk_idc_name": _("机房"),
        "bk_idc_id": _("机房 ID"),
        "bk_cloud_id": _("云区域 ID"),
        "net_device_id": _("网络设备 ID"),
    }
