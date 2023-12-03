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

from backend.configuration.constants import DBType
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta import api
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.models import StorageInstance
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version
from backend.flow.utils.mysql.mysql_module_operate import MysqlCCTopoOperator

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
        resource_spec: dict,
        region: str,
    ):
        """「必须」创建集群,多实例录入方式"""

        # 录入机器
        machines = [
            {
                "ip": cluster_ip_dict["new_master_ip"],
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.BACKEND.value,
                "spec_id": resource_spec[MachineType.BACKEND.value]["id"],
                "spec_config": resource_spec[MachineType.BACKEND.value],
            },
            {
                "ip": cluster_ip_dict["new_slave_ip"],
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.BACKEND.value,
                "spec_id": resource_spec[MachineType.BACKEND.value]["id"],
                "spec_config": resource_spec[MachineType.BACKEND.value],
            },
            {
                "ip": cluster_ip_dict["new_proxy_1_ip"],
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.PROXY.value,
                "spec_id": resource_spec[MachineType.PROXY.value]["id"],
                "spec_config": resource_spec[MachineType.PROXY.value],
            },
            {
                "ip": cluster_ip_dict["new_proxy_2_ip"],
                "bk_biz_id": int(bk_biz_id),
                "machine_type": MachineType.PROXY.value,
                "spec_id": resource_spec[MachineType.PROXY.value]["id"],
                "spec_config": resource_spec[MachineType.PROXY.value],
            },
        ]
        api.machine.create(machines=machines, creator=creator, bk_cloud_id=bk_cloud_id)

        # 录入机器对应的集群信息
        new_clusters = []
        mysql_pkg = Package.get_latest_package(version=major_version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)

        storage_objs = []
        proxy_objs = []
        for cluster in clusters:
            name = cluster["name"]
            immute_domain = cluster["master"]
            slave_domain = cluster["slave"]
            storages = [
                {
                    "ip": cluster_ip_dict["new_master_ip"],
                    "port": cluster["mysql_port"],
                    "instance_role": InstanceRole.BACKEND_MASTER.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": get_mysql_real_version(mysql_pkg.name),  # 存储真正的版本号信息
                },
                {
                    "ip": cluster_ip_dict["new_slave_ip"],
                    "port": cluster["mysql_port"],
                    "instance_role": InstanceRole.BACKEND_SLAVE.value,
                    "is_stand_by": True,  # 标记实例属于切换组实例
                    "db_version": get_mysql_real_version(mysql_pkg.name),  # 存储真正的版本号信息
                },
            ]
            proxies = [
                {"ip": cluster_ip_dict["new_proxy_1_ip"], "port": cluster["proxy_port"]},
                {"ip": cluster_ip_dict["new_proxy_2_ip"], "port": cluster["proxy_port"]},
            ]
            api.cluster.tendbha.create_precheck(bk_biz_id, name, immute_domain, db_module_id, slave_domain)
            storage_objs.extend(api.storage_instance.create(instances=storages, creator=creator, time_zone=time_zone))
            proxy_objs.extend(api.proxy_instance.create(proxies=proxies, creator=creator, time_zone=time_zone))
            new_clusters.append(
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
                    region=region,
                )
            )

        cc_topo_operator = MysqlCCTopoOperator(new_clusters)
        # mysql主机转移模块、添加对应的服务实例
        cc_topo_operator.transfer_instances_to_cluster_module(storage_objs)

        # proxy主机转移模块、添加对应的服务实例
        cc_topo_operator.transfer_instances_to_cluster_module(proxy_objs)

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

    def get_remote_address(self) -> StorageInstance:
        """查询DRS访问远程数据库的地址"""
        return StorageInstance.objects.get(
            cluster=self.cluster, instance_inner_role=InstanceInnerRole.MASTER.value
        ).ip_port

    @transaction.atomic
    def add_tbinlogdumper(self, add_confs: list):
        """
        添加TBinlogDumper实例的信息
        """
        master = self.cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
        for conf in add_confs:
            tbinlogdumper = ExtraProcessInstance(
                bk_biz_id=self.cluster.bk_biz_id,
                cluster_id=self.cluster.id,
                bk_cloud_id=self.cluster.bk_cloud_id,
                ip=master.machine.ip,
                proc_type=ExtraProcessType.TBINLOGDUMPER,
                version="",
                listen_port=conf["port"],
                extra_config={
                    "dumper_id": str(conf["area_name"]),
                    "area_name": str(conf["area_name"]),
                    "source_data_ip": master.machine.ip,
                    "source_data_port": master.port,
                    "repl_tables": conf["repl_tables"],
                    "target_address": conf["target_address"],
                    "target_port": conf["target_port"],
                    "protocol_type": conf["protocol_type"],
                    "l5_modid": conf.get("l5_modid", 0),
                    "l5_cmdid": conf.get("l5_cmdid", 0),
                    "kafka_user": AsymmetricHandler.encrypt(
                        name=AsymmetricCipherConfigType.PASSWORD.value, content=conf.get("kafka_user", "")
                    ),
                    "kafka_pwd": AsymmetricHandler.encrypt(
                        name=AsymmetricCipherConfigType.PASSWORD.value, content=conf.get("kafka_pwd", "")
                    ),
                },
            )
            tbinlogdumper.save()
            # todo 关联tbinlogdumper订阅配置

    @transaction.atomic()
    def switch_tbinlogdumper_for_cluster(self, switch_ids: list):
        """
        切换TBinlogDumper实例的信息变更
        """
        master = self.cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
        for inst in ExtraProcessInstance.objects.filter(id__in=switch_ids):
            inst.bk_cloud_id = master.machine.bk_cloud_id
            inst.ip = master.machine.ip
            inst.extra_config["source_data_ip"] = master.machine.ip
            inst.extra_config["source_data_port"] = master.port
            inst.save()
