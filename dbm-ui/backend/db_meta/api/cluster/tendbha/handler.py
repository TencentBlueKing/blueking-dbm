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

from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.models import StorageInstance
from backend.flow.utils.mysql.bk_module_operate import create_bk_module_for_cluster_id, transfer_host_in_cluster_module

from .others import add_slaves, delete_slaves


class TenDBHAClusterHandler(ClusterHandler):
    # 「必须」 集群类型
    cluster_type = ClusterType.TenDBHA

    @classmethod
    @transaction.atomic
    def create(
        cls,
        bk_biz_id: int,
        db_module_id: int,
        major_version: str,
        clusters: list,
        cluster_ip_dict: dict,
        creator: str,
        time_zone: str,
        bk_cloud_id: int,
    ):
        """「必须」创建集群,多实例录入方式"""

        # 录入机器
        machines = [
            {
                "ip": cluster_ip_dict["new_master_ip"],
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.BACKEND.value,
            },
            {
                "ip": cluster_ip_dict["new_slave_ip"],
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.BACKEND.value,
            },
            {
                "ip": cluster_ip_dict["new_proxy_1_ip"],
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.PROXY.value,
            },
            {
                "ip": cluster_ip_dict["new_proxy_2_ip"],
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.PROXY.value,
            },
        ]
        api.machine.create(machines=machines, creator=creator, bk_cloud_id=bk_cloud_id)

        # 录入机器对应的集群信息
        new_cluster_ids = []
        for cluster in clusters:
            name = cluster["name"]
            immute_domain = cluster["master"]
            slave_domain = cluster["slave"]
            storages = [
                {
                    "ip": cluster_ip_dict["new_master_ip"],
                    "port": cluster["mysql_port"],
                    "instance_role": InstanceRole.BACKEND_MASTER.value,
                },
                {
                    "ip": cluster_ip_dict["new_slave_ip"],
                    "port": cluster["mysql_port"],
                    "instance_role": InstanceRole.BACKEND_SLAVE.value,
                },
            ]
            proxies = [
                {"ip": cluster_ip_dict["new_proxy_1_ip"], "port": cluster["proxy_port"]},
                {"ip": cluster_ip_dict["new_proxy_2_ip"], "port": cluster["proxy_port"]},
            ]
            api.cluster.tendbha.create_precheck(bk_biz_id, name, immute_domain, db_module_id, slave_domain)
            api.storage_instance.create(instances=storages, creator=creator, time_zone=time_zone)
            api.proxy_instance.create(proxies=proxies, creator=creator, time_zone=time_zone)
            new_cluster_ids.append(
                api.cluster.tendbha.create(
                    bk_biz_id=bk_biz_id,
                    name=name,
                    immute_domain=immute_domain,
                    db_module_id=db_module_id,
                    slave_domain=slave_domain,
                    proxies=proxies,
                    storages=storages,
                    creator=creator,
                    bk_cloud_id=bk_cloud_id,
                    time_zone=time_zone,
                    major_version=major_version,
                )
            )
        # 生成域名模块
        create_bk_module_for_cluster_id(cluster_ids=new_cluster_ids)

        # mysql主机转移模块、添加对应的服务实例
        transfer_host_in_cluster_module(
            cluster_ids=new_cluster_ids,
            ip_list=[cluster_ip_dict["new_master_ip"], cluster_ip_dict["new_slave_ip"]],
            machine_type=MachineType.BACKEND.value,
            bk_cloud_id=bk_cloud_id,
        )

        # proxy主机转移模块、添加对应的服务实例
        transfer_host_in_cluster_module(
            cluster_ids=new_cluster_ids,
            ip_list=[cluster_ip_dict["new_proxy_1_ip"], cluster_ip_dict["new_proxy_2_ip"]],
            machine_type=MachineType.PROXY.value,
            bk_cloud_id=bk_cloud_id,
        )

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群"""
        api.cluster.tendbha.decommission_precheck(self.cluster)
        api.cluster.tendbha.decommission(self.cluster)

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        return api.cluster.tendbha.scan_cluster(self.cluster).to_dict()

    def add_slaves(self, slaves: List[Dict]):
        add_slaves(self.cluster, slaves)

    def delete_slaves(self, slaves: List[Dict]):
        delete_slaves(self.cluster, slaves)

    def get_exec_inst(self) -> StorageInstance:
        """查询集群可执行的实例"""
        return StorageInstance.objects.get(cluster=self.cluster, instance_inner_role=InstanceInnerRole.MASTER.value)
