"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import json
from typing import List, Optional

from django.db import transaction

from backend import env
from backend.components import CCApi
from backend.configuration.constants import DBType
from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version, get_spider_real_version
from backend.flow.utils.mysql.bk_module_operate import create_bk_module_for_cluster_id, transfer_host_in_cluster_module
from backend.flow.utils.spider.spider_act_dataclass import ShardInfo


class TenDBClusterClusterHandler(ClusterHandler):
    # 「必须」 集群类型
    cluster_type = ClusterType.TenDBCluster

    @classmethod
    @transaction.atomic
    def create(
        cls,
        bk_biz_id: int,
        db_module_id: int,
        cluster_name: str,
        immutable_domain: str,
        mysql_version: str,
        spider_version: str,
        mysql_ip_list: list,
        spider_ip_list: list,
        spider_port: int,
        ctl_port: int,
        creator: str,
        time_zone: str,
        bk_cloud_id: int,
        shard_infos: Optional[List[ShardInfo]],
        resource_spec: dict,
        region: str,
    ):
        """「必须」创建spider集群"""

        # 录入机器
        machines = []
        for ip_info in mysql_ip_list:
            machines.append(
                {
                    "ip": ip_info["ip"],
                    "bk_biz_id": int(bk_biz_id),
                    "machine_type": MachineType.REMOTE.value,
                    "spec_id": resource_spec[MachineType.REMOTE.value]["id"],
                    "spec_config": resource_spec[MachineType.REMOTE.value],
                },
            )
        for ip_info in spider_ip_list:
            machines.append(
                {
                    "ip": ip_info["ip"],
                    "bk_biz_id": int(bk_biz_id),
                    "machine_type": MachineType.SPIDER.value,
                    "spec_id": resource_spec[MachineType.SPIDER.value]["id"],
                    "spec_config": resource_spec[MachineType.SPIDER.value],
                },
            )

        api.machine.create(machines=machines, creator=creator, bk_cloud_id=bk_cloud_id)

        # 录入机器对应的实例信息
        storages = []
        spiders = []
        mysql_pkg = Package.get_latest_package(version=mysql_version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
        spider_pkg = Package.get_latest_package(
            version=spider_version, pkg_type=MediumEnum.Spider, db_type=DBType.MySQL
        )
        for info in shard_infos:
            storages.append(
                {
                    "ip": info.instance_tuple.master_ip,
                    "port": info.instance_tuple.mysql_port,
                    "instance_role": InstanceRole.REMOTE_MASTER.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": get_mysql_real_version(mysql_pkg.name),  # 存储真正的版本号信息
                },
            )
            storages.append(
                {
                    "ip": info.instance_tuple.slave_ip,
                    "port": info.instance_tuple.mysql_port,
                    "instance_role": InstanceRole.REMOTE_SLAVE.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": get_mysql_real_version(mysql_pkg.name),  # 存储真正的版本号信息
                },
            )

        for ip_info in spider_ip_list:
            spiders.append(
                {
                    "ip": ip_info["ip"],
                    "port": spider_port,
                    "admin_port": ctl_port,
                    "version": get_spider_real_version(spider_pkg.name),
                }
            )
        api.storage_instance.create(instances=storages, creator=creator, time_zone=time_zone)
        api.proxy_instance.create(proxies=spiders, creator=creator, time_zone=time_zone)

        # 录入集群的相关云信息
        api.cluster.tendbcluster.create_pre_check(
            bk_biz_id=bk_biz_id, name=cluster_name, immutable_domain=immutable_domain, db_module_id=db_module_id
        )
        cluster_id = api.cluster.tendbcluster.create(
            bk_biz_id=bk_biz_id,
            name=cluster_name,
            immutable_domain=immutable_domain,
            major_version=mysql_version,
            db_module_id=db_module_id,
            bk_cloud_id=bk_cloud_id,
            shard_infos=shard_infos,
            time_zone=time_zone,
            spiders=spiders,
            storages=storages,
            creator=creator,
            region=region,
        )

        # 生成域名模块
        create_bk_module_for_cluster_id(cluster_ids=[cluster_id])

        # mysql主机转移模块、添加对应的服务实例
        transfer_host_in_cluster_module(
            cluster_ids=[cluster_id],
            ip_list=[ip_info["ip"] for ip_info in mysql_ip_list],
            machine_type=MachineType.REMOTE.value,
            bk_cloud_id=bk_cloud_id,
        )

        # spider主机转移模块、添加对应的服务实例
        transfer_host_in_cluster_module(
            cluster_ids=[cluster_id],
            ip_list=[ip_info["ip"] for ip_info in spider_ip_list],
            machine_type=MachineType.SPIDER.value,
            bk_cloud_id=bk_cloud_id,
        )

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群"""
        api.cluster.tendbcluster.decommission_precheck(self.cluster)
        api.cluster.tendbcluster.decommission(self.cluster)

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        pass

    @classmethod
    @transaction.atomic
    def add_spider_slaves(
        cls,
        cluster_id: int,
        creator: str,
        spider_version: str,
        slave_domain: str,
        spider_slaves: list,
        is_create: bool,
    ):
        """
        对已有的集群添加从集群信息
        因为从集群添加的行为spider-slave扩容行为基本类似，所以这里作为一个公共方法，对域名处理根据不同单据类型做不同的处理
        @param cluster_id: 待关联的集群id
        @param creator: 提单的用户名称
        @param spider_version: 待加入的spider版本号（包括小版本信息）
        @param slave_domain: 待添加从域名
        @param spider_slaves: 待加入的spider-slave机器信息
        @param is_create: 代表这次是否是添加从集群，还是spider-slave扩容
        """
        cluster = Cluster.objects.get(id=cluster_id)

        # 录入机器
        machines = []
        for ip_info in spider_slaves:
            machines.append(
                {
                    "ip": ip_info["ip"],
                    "bk_biz_id": cluster.bk_biz_id,
                    "machine_type": MachineType.SPIDER.value,
                },
            )
        # 录入机器信息
        api.machine.create(machines=machines, creator=creator, bk_cloud_id=cluster.bk_cloud_id)

        # 录入机器对应的实例信息
        spiders = []
        spider_pkg = Package.get_latest_package(
            version=spider_version, pkg_type=MediumEnum.Spider, db_type=DBType.MySQL
        )

        for ip_info in spider_slaves:
            spiders.append(
                {
                    "ip": ip_info["ip"],
                    "port": cluster.proxyinstance_set.first().port,
                    "admin_port": cluster.proxyinstance_set.first().admin_port,  # spider_slave是否存储管理端口？
                    "version": get_spider_real_version(spider_pkg.name),
                }
            )
        # 新增的实例继承cluster集群的时区设置
        api.proxy_instance.create(proxies=spiders, creator=creator, time_zone=cluster.time_zone)

        # 判断is_create参数，如果是True则代表做从集群添加，需要添加从域名元信息；如果False则代表spider-slave扩容
        if is_create:
            api.cluster.tendbcluster.slave_cluster_create_pre_check(slave_domain=slave_domain)
            cluster_slave_entry = ClusterEntry.objects.create(
                cluster=cluster,
                cluster_entry_type=ClusterEntryType.DNS,
                entry=slave_domain,
                creator=creator,
                role=ClusterEntryRole.SLAVE_ENTRY.value,
            )
        else:
            cluster_slave_entry = cluster.clusterentry_set.get(entry=slave_domain)

        # 录入集群相关信息
        api.cluster.tendbcluster.add_spider_slaves(
            cluster=cluster, spiders=spiders, cluster_slave_entry=cluster_slave_entry
        )

        # spider主机转移模块、添加对应的服务实例
        transfer_host_in_cluster_module(
            cluster_ids=[cluster_id],
            ip_list=[ip_info["ip"] for ip_info in spider_slaves],
            machine_type=MachineType.SPIDER.value,
            bk_cloud_id=cluster.bk_cloud_id,
        )

    @classmethod
    @transaction.atomic
    def add_spider_master(
        cls,
        cluster_id: int,
        creator: str,
        spider_masters: list,
    ):
        pass

    @classmethod
    @transaction.atomic
    def reduce_spider(
        cls,
        cluster_id: int,
        spiders: list,
    ):
        """
        对已有的集群删除待卸载的spider节点
        """
        cluster = Cluster.objects.get(id=cluster_id)
        for info in spiders:
            # 同一台spider机器专属于一个集群
            spider = cluster.proxyinstance_set.get(machine__ip=info["ip"])
            # 先删除额外的spider关联信息，否则直接删除实例，会报ProtectedError 异常
            spider.tendbclusterspiderext.delete()
            spider.delete(keep_parents=True)
            if not spider.machine.proxyinstance_set.exists():
                # 这个 api 不需要检查返回值, 转移主机到空闲模块，转移模块这里会把服务实例删除
                CCApi.transfer_host_to_recyclemodule(
                    {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [spider.machine.bk_host_id]}
                )
                spider.machine.delete(keep_parents=True)

    def spider_mnt_create(cls, cluster_id, creator, spider_version, spider_mnts):
        """
        对已有的集群添加临时节点信息
        根据cluster_id获取相关的cluster信息
        """
        cluster = Cluster.objects.get(id=cluster_id)

        # 录入机器
        machines = []
        for ip_info in spider_mnts:
            machines.append(
                {
                    "ip": ip_info["ip"],
                    "bk_biz_id": cluster.bk_biz_id,
                    "machine_type": MachineType.SPIDER.value,
                },
            )
        # # 录入机器信息
        api.machine.create(machines=machines, creator=creator, bk_cloud_id=cluster.bk_cloud_id)

        # 录入机器对应的实例信息
        spiders = []
        spider_pkg = Package.get_latest_package(
            version=spider_version, pkg_type=MediumEnum.Spider, db_type=DBType.MySQL
        )

        for ip_info in spider_mnts:
            spiders.append(
                {
                    "ip": ip_info["ip"],
                    "port": cluster.proxyinstance_set.first().port,
                    "admin_port": cluster.proxyinstance_set.first().admin_port,  # spider_slave是否存储管理端口？
                    "version": get_spider_real_version(spider_pkg.name),
                }
            )
        # # 新增的实例继承cluster集群的时区设置
        api.proxy_instance.create(proxies=spiders, creator=creator, time_zone=cluster.time_zone)

        # 录入集群相关信息
        # 这里区分与从域名的与检查从域名，不用检查域名，应为已经有了cluster id，主域名是必然存在的
        api.cluster.tendbcluster.add_spider_mnt(
            cluster=cluster,
            spiders=spiders,
        )

        # spider主机转移模块、添加对应的服务实例
        transfer_host_in_cluster_module(
            cluster_ids=[cluster_id],
            ip_list=[ip_info["ip"] for ip_info in spider_mnts],
            machine_type=MachineType.SPIDER.value,
            bk_cloud_id=cluster.bk_cloud_id,
        )
