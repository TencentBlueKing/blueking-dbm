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

from django.db.transaction import atomic

from backend.db_meta import api
from backend.db_meta.enums import InstanceRole, MachineType
from backend.flow.consts import DEFAULT_DB_MODULE_ID, DEFAULT_RIAK_PORT

logger = logging.getLogger("flow")


class RiakDBMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    """

    def __init__(self, ticket_data: dict, cluster: dict):
        """
        @param ticket_data : 单据信息
        @param cluster: 集群信息
        """
        self.ticket_data = ticket_data
        self.cluster = cluster

    def riak_cluster_apply(self) -> bool:
        ips = self.cluster.nodes
        machines = [
            {"ip": ip, "bk_biz_id": int(self.ticket_data["bk_biz_id"]), "machine_type": MachineType.RIAK.value}
            for ip in ips
        ]
        instances = [
            {"ip": ip, "port": DEFAULT_RIAK_PORT, "instance_role": InstanceRole.RIAK_NODE.value} for ip in ips
        ]
        cluster = {
            "bk_cloud_id": self.ticket_data["bk_cloud_id"],
            "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
            "name": self.ticket_data["cluster_name"],
            "alias": self.ticket_data["cluster_alias"],
            "immute_domain": self.ticket_data["domain"],
            "db_module_id": DEFAULT_DB_MODULE_ID,
            "storages": instances,
            "creator": self.ticket_data["created_by"],
            "major_version": self.ticket_data["db_version"],
        }

        with atomic():
            api.machine.create(
                machines=machines,
                bk_cloud_id=self.ticket_data["bk_cloud_id"],
                creator=self.ticket_data["created_by"],
            )
            api.storage_instance.create(instances=instances, creator=self.ticket_data["created_by"])
            api.cluster.riak.create(**cluster)
        return True

    def riak_scale_out(self) -> bool:
        ips = self.cluster.operate_nodes
        machines = [
            {"ip": ip, "bk_biz_id": int(self.ticket_data["bk_biz_id"]), "machine_type": MachineType.RIAK.value}
            for ip in ips
        ]
        instances = [
            {"ip": ip, "port": DEFAULT_RIAK_PORT, "instance_role": InstanceRole.RIAK_NODE.value} for ip in ips
        ]
        cluster = {
            "cluster_id": self.ticket_data["cluster_id"],
            "storages": instances,
        }

        with atomic():
            api.machine.create(
                machines=machines,
                bk_cloud_id=self.ticket_data["bk_cloud_id"],
                creator=self.ticket_data["created_by"],
            )
            api.storage_instance.create(instances=instances, creator=self.ticket_data["created_by"])
            api.cluster.riak.scale_out(**cluster)

    def riak_scale_in(self) -> bool:
        ips = self.cluster.operate_nodes
        instances = [
            {"ip": ip, "port": DEFAULT_RIAK_PORT, "instance_role": InstanceRole.RIAK_NODE.value} for ip in ips
        ]
        cluster = {
            "cluster_id": self.ticket_data["cluster_id"],
            "storages": instances,
        }
        api.cluster.riak.scale_in(**cluster)

    def riak_cluster_destroy(self) -> bool:
        api.cluster.riak.destroy(self.ticket_data["cluster_id"])
