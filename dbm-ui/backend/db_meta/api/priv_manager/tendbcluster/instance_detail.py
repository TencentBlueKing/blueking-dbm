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

from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import InstanceNotExistException
from backend.db_meta.models import ProxyInstance, StorageInstance


def instance_detail(ip: str, port: int, bk_cloud_id: int):
    res = {}
    try:
        ins = StorageInstance.objects.get(
            machine__ip=ip,
            port=port,
            machine__bk_cloud_id=bk_cloud_id,
            cluster__cluster_type=ClusterType.TenDBCluster.value,
        )
    except ObjectDoesNotExist:
        try:
            ins = ProxyInstance.objects.get(
                machine__ip=ip,
                port=port,
                machine__bk_cloud_id=bk_cloud_id,
                cluster__cluster_type=ClusterType.TenDBCluster.value,
            )
        except ObjectDoesNotExist:
            return InstanceNotExistException(ip=ip, port=port, bk_cloud_id=bk_cloud_id)

    res["ip"] = ins.machine.ip
    res["port"] = ins.port
    res["bk_instance_id"] = ins.bk_instance_id
    res["bk_biz_id"] = ins.bk_biz_id
    res["machine_type"] = ins.machine_type

    if isinstance(ins, StorageInstance):
        res["instance_role"] = ins.instance_role
        res["instance_inner_role"] = ins.instance_inner_role
    else:
        res["spider_role"] = ins.tendbclusterspiderext.spider_role
        # res["ctl_role"] = ins.tendbclusterspiderext.ctl_role

    res["bind_entry"] = [
        {
            "entry": ele.entry,
            "entry_type": ele.cluster_entry_type,
            "entry_role": ele.role,
        }
        for ele in ins.bind_entry.all()
    ]
    res["immute_domain"] = ins.cluster.first().immute_domain
    res["cluster_type"] = ins.cluster_type
    res["bk_cloud_id"] = ins.machine.bk_cloud_id
    return res
