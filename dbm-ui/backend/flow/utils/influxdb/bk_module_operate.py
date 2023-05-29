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
from dataclasses import asdict, dataclass

from backend.constants import CommonInstanceLabels
from backend.db_meta.api.common import add_service_instance
from backend.db_meta.api.db_module import get_or_create_influxdb
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, ClusterMonitorTopo
from backend.flow.utils.cc_manage import CcManage


@dataclass()
class InfluxDBInstanceLabels(CommonInstanceLabels):
    instance_port: str
    exporter_port: str
    db_group: str


def create_bk_module(bk_biz_id: int, storages: list, creator: str = ""):
    for storage in storages:
        get_or_create_influxdb(
            bk_biz_id=bk_biz_id,
            instance_id=storage.id,
            cluster_type=ClusterType.Influxdb.value,
            instance_ip=storage.machine.ip,
            creator=creator,
        )


def transfer_host_in_cluster_module(
    bk_biz_id: int,
    storages: list,
    machine_type: str,
    group_name: str,
):
    """
    根据机器的ip和machine_type的信息，选择对应的bk_set_id, 并将主机转移到对应cluster模块下
    @param bk_biz_id: 主机所属业务ID
    @param storages: 对应的storages 列表
    @param machine_type: 机器的类型
    @param group_name: 组名称
    """
    for storage in storages:
        bk_module_id = ClusterMonitorTopo.objects.get(
            bk_biz_id=storage.bk_biz_id, instance_id=storage.id, machine_type=machine_type
        ).bk_module_id

        CcManage.transfer_host_module(bk_biz_id, [storage.machine.bk_host_id], [bk_module_id])

        init_instance_service(
            ins=storage,
            bk_module_id=bk_module_id,
            instance_role=storage.instance_role,
            func_name="telegraf",
            group_name=group_name,
        )


def init_instance_service(ins, bk_module_id, instance_role, func_name, group_name):
    ins_labels = asdict(
        InfluxDBInstanceLabels(
            app=AppCache.get_app_attr(ins.bk_biz_id, default=ins.bk_biz_id),
            app_id=str(ins.bk_biz_id),
            app_name=AppCache.get_app_attr(ins.bk_biz_id, "db_app_abbr", ins.bk_biz_id),
            bk_biz_id=str(ins.bk_biz_id),
            bk_cloud_id=str(ins.machine.bk_cloud_id),
            cluster_domain=ins.machine.ip,
            cluster_name=ins.machine.ip,
            cluster_type=ClusterType.Influxdb.value,
            instance_role=instance_role,
            instance_host=ins.machine.ip,
            instance=f"{ins.machine.ip}-9274",
            instance_port=str(ins.port),
            exporter_port=str(9274),
            db_group=group_name,
        )
    )

    bk_instance_id = add_service_instance(
        bk_module_id=bk_module_id,
        bk_host_id=ins.machine.bk_host_id,
        listen_ip=ins.machine.ip,
        listen_port=9274,
        func_name=func_name,
        labels_dict=ins_labels,
    )
    # 保存到数据库
    ins.bk_instance_id = bk_instance_id
    ins.save(update_fields=["bk_instance_id"])
