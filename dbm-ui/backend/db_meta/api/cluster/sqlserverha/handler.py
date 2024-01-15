"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.db import transaction

from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.flow.utils.sqlserver.sqlserver_module_operate import SqlserverCCTopoOperator


class SqlserverHAClusterHandler(ClusterHandler):
    # 「必须」 集群类型
    cluster_type = ClusterType.SqlserverHA

    @classmethod
    @transaction.atomic
    def create(
        cls,
        bk_biz_id: int,
        db_module_id: int,
        major_version: str,
        master_ip: str,
        slave_ip: str,
        clusters: list,
        creator: str,
        time_zone: str,
        bk_cloud_id: int,
        resource_spec: dict,
        region: str,
    ):
        """
        1: 录入机器信息
        2：录入相关实例信息
        3：录入集群信息
        """

        # 录入机器
        machines = [
            {
                "ip": master_ip,
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.SQLSERVER_HA.value,
                "spec_id": resource_spec[MachineType.SQLSERVER_HA.value]["id"],
                "spec_config": resource_spec[MachineType.SQLSERVER_HA.value],
            },
            {
                "ip": slave_ip,
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.SQLSERVER_HA.value,
                "spec_id": resource_spec[MachineType.SQLSERVER_HA.value]["id"],
                "spec_config": resource_spec[MachineType.SQLSERVER_HA.value],
            },
        ]
        api.machine.create(machines=machines, creator=creator, bk_cloud_id=bk_cloud_id)

        # 录入机器对应的集群信息
        new_clusters = []
        storage_objs = []

        for cluster in clusters:
            name = cluster["name"]
            immute_domain = cluster["immutable_domain"]
            slave_domain = cluster["slave_domain"]
            storages = [
                {
                    "ip": master_ip,
                    "port": cluster["port"],
                    "instance_role": InstanceRole.BACKEND_MASTER.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": major_version,
                },
                {
                    "ip": slave_ip,
                    "port": cluster["port"],
                    "instance_role": InstanceRole.BACKEND_SLAVE.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": major_version,
                },
            ]

            api.cluster.sqlserverha.create_pre_check(bk_biz_id, name, immute_domain, db_module_id, slave_domain)
            storage_objs.extend(api.storage_instance.create(instances=storages, creator=creator, time_zone=time_zone))

            new_clusters.append(
                api.cluster.sqlserverha.create(
                    bk_biz_id=bk_biz_id,
                    name=name,
                    immute_domain=immute_domain,
                    db_module_id=db_module_id,
                    slave_domain=slave_domain,
                    storages=storages,
                    creator=creator,
                    bk_cloud_id=bk_cloud_id,
                    time_zone=time_zone,
                    major_version=major_version,
                    region=region,
                )
            )

        # 主机转移模块、添加对应的服务实例
        SqlserverCCTopoOperator(new_clusters).transfer_instances_to_cluster_module(storage_objs)

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群"""
        pass

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        pass
