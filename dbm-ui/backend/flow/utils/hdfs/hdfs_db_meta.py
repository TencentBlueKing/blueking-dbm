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
from django.utils.translation import ugettext as _

from backend.db_meta import api
from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import HdfsRoleEnum, LevelInfoEnum
from backend.flow.utils.hdfs.bk_module_operate import create_bk_module_for_cluster_id, transfer_host_in_cluster_module
from backend.flow.utils.hdfs.consts import DATANODE_DEFAULT_PORT, JOURNAL_NODE_DEFAULT_PORT, ZOOKEEPER_DEFAULT_PORT
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class HdfsDBMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    规定：
    Machine:
        access_layer:          storage/proxy
    StorageInstance:
        access_layer:          storage
        machine_type:          hdfs_datanode/hdfs_master
        instance_role:         hdfs_datanode/hdfs_journalnode/hdfs_zookeeper/hdfs_namenode
        instance_inner_role:   orphan
    """

    def __init__(self, ticket_data: dict):
        """
        @param ticket_data : 单据信息
        """
        self.ticket_data = ticket_data
        self.role_machine_dict = {
            HdfsRoleEnum.ZooKeeper.value: MachineType.HDFS_MASTER.value,
            HdfsRoleEnum.NameNode.value: MachineType.HDFS_MASTER.value,
            HdfsRoleEnum.DataNode.value: MachineType.HDFS_DATANODE.value,
        }

    def write(self) -> bool:
        function_name = self.ticket_data["ticket_type"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()
        else:
            logger.error(_("找不到单据类型需要变更的cmdb函数，请联系系统管理员"))
            return False

    def hdfs_apply(self) -> bool:
        # 部署hdfs，更新cmdb
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()

        cluster = {
            "bk_cloud_id": self.ticket_data["bk_cloud_id"],
            "bk_biz_id": self.ticket_data["bk_biz_id"],
            "name": self.ticket_data["cluster_name"],
            "alias": self.ticket_data["cluster_alias"],
            "immute_domain": self.ticket_data["domain"],
            "db_module_id": int(LevelInfoEnum.TendataModuleDefault),
            "major_version": self.ticket_data["db_version"],
            "storages": storage_instances,
            "creator": self.ticket_data["created_by"],
        }

        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=self.ticket_data["bk_cloud_id"], machines=machines, creator=self.ticket_data["created_by"]
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            cluster_id = api.cluster.hdfs.create(**cluster)
            # 根据已插入dbmeta的Cluster实体创建CC模块，主机转模块
            self.__create_and_transfer_module(cluster_id)

        return True

    def hdfs_scale_up(self) -> bool:
        # 扩容HDFS集群 更新cmdb
        machines = self.__generate_machine()
        storage_instances = self.__generate_storage_instance()

        with atomic():
            # 绑定事务更新cmdb
            api.machine.create(
                bk_cloud_id=self.ticket_data["bk_cloud_id"], machines=machines, creator=self.ticket_data["created_by"]
            )
            api.storage_instance.create(instances=storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.hdfs.scale_up(
                cluster_id=self.ticket_data["cluster_id"],
                storages=storage_instances,
            )
            # 扩容时仅转移新主机模块
            transfer_host_in_cluster_module(
                cluster_id=self.ticket_data["cluster_id"],
                ip_list=self.ticket_data["new_dn_ips"],
                machine_type=MachineType.HDFS_DATANODE.value,
                bk_cloud_id=self.ticket_data["bk_cloud_id"],
                kwargs=self.ticket_data,
            )
        return True

    def hdfs_shrink(self) -> bool:
        # 缩容HDFS集群 更新cmdb
        storage_instances = self.__generate_storage_instance()
        with atomic():
            # 删除集群绑定关系
            api.cluster.hdfs.shrink(
                cluster_id=self.ticket_data["cluster_id"],
                storages=storage_instances,
            )
        return True

    def hdfs_destroy(self) -> bool:
        api.cluster.hdfs.destroy(self.ticket_data["cluster_id"])
        return True

    def hdfs_disable(self) -> bool:
        api.cluster.hdfs.disable(self.ticket_data["cluster_id"])
        return True

    def hdfs_enable(self) -> bool:
        api.cluster.hdfs.enable(self.ticket_data["cluster_id"])
        return True

    def hdfs_replace(self) -> bool:
        # HDFS集群 替换操作为分阶段执行，从ticket_data判断当前替换角色区分
        with atomic():
            add_storage_instances, del_storage_instances = self.__generate_replace_storage_instance(
                self.ticket_data["replace_role"]
            )
            new_machines = self.__generate_replace_machine(self.ticket_data["replace_role"])
            # 兼容 已加入集群的机器分配其他master角色
            if new_machines:
                api.machine.create(machines=new_machines, creator=self.ticket_data["created_by"])
            api.storage_instance.create(instances=add_storage_instances, creator=self.ticket_data["created_by"])
            api.cluster.hdfs.replace(
                cluster_id=self.ticket_data["cluster_id"],
                add_storages=add_storage_instances,
                del_storages=del_storage_instances,
            )
        return True

    def __generate_storage_instance(self) -> list:
        storage_instances = []
        if self.ticket_data["ticket_type"] == TicketType.HDFS_APPLY:
            for dn_ip in self.ticket_data["dn_ips"]:
                storage_instances.append(
                    {
                        "ip": dn_ip,
                        "port": DATANODE_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_DATA_NODE.value,
                        "name": HdfsRoleEnum.DataNode.value,
                    }
                )
            storage_instances.append(
                {
                    "ip": self.ticket_data["nn1_ip"],
                    "port": self.ticket_data["rpc_port"],
                    "instance_role": InstanceRole.HDFS_NAME_NODE.value,
                    "name": HdfsRoleEnum.NameNode.value,
                }
            )
            storage_instances.append(
                {
                    "ip": self.ticket_data["nn2_ip"],
                    "port": self.ticket_data["rpc_port"],
                    "instance_role": InstanceRole.HDFS_NAME_NODE.value,
                    "name": HdfsRoleEnum.NameNode.value,
                }
            )

            for zk_ip in self.ticket_data["zk_ips"]:
                storage_instances.append(
                    {
                        "ip": zk_ip,
                        "port": ZOOKEEPER_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_ZOOKEEPER.value,
                        "name": HdfsRoleEnum.ZooKeeper.value,
                    }
                )
            for jn_ip in self.ticket_data["jn_ips"]:
                storage_instances.append(
                    {
                        "ip": jn_ip,
                        "port": JOURNAL_NODE_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_JOURNAL_NODE.value,
                        "name": HdfsRoleEnum.JournalNode.value,
                    }
                )
        elif self.ticket_data["ticket_type"] == TicketType.HDFS_SCALE_UP:
            for dn_ip in self.ticket_data["new_dn_ips"]:
                storage_instances.append(
                    {
                        "ip": dn_ip,
                        "port": DATANODE_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_DATA_NODE.value,
                        "name": HdfsRoleEnum.DataNode.value,
                    }
                )
        elif self.ticket_data["ticket_type"] == TicketType.HDFS_SHRINK:
            for dn_ip in self.ticket_data["del_dn_ips"]:
                storage_instances.append(
                    {
                        "ip": dn_ip,
                        "port": DATANODE_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_DATA_NODE.value,
                        "name": HdfsRoleEnum.DataNode.value,
                    }
                )
        return storage_instances

    def __generate_machine(self) -> list:
        machines = []
        bk_biz_id = self.ticket_data["bk_biz_id"]

        if self.ticket_data["ticket_type"] == TicketType.HDFS_APPLY:
            nn_ips = {self.ticket_data["nn1_ip"], self.ticket_data["nn2_ip"]}
            # 通过遍历 HdfsRoleEnum 区分
            for role, machine_type in self.role_machine_dict.items():
                for node in self.ticket_data["nodes"][role]:
                    # ZK与NN混用时，跳过machine插入
                    if role == HdfsRoleEnum.ZooKeeper.value and node["ip"] in nn_ips:
                        continue
                    machine = {
                        "ip": node["ip"],
                        "bk_biz_id": bk_biz_id,
                        "machine_type": machine_type,
                    }
                    if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
                        machine.update(
                            {
                                "spec_id": self.ticket_data["resource_spec"][role]["id"],
                                "spec_config": self.ticket_data["resource_spec"][role],
                            }
                        )
                    machines.append(machine)
        elif self.ticket_data["ticket_type"] == TicketType.HDFS_SCALE_UP:
            for dn_ip in self.ticket_data["new_dn_ips"]:
                machine = {
                    "ip": dn_ip,
                    "bk_biz_id": bk_biz_id,
                    "machine_type": MachineType.HDFS_DATANODE.value,
                }
                if self.ticket_data["ip_source"] == IpSource.RESOURCE_POOL:
                    machine.update(
                        {
                            "spec_id": self.ticket_data["resource_spec"][HdfsRoleEnum.DataNode.value]["id"],
                            "spec_config": self.ticket_data["resource_spec"][HdfsRoleEnum.DataNode.value],
                        }
                    )
                machines.append(machine)
        elif self.ticket_data["ticket_type"] == TicketType.HDFS_SHRINK:
            for dn_ip in self.ticket_data["del_dn_ips"]:
                machines.append({"ip": dn_ip, "bk_biz_id": bk_biz_id, "machine_type": MachineType.HDFS_DATANODE.value})
        return machines

    def __generate_replace_storage_instance(self, replace_role: str) -> (list, list):
        add_storage_instances = []
        del_storage_instances = []
        if replace_role == HdfsRoleEnum.DataNode.value:
            for dn_ip in self.ticket_data["new_dn_ips"]:
                add_storage_instances.append(
                    {
                        "ip": dn_ip,
                        "port": DATANODE_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_DATA_NODE.value,
                        "name": HdfsRoleEnum.DataNode.value,
                    }
                )
            for dn_ip in self.ticket_data["del_dn_ips"]:
                del_storage_instances.append(
                    {
                        "ip": dn_ip,
                        "port": DATANODE_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_DATA_NODE.value,
                        "name": HdfsRoleEnum.DataNode.value,
                    }
                )
        elif replace_role == HdfsRoleEnum.ZooKeeper.value:
            for zk_ip in self.ticket_data["new_zk_ips"]:
                add_storage_instances.append(
                    {
                        "ip": zk_ip,
                        "port": ZOOKEEPER_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_ZOOKEEPER.value,
                        "name": HdfsRoleEnum.ZooKeeper.value,
                    },
                )
                add_storage_instances.append(
                    {
                        "ip": zk_ip,
                        "port": JOURNAL_NODE_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_JOURNAL_NODE.value,
                        "name": HdfsRoleEnum.JournalNode.value,
                    },
                )
            for zk_ip in self.ticket_data["old_zk_ips"]:
                del_storage_instances.append(
                    {
                        "ip": zk_ip,
                        "port": ZOOKEEPER_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_ZOOKEEPER.value,
                        "name": HdfsRoleEnum.ZooKeeper.value,
                    },
                )
                del_storage_instances.append(
                    {
                        "ip": zk_ip,
                        "port": JOURNAL_NODE_DEFAULT_PORT,
                        "instance_role": InstanceRole.HDFS_JOURNAL_NODE.value,
                        "name": HdfsRoleEnum.JournalNode.value,
                    },
                )
        elif replace_role == HdfsRoleEnum.NameNode.value:
            for nn_ip in self.ticket_data["new_nn_ips"]:
                add_storage_instances.append(
                    {
                        "ip": nn_ip,
                        "port": self.ticket_data["rpc_port"],
                        "instance_role": InstanceRole.HDFS_NAME_NODE.value,
                        "name": HdfsRoleEnum.NameNode.value,
                    }
                )
            for nn_ip in self.ticket_data["old_nn_ips"]:
                del_storage_instances.append(
                    {
                        "ip": nn_ip,
                        "port": self.ticket_data["rpc_port"],
                        "instance_role": InstanceRole.HDFS_NAME_NODE.value,
                        "name": HdfsRoleEnum.NameNode.value,
                    }
                )
        return add_storage_instances, del_storage_instances

    def __generate_replace_machine(self, replace_role: str) -> list:

        machines = []
        bk_biz_id = self.ticket_data["bk_biz_id"]
        if replace_role == HdfsRoleEnum.DataNode.value:
            for dn_ip in self.ticket_data["new_dn_ips"]:
                machines.append({"ip": dn_ip, "bk_biz_id": bk_biz_id, "machine_type": MachineType.HDFS_DATANODE.value})
        elif replace_role == HdfsRoleEnum.NameNode.value:
            for nn_ip in self.ticket_data["new_nn_ips"]:
                if nn_ip not in self.ticket_data["master_ips"]:
                    machines.append(
                        {"ip": nn_ip, "bk_biz_id": bk_biz_id, "machine_type": MachineType.HDFS_MASTER.value}
                    )
        elif replace_role == HdfsRoleEnum.ZooKeeper.value:
            for zk_ip in self.ticket_data["new_zk_ips"]:
                if zk_ip not in self.ticket_data["master_ips"]:
                    machines.append(
                        {"ip": zk_ip, "bk_biz_id": bk_biz_id, "machine_type": MachineType.HDFS_MASTER.value}
                    )
        return machines

    def __create_and_transfer_module(self, cluster_id: int):
        # 创建集群DBMeta后，再调用CC创建集群拓扑
        create_bk_module_for_cluster_id(cluster_id)

        # HDFS主机转移模块、添加对应的服务实例
        cluster = Cluster.objects.get(id=cluster_id)

        master_ips = list(
            set(
                cluster.storageinstance_set.filter(
                    instance_role__in=[
                        InstanceRole.HDFS_NAME_NODE,
                        InstanceRole.HDFS_ZOOKEEPER,
                        InstanceRole.HDFS_JOURNAL_NODE,
                    ]
                ).values_list("machine__ip", flat=True)
            )
        )
        transfer_host_in_cluster_module(
            cluster_id=cluster_id,
            ip_list=master_ips,
            machine_type=MachineType.HDFS_MASTER.value,
            bk_cloud_id=cluster.bk_cloud_id,
            kwargs=self.ticket_data,
        )

        dn_ips = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_DATA_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        transfer_host_in_cluster_module(
            cluster_id=cluster_id,
            ip_list=dn_ips,
            machine_type=MachineType.HDFS_DATANODE.value,
            bk_cloud_id=cluster.bk_cloud_id,
            kwargs=self.ticket_data,
        )
