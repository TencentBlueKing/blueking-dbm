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
from typing import Optional

from django.db import transaction
from django.db.transaction import atomic

from backend.db_meta.api.cluster.tendbcluster.handler import TenDBClusterClusterHandler
from backend.db_meta.api.cluster.tendbcluster.remotedb_node_migrate import TenDBClusterMigrateRemoteDb
from backend.db_meta.enums import InstanceStatus, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.utils.dict_to_dataclass import dict_to_dataclass
from backend.flow.utils.spider.spider_act_dataclass import ShardInfo

logger = logging.getLogger("flow")


class SpiderDBMeta(object):
    """
    根据spider（tendb cluster）集群单据信息和集群信息，更新cmdb
    """

    def __init__(self, global_data: dict, cluster: dict = None):
        """
        @param global_data : 单据信息,对应流程中的global_data
        @param cluster: 集群信息
        """
        self.global_data = global_data
        self.cluster = cluster

        if not self.cluster:
            self.cluster = {}

    def tendb_cluster_apply(self):
        """
        添加tendb cluster（spider集群）集群元数据的逻辑
        """
        # 部署spider集群，更新cmdb
        # 这里采用dict转换到 ShardInfo 类型数据结构体，让后续代码可读性更高
        shard_infos = []
        def_resource_spec = {MachineType.REMOTE.value: {"id": 0}, MachineType.SPIDER.value: {"id": 0}}
        for info in self.cluster["shard_infos"]:
            shard_infos.append(dict_to_dataclass(data_dict=info, data_class=ShardInfo))

        kwargs = {
            "bk_biz_id": int(self.global_data["bk_biz_id"]),
            "db_module_id": int(self.global_data["module"]),
            "cluster_name": self.global_data["cluster_name"],
            "immutable_domain": self.global_data["immutable_domain"],
            "mysql_version": self.global_data["db_version"],
            "spider_version": self.global_data["spider_version"],
            "mysql_ip_list": self.global_data["mysql_ip_list"],
            "spider_ip_list": self.global_data["spider_ip_list"],
            "spider_port": int(self.global_data["spider_port"]),
            "ctl_port": int(self.global_data["ctl_port"]),
            "creator": self.global_data["created_by"],
            "time_zone": self.cluster["time_zone_info"]["time_zone"],
            "bk_cloud_id": int(self.global_data["bk_cloud_id"]),
            "resource_spec": self.global_data.get("resource_spec") or def_resource_spec,
            "shard_infos": shard_infos,
            "region": self.global_data["city"],
            "disaster_tolerance_level": self.global_data["disaster_tolerance_level"],
        }
        TenDBClusterClusterHandler.create(**kwargs)
        return True

    def tendb_cluster_destroy(self):
        """
        回收tendb cluster（spider集群）集群元数据的逻辑
        """
        TenDBClusterClusterHandler(
            bk_biz_id=self.global_data["bk_biz_id"], cluster_id=self.cluster["id"]
        ).decommission()
        return True

    def tendb_cluster_slave_apply(self):
        """
        对已有的TenDB cluster集群 （spider集群）添加从集群（只读接入层）
        """
        kwargs = {
            "cluster_id": self.global_data["cluster_id"],
            "creator": self.global_data["created_by"],
            "add_spiders": self.global_data["spider_slave_ip_list"],
            "spider_role": TenDBClusterSpiderRole.SPIDER_SLAVE,
            "is_slave_cluster_create": True,
            "new_slave_domain": self.global_data["slave_domain"],
        }
        TenDBClusterClusterHandler.add_spiders(**kwargs)
        return True

    def add_spider_nodes(self, spider_role: Optional[TenDBClusterSpiderRole]):
        """
        对已有的TenDB cluster集群 （spider集群）扩容写入的公共方法
        """
        kwargs = {
            "cluster_id": self.global_data["cluster_id"],
            "creator": self.global_data["created_by"],
            "add_spiders": self.global_data["spider_ip_list"],
            "spider_role": spider_role,
            "is_slave_cluster_create": False,
            "new_db_module_id": self.global_data.get("new_db_module_id", 0),
        }
        TenDBClusterClusterHandler.add_spiders(**kwargs)
        return True

    def add_spider_slave_nodes_apply(self):
        """
        对已有的TenDB cluster集群 （spider集群）扩容spider-slave节点
        """
        self.add_spider_nodes(spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE)

    def add_spider_master_nodes_apply(self):
        """
        对已有的TenDB cluster集群 （spider集群）扩容spider-master节点
        """
        self.add_spider_nodes(spider_role=TenDBClusterSpiderRole.SPIDER_MASTER)

    def reduce_spider_nodes_apply(self):
        """
        对已有的TenDB cluster集群 （spider集群）缩容spider节点，这里不区分spider角色
        """
        TenDBClusterClusterHandler.reduce_spider(
            cluster_id=self.global_data["cluster_id"],
            spiders=self.global_data["reduce_spiders"],
        )
        return True

    def del_spider_nodes_meta(self):
        """
        删除spider db meta
        """
        cluster_id = self.cluster["cluster_id"]
        replace_spiders = self.cluster["spiders"]
        TenDBClusterClusterHandler.reduce_spider(
            cluster_id=cluster_id,
            spiders=replace_spiders,
        )
        return True

    def add_spider_mnt(self):
        """
        对已有的TenDB cluster集群 （spider集群）扩容spider-mnt节点
        """
        self.add_spider_nodes(spider_role=TenDBClusterSpiderRole.SPIDER_MNT)

    def remote_switch(self):
        """
        对已执行remote互切/主故障切换后的集群做元数据的调整
        """
        TenDBClusterClusterHandler.remote_switch(
            cluster_id=self.cluster["cluster_id"],
            switch_tuples=self.cluster["switch_tuples"],
            force=self.cluster["force"],
        )
        return True

    def remotedb_migrate_add_install_nodes(self):
        """
        remotedb 成对迁移添加初始化节点元数据
        """
        # cluster = Cluster.objects.get(id=self.cluster["cluster_id"])
        # old_resource_spec = {MachineType.REMOTE.value: cluster.storageinstance_set.first().machine.spec_config}
        # 不继承参数，如果无resource_spec参数则留空
        default_resource_spec = {MachineType.REMOTE.value: {"id": 0}}
        resource_spec = self.global_data.get("resource_spec", {})
        if MachineType.REMOTE.value not in resource_spec:
            resource_spec = default_resource_spec

        TenDBClusterMigrateRemoteDb.storage_create(
            cluster_id=self.cluster["cluster_id"],
            master_ip=self.cluster["new_master_ip"],
            slave_ip=self.cluster["new_slave_ip"],
            ports=self.cluster["ports"],
            creator=self.global_data["created_by"],
            mysql_version=self.cluster["version"],
            # 兼容资源池和手输机器两种情况
            resource_spec=resource_spec,
        )
        return True

    def remotedb_migrate_add_storage_tuple(self):
        """
        写入真实的主从对应关系
        新从库->新主库
        新主库->旧主库(这条关系链在切换完毕后需要断开)
        """
        new_slave_to_new_master = {
            "master": {"ip": self.cluster["new_master_ip"], "port": self.cluster["new_master_port"]},
            "slave": {"ip": self.cluster["new_slave_ip"], "port": self.cluster["new_slave_port"]},
        }
        TenDBClusterMigrateRemoteDb.add_storage_tuple(
            cluster_id=self.cluster["cluster_id"], storage=new_slave_to_new_master
        )
        new_master_to_old_master = {
            "slave": {"ip": self.cluster["new_master_ip"], "port": self.cluster["new_master_port"]},
            "master": {"ip": self.cluster["master_ip"], "port": self.cluster["master_port"]},
        }
        TenDBClusterMigrateRemoteDb.add_storage_tuple(
            cluster_id=self.cluster["cluster_id"], storage=new_master_to_old_master
        )

    def remotedb_migrate_switch(self):
        for port in self.cluster["ports"]:
            source = {
                "master": {"ip": self.cluster["master_ip"], "port": port},
                "slave": {"ip": self.cluster["slave_ip"], "port": port},
            }
            target = {
                "master": {"ip": self.cluster["new_master_ip"], "port": port},
                "slave": {"ip": self.cluster["new_slave_ip"], "port": port},
            }
            TenDBClusterMigrateRemoteDb.switch_remote_node(
                cluster_id=self.cluster["cluster_id"], source=source, target=target
            )

    def remotedb_migrate_remove_storage(self):
        TenDBClusterMigrateRemoteDb.uninstall_storage(
            cluster_id=self.cluster["cluster_id"], ip=self.cluster["uninstall_ip"]
        )

    @transaction.atomic
    def tendb_remotedb_rebalance_switch(self):
        for node in self.cluster["shards"].values():
            source = {
                "master": {"ip": node["master"]["ip"], "port": node["master"]["port"]},
                "slave": {"ip": node["slave"]["ip"], "port": node["slave"]["port"]},
            }
            target = {
                "master": {"ip": node["new_master"]["ip"], "port": node["new_master"]["port"]},
                "slave": {"ip": node["new_slave"]["ip"], "port": node["new_slave"]["port"]},
            }
            TenDBClusterMigrateRemoteDb.switch_remote_node(
                cluster_id=self.cluster["cluster_id"], source=source, target=target
            )

    def tendb_cluster_slave_destroy(self):
        """
        清理只读接入层剩余元数据信息
        """
        kwargs = {
            "cluster_id": self.global_data["cluster_id"],
        }
        TenDBClusterClusterHandler.clear_clusterentry(**kwargs)
        return True

    def tendb_slave_recover_add_nodes(self):
        """
        remotedb 成对迁移添加初始化节点元数据
        """
        # cluster = Cluster.objects.get(id=self.cluster["cluster_id"])
        # 不继承参数，如果无resource_spec参数则留空。以防出现规格错误
        # old_resource_spec = {MachineType.REMOTE.value: cluster.storageinstance_set.first().machine.spec_config}
        default_resource_spec = {MachineType.REMOTE.value: {"id": 0}}
        resource_spec = self.global_data.get("resource_spec", {})
        if MachineType.REMOTE.value not in resource_spec:
            resource_spec = default_resource_spec

        TenDBClusterMigrateRemoteDb.storage_create(
            cluster_id=self.cluster["cluster_id"],
            slave_ip=self.cluster["new_slave_ip"],
            ports=self.cluster["ports"],
            creator=self.global_data["created_by"],
            mysql_version=self.cluster["version"],
            # 兼容资源池和手输机器两种情况
            resource_spec=resource_spec,
        )
        return True

    def tendb_slave_recover_add_tuple(self):
        with atomic():
            new_slave_to_old_master = {
                "master": {"ip": self.cluster["master_ip"], "port": self.cluster["master_port"]},
                "slave": {"ip": self.cluster["new_slave_ip"], "port": self.cluster["new_slave_port"]},
            }
            TenDBClusterMigrateRemoteDb.add_storage_tuple(
                cluster_id=self.cluster["cluster_id"], storage=new_slave_to_old_master
            )
            StorageInstance.objects.filter(
                machine__ip=self.cluster["new_slave_ip"],
                machine__bk_cloud_id=self.cluster["bk_cloud_id"],
                port=self.cluster["new_slave_port"],
            ).update(status=InstanceStatus.RUNNING.value)
            # slave_storages = StorageInstance.objects.filter(machine__ip=self.cluster["new_slave_port"],
            # machine__bk_cloud_id=self.cluster["bk_cloud_id"])
            # for slave_storage in slave_storages:
            #     slave_storage.status=InstanceStatus.RUNNING.value
            #     slave_storage.save()

    def tendb_modify_cluster_phase(self):
        Cluster.objects.filter(id=self.cluster["cluster_id"]).update(phase=self.cluster["cluster_phase"])

    def tendb_modify_storage_status(self):
        StorageInstance.objects.filter(id__in=self.cluster["storage_ids"]).update(
            status=self.cluster["storage_status"]
        )

    def tendb_modify_proxy_status(self):
        ProxyInstance.objects.filter(id__in=self.cluster["proxy_ids"]).update(status=self.cluster["proxy_status"])

    def tendb_slave_recover_switch(self):
        for node in self.cluster["my_shards"].values():
            source = {
                "master": {"ip": node["master"]["ip"], "port": node["master"]["port"]},
                "slave": {"ip": node["slave"]["ip"], "port": node["slave"]["port"]},
            }
            target = {
                "master": {"ip": node["master"]["ip"], "port": node["master"]["port"]},
                "slave": {"ip": node["new_slave"]["ip"], "port": node["new_slave"]["port"]},
            }
            TenDBClusterMigrateRemoteDb.switch_remote_node(
                cluster_id=self.cluster["cluster_id"], source=source, target=target
            )
