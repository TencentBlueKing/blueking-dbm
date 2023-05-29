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

from django.db import transaction

from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import StorageInstance
from backend.flow.utils.mysql.mysql_module_operate import MysqlCCTopoOperator


class TenDBSingleClusterHandler(ClusterHandler):
    # 「必须」 集群类型
    cluster_type = ClusterType.TenDBSingle

    @classmethod
    @transaction.atomic
    def create(
        cls,
        bk_biz_id: int,
        major_version: str,
        ip: str,
        clusters: list,
        db_module_id: int,
        creator: str,
        time_zone: str,
        bk_cloud_id: int,
        resource_spec: dict,
        region: str,
    ):
        """「必须」创建集群"""
        api.machine.create(
            machines=[
                {
                    "ip": ip,
                    "bk_biz_id": bk_biz_id,
                    "machine_type": MachineType.SINGLE.value,
                    "bk_cloud_id": bk_cloud_id,
                    "spec_id": resource_spec[MachineType.SINGLE.value]["id"],
                    "spec_config": resource_spec[MachineType.SINGLE.value],
                }
            ],
            creator=creator,
            bk_cloud_id=bk_cloud_id,
        )
        new_clusters = []
        new_storage_objs = []
        for cluster in clusters:
            storage = {"ip": ip, "port": cluster["mysql_port"]}
            immute_domain = cluster["master"]
            new_storage_objs.extend(
                api.storage_instance.create(
                    instances=[
                        {
                            "ip": ip,
                            "port": cluster["mysql_port"],
                            "instance_role": InstanceRole.ORPHAN.value,
                            "bk_cloud_id": bk_cloud_id,
                        }
                    ],
                    creator=creator,
                    time_zone=time_zone,
                )
            )
            api.cluster.tendbsingle.create_precheck(bk_biz_id, cluster["name"], immute_domain, db_module_id)
            new_clusters.append(
                api.cluster.tendbsingle.create(
                    bk_biz_id=bk_biz_id,
                    major_version=major_version,
                    name=cluster["name"],
                    immute_domain=immute_domain,
                    db_module_id=db_module_id,
                    storage=storage,
                    creator=creator,
                    bk_cloud_id=bk_cloud_id,
                    time_zone=time_zone,
                    region=region,
                )
            )

        # mysql主机转移模块、添加对应的服务实例
        MysqlCCTopoOperator(new_clusters).transfer_instances_to_cluster_module(new_storage_objs)

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群"""
        api.cluster.tendbsingle.decommission(self.cluster)

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        return api.cluster.tendbsingle.scan_cluster(self.cluster).to_dict()

    def get_remote_address(self) -> StorageInstance:
        """查询DRS访问远程数据库的地址"""
        return StorageInstance.objects.get(cluster=self.cluster).ip_port
