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
from django.db.models import F
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import (
    ClusterEntryRole,
    ClusterEntryType,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    MachineType,
    TenDBClusterSpiderRole,
)
from backend.db_meta.exceptions import InstanceNotExistException
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, StorageInstanceTuple
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum, TenDBBackUpLocation
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version, get_spider_real_version
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.mysql.mysql_module_operate import MysqlCCTopoOperator
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
        storage_objs = api.storage_instance.create(instances=storages, creator=creator, time_zone=time_zone)
        proxy_objs = api.proxy_instance.create(proxies=spiders, creator=creator, time_zone=time_zone)

        # 录入集群的相关云信息
        api.cluster.tendbcluster.create_pre_check(
            bk_biz_id=bk_biz_id, name=cluster_name, immutable_domain=immutable_domain, db_module_id=db_module_id
        )
        cluster = api.cluster.tendbcluster.create(
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

        cc_topo_operator = MysqlCCTopoOperator(cluster)
        # mysql主机转移模块、添加对应的服务实例
        cc_topo_operator.transfer_instances_to_cluster_module(storage_objs)
        # spider主机转移模块、添加对应的服务实例
        cc_topo_operator.transfer_instances_to_cluster_module(proxy_objs)

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
    def add_spiders(
        cls,
        cluster_id: int,
        creator: str,
        spider_version: str,
        add_spiders: list,
        spider_role: Optional[TenDBClusterSpiderRole],
        resource_spec: dict,
        is_slave_cluster_create: bool,
        domain: str = None,
    ):
        """
        对已有的集群添加spider的元信息
        因为从集群添加的行为spider-slave扩容行为基本类似，所以这里作为一个公共方法，对域名处理根据不同单据类型做不同的处理
        @param cluster_id: 待关联的集群id
        @param creator: 提单的用户名称
        @param spider_version: 待加入的spider版本号（包括小版本信息）
        @param domain: 待关联的域名
        @param add_spiders: 待加入的spider机器信息
        @param spider_role: 待加入spider的角色
        @param resource_spec: 待加入spider的规格
        @param is_slave_cluster_create: 代表这次是否是添加从集群
        """
        cluster = Cluster.objects.get(id=cluster_id)

        # 录入机器
        machines = []
        for ip_info in add_spiders:
            machines.append(
                {
                    "ip": ip_info["ip"],
                    "bk_biz_id": cluster.bk_biz_id,
                    "machine_type": MachineType.SPIDER.value,
                    "spec_id": resource_spec[MachineType.SPIDER.value]["id"],
                    "spec_config": resource_spec[MachineType.SPIDER.value],
                },
            )
        # 录入机器信息
        api.machine.create(machines=machines, creator=creator, bk_cloud_id=cluster.bk_cloud_id)

        # 录入机器对应的实例信息
        spiders = []
        spider_pkg = Package.get_latest_package(
            version=spider_version, pkg_type=MediumEnum.Spider, db_type=DBType.MySQL
        )

        for ip_info in add_spiders:
            spiders.append(
                {
                    "ip": ip_info["ip"],
                    "port": cluster.proxyinstance_set.first().port,
                    "admin_port": cluster.proxyinstance_set.first().admin_port,
                    "version": get_spider_real_version(spider_pkg.name),
                }
            )
        # 新增的实例继承cluster集群的时区设置
        spider_objs = api.proxy_instance.create(proxies=spiders, creator=creator, time_zone=cluster.time_zone)

        # 判断is_slave_cluster_create参数，如果是True则代表做从集群添加，需要添加从域名元信息；如果False则代表spider扩容
        if is_slave_cluster_create:
            api.cluster.tendbcluster.slave_cluster_create_pre_check(slave_domain=domain)
            cluster_entry = ClusterEntry.objects.create(
                cluster=cluster,
                cluster_entry_type=ClusterEntryType.DNS,
                entry=domain,
                creator=creator,
                role=ClusterEntryRole.SLAVE_ENTRY.value,
            )
        else:
            if domain:
                cluster_entry = cluster.clusterentry_set.get(entry=domain)
            else:
                # 运维节点添加不需要做域名映射
                cluster_entry = None

        # 录入集群相关信息
        api.cluster.tendbcluster.add_spiders(
            cluster=cluster, spiders=spiders, domain_entry=cluster_entry, spider_role=spider_role
        )

        # spider主机转移模块、添加对应的服务实例
        MysqlCCTopoOperator(cluster).transfer_instances_to_cluster_module(spider_objs)

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
        cc_manage = CcManage(cluster.bk_biz_id, DBType.TenDBCluster.value)
        for info in spiders:
            # 同一台spider机器专属于一个集群
            spider = cluster.proxyinstance_set.get(machine__ip=info["ip"])
            # 先删除额外的spider关联信息，否则直接删除实例，会报ProtectedError 异常
            spider.tendbclusterspiderext.delete()
            spider.delete(keep_parents=True)
            if not spider.machine.proxyinstance_set.exists():
                # 这个 api 不需要检查返回值, 转移主机到空闲模块，转移模块这里会把服务实例删除
                cc_manage.recycle_host([spider.machine.bk_host_id])
                spider.machine.delete(keep_parents=True)

    @classmethod
    @transaction.atomic
    def remote_switch(cls, cluster_id: int, switch_tuples: list):
        """
        对已有集群的remote存储对进行切换记录
        """
        cluster = Cluster.objects.get(id=cluster_id)
        cc_manage = CcManage(cluster.bk_biz_id, DBType.TenDBCluster.value)
        for switch_tuple in switch_tuples:
            # 理论上remote机器专属一套TenDB-Cluster集群

            # 机器所有的实例更改角色
            slave_objs = cluster.storageinstance_set.filter(machine__ip=switch_tuple["slave"]["ip"])
            master_objs = cluster.storageinstance_set.filter(machine__ip=switch_tuple["master"]["ip"])
            slave_objs.update(instance_role=InstanceRole.REMOTE_MASTER, instance_inner_role=InstanceInnerRole.MASTER)
            master_objs.update(instance_role=InstanceRole.REMOTE_SLAVE, instance_inner_role=InstanceInnerRole.SLAVE)

            # 修改主从的映射关系
            for obj in master_objs:
                StorageInstanceTuple.objects.filter(ejector=obj).update(ejector=F("receiver"), receiver=obj)

            # 切换新master服务实例角色标签
            cc_manage.add_label_for_service_instance(
                bk_instance_ids=[obj.bk_instance_id for obj in slave_objs],
                labels_dict={"instance_role": InstanceRole.REMOTE_MASTER.value},
            )

            # 切换新slave服务实例角色标签
            cc_manage.add_label_for_service_instance(
                bk_instance_ids=[obj.bk_instance_id for obj in master_objs],
                labels_dict={"instance_role": InstanceRole.REMOTE_SLAVE.value},
            )

    def get_remote_address(self, role=TenDBBackUpLocation.REMOTE) -> str:
        """
        查询DRS访问远程数据库的地址，你默认查询remote的db
        """
        proxy_role = (
            TenDBClusterSpiderRole.SPIDER_MASTER
            if role == TenDBBackUpLocation.REMOTE
            else TenDBClusterSpiderRole.SPIDER_MNT
        )

        inst = ProxyInstance.objects.filter(cluster=self.cluster, tendbclusterspiderext__spider_role=proxy_role)
        if not inst:
            raise InstanceNotExistException(_("集群{}不具有该角色「{}」的实例").format(self.cluster.name, proxy_role))

        return inst.first().ip_port

    @classmethod
    @transaction.atomic
    def clear_clusterentry(cls, cluster_id: int):
        cluster = Cluster.objects.get(id=cluster_id)
        clusterentry = cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
        ).all()
        for ce in clusterentry:
            ce.delete(keep_parents=True)
