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
from typing import List

from backend.configuration.constants import DBType
from backend.configuration.models import BizSettings
from backend.constants import CommonInstanceLabels
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, ClusterMonitorTopo, StorageInstance
from backend.exceptions import ValidationError
from backend.flow.consts import InstanceFuncAliasEnum
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.influxdb.consts import INFLUXDB_EXPORTER_PORT


@dataclass()
class InfluxDBInstanceLabels(CommonInstanceLabels):
    instance_port: str
    exporter_port: str
    db_group: str


class InfluxdbCCTopoOperator:
    """
    Influxdb 拓扑处理，由于 Influxdb 不以 Cluster 组织结构
    这里单独处理，后续如也有通过 group 来组织的数据库，可以进一步封装
    """

    def __init__(self, storages: List[StorageInstance]):
        self.storages = storages

        # 仅允许同一业务的实例操作
        bk_biz_ids = [ins.bk_biz_id for ins in self.storages]
        if len(bk_biz_ids) != 1:
            raise ValidationError("different cluster biz is not supporting")
        self.bk_biz_id = bk_biz_ids[0]
        self.hosting_biz_id = BizSettings.get_exact_hosting_biz(self.bk_biz_id, DBType.InfluxDB.value)
        self.is_bk_module_created = False

    def create_bk_module(self):
        for storage in self.storages:
            CcManage(bk_biz_id=storage.bk_biz_id, db_type=DBType.InfluxDB.value).get_or_create_set_module(
                db_type=DBType.InfluxDB.value,
                cluster_type=ClusterType.Influxdb.value,
                bk_module_name=storage.machine.ip,
                instance_id=storage.id,
                creator=storage.creator,
            )
        self.is_bk_module_created = True

    def transfer_host_in_cluster_module(self, machine_type: str, group_name: str):
        """
        根据机器的ip和machine_type的信息，选择对应的bk_set_id, 并将主机转移到对应cluster模块下
        @param machine_type: 机器的类型
        @param group_name: 组名称
        """
        if not self.is_bk_module_created:
            self.create_bk_module()
        for ins in self.storages:
            bk_module_id = ClusterMonitorTopo.objects.get(
                bk_biz_id=self.hosting_biz_id, instance_id=ins.id, machine_type=machine_type
            ).bk_module_id

            CcManage(ins.bk_biz_id, DBType.InfluxDB.value).transfer_host_module(
                [ins.machine.bk_host_id], [bk_module_id]
            )

            ins_labels = asdict(
                InfluxDBInstanceLabels(
                    app=AppCache.get_app_attr(ins.bk_biz_id, default=ins.bk_biz_id),
                    appid=str(ins.bk_biz_id),
                    app_name=AppCache.get_app_attr(ins.bk_biz_id, "db_app_abbr", ins.bk_biz_id),
                    bk_biz_id=str(ins.bk_biz_id),
                    bk_cloud_id=str(ins.machine.bk_cloud_id),
                    cluster_domain=ins.machine.ip,
                    cluster_name=ins.machine.ip,
                    cluster_type=ClusterType.Influxdb.value,
                    instance_role=ins.instance_role,
                    instance_host=ins.machine.ip,
                    instance=f"{ins.machine.ip}-{INFLUXDB_EXPORTER_PORT}",
                    instance_port=str(ins.port),
                    exporter_port=str(INFLUXDB_EXPORTER_PORT),
                    db_group=group_name,
                    db_module="default",
                )
            )

            bk_instance_id = CcManage(ins.bk_biz_id, DBType.InfluxDB.value).add_service_instance(
                bk_module_id=bk_module_id,
                bk_host_id=ins.machine.bk_host_id,
                listen_ip=ins.machine.ip,
                listen_port=ins.port,
                func_name=InstanceFuncAliasEnum.INFLUXDB_FUNC_ALIAS.value,
                bk_process_name=DBType.InfluxDB.value,
                labels_dict=ins_labels,
            )
            # 保存到数据库
            ins.bk_instance_id = bk_instance_id
            ins.save(update_fields=["bk_instance_id"])
