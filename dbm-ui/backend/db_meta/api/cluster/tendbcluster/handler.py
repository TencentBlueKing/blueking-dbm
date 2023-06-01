"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from typing import List, Optional

from django.db import transaction

from backend.configuration.constants import DBType
from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster
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
        deploy_plan_id: int,
        resource_spec: dict,
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
                    "spec_config": str(resource_spec[MachineType.REMOTE.value]),
                },
            )
        for ip_info in spider_ip_list:
            machines.append(
                {
                    "ip": ip_info["ip"],
                    "bk_biz_id": int(bk_biz_id),
                    "machine_type": MachineType.SPIDER.value,
                    "spec_id": resource_spec[MachineType.SPIDER.value]["id"],
                    "spec_config": str(resource_spec[MachineType.SPIDER.value]),
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
            deploy_plan_id=deploy_plan_id,
            creator=creator,
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
    def slave_cluster_create(cls, cluster_id, creator, spider_version, slave_domain, spider_slaves):
        """对已有的集群添加从集群信息"""
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

        # 录入集群相关信息
        api.cluster.tendbcluster.slave_cluster_create_pre_check(slave_domain=slave_domain)
        api.cluster.tendbcluster.slave_cluster_create(
            cluster=cluster,
            spiders=spiders,
            slave_domain=slave_domain,
            creator=creator,
        )

        # spider主机转移模块、添加对应的服务实例
        transfer_host_in_cluster_module(
            cluster_ids=[cluster_id],
            ip_list=[ip_info["ip"] for ip_info in spider_slaves],
            machine_type=MachineType.SPIDER.value,
            bk_cloud_id=cluster.bk_cloud_id,
        )
