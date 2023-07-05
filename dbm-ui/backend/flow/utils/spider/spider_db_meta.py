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

from backend.db_meta.api.cluster.tendbcluster.handler import TenDBClusterClusterHandler
from backend.db_meta.enums import ClusterEntryRole
from backend.db_meta.models import Cluster
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
            "resource_spec": self.global_data["resource_spec"],
            "shard_infos": shard_infos,
            "region": self.global_data["city"],
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
        对已有的TenDB cluster集群 （spider集群）添加从集群（只读集群）
        """
        kwargs = {
            "cluster_id": self.global_data["cluster_id"],
            "creator": self.global_data["created_by"],
            "spider_version": self.global_data["spider_version"],
            "slave_domain": self.global_data["slave_domain"],
            "spider_slaves": self.global_data["spider_slave_ip_list"],
            "is_create": True,
        }
        TenDBClusterClusterHandler.add_spider_slaves(**kwargs)
        return True

    def add_spider_slave_nodes_apply(self):
        """
        对已有的TenDB cluster集群 （spider集群）扩容spider-slave节点
        """
        cluster = Cluster.objects.get(id=self.global_data["cluster_id"])
        slave_dns = cluster.clusterentry_set.get(role=ClusterEntryRole.SLAVE_ENTRY).entry
        kwargs = {
            "cluster_id": self.global_data["cluster_id"],
            "creator": self.global_data["created_by"],
            "spider_version": self.global_data["spider_version"],
            "slave_domain": slave_dns,
            "spider_slaves": self.global_data["spider_ip_list"],
            "is_create": False,
        }
        TenDBClusterClusterHandler.add_spider_slaves(**kwargs)
        return True

    def add_spider_master_nodes_apply(self):
        """
        对已有的TenDB cluster集群 （spider集群）扩容spider-master节点
        todo 后续tdbctl新版本出现在补齐
        """
        return True

    def reduce_spider_nodes_apply(self):
        """
        对已有的TenDB cluster集群 （spider集群）缩容spider节点，这里不区分spider角色
        """
        TenDBClusterClusterHandler.reduce_spider(
            cluster_id=self.global_data["cluster_id"],
            spiders=self.global_data["reduce_spiders"],
        )
        return True

    def add_spider_mnt(self):
        """
        已有集群添加运维节点
        """
        kwargs = {
            "cluster_id": self.global_data["cluster_id"],
            "creator": self.global_data["created_by"],
            "spider_version": self.global_data["spider_version"],
            "spider_mnts": self.global_data["spider_ip_list"],
        }
        TenDBClusterClusterHandler.spider_mnt_create(**kwargs)
        return True
