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
import copy
import logging.config
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import MYSQL8_VER_PARSE_NUM, DBType
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import InstanceStatus, MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import build_surrounding_apps_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.master_and_slave_switch import master_and_slave_switch_v2
from backend.flow.engine.bamboo.scene.mysql.mysql_migrate_cluster_remote_flow import MySQLMigrateClusterRemoteFlow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.mysql_version_parse import get_sub_version_by_pkg_name, mysql_version_parse

logger = logging.getLogger("flow")


def upgrade_version_check(origin_ver: str, new_ver: str):
    new_version_num = mysql_version_parse(new_ver)
    original_vernum = mysql_version_parse(origin_ver)
    if new_version_num >= MYSQL8_VER_PARSE_NUM:
        new_version_num = convert_mysql8_version_num(new_version_num)
    if new_version_num // 1000 - original_vernum // 1000 > 1:
        logger.error("upgrades across multiple major versions are not allowed")
        raise DBMetaException(message=_("不允许跨多个大版本升级"))
    if original_vernum >= new_version_num:
        logger.error(
            "the upgrade version {} needs to be larger than the current verion {}".format(
                new_version_num, original_vernum
            )
        )
        raise DBMetaException(message=_("当前集群MySQL升级版本大于等于新版本,请确认"))


def convert_mysql8_version_num(verno: int) -> int:
    # MySQL的发行版本号并不连续 MySQL 5.5 5.6 5.7 8.0
    # 为了方便比较将8.0 装换成 parse 之后的5.8的版本号来做比较
    return 5008 * 1000 + verno % 1000


# MySQLMigrateClusterRemoteFlow: 使用远程备份来恢复
# MySQLMigrateClusterFlow： 使用本地备份来恢复
class MySQMigrateUpgradeFlow(MySQLMigrateClusterRemoteFlow):
    """
    构建mysql主从成对迁移的方式来升级MySQL
    # new_non_standy_slave_ip_list:[
        {
            "old_slave": {"ip": "127.0.0.2", "bk_cloud_id": 0, "bk_host_id": 1, "bk_biz_id": 2005000002},
            "new_slave":  {"ip": "127.0.0.3", "bk_cloud_id": 0, "bk_host_id": 1, "bk_biz_id": 2005000003},
        },
        {
            "old_slave":  {"ip": "127.0.1.2", "bk_cloud_id": 0, "bk_host_id": 1, "bk_biz_id": 2005000004},
            "new_slave":   {"ip": "127.0.1.3", "bk_cloud_id": 0, "bk_host_id": 1, "bk_biz_id": 2005000005},
        }
        ]
    ]
    """

    def upgrade(self):
        # 进行模块的版本检查
        self.__pre_check()
        self.migrate_cluster_flow(use_for_upgrade=True)

    def __pre_check(self):
        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            cluster_class = Cluster.objects.get(id=self.data["cluster_ids"][0])

            origin_chaset, origin_mysql_ver = get_version_and_charset(
                self.ticket_data["bk_biz_id"],
                db_module_id=cluster_class.db_module_id,
                cluster_type=cluster_class.cluster_type,
            )

            new_charset, new_mysql_ver = get_version_and_charset(
                self.ticket_data["bk_biz_id"],
                db_module_id=info["new_db_module_id"],
                cluster_type=cluster_class.cluster_type,
            )
            # 判断是否存在一组多从的情况
            slave = cluster_class.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.SLAVE.value,
                is_stand_by=True,
                db_module_id=cluster_class.db_module_id,
            ).first()

            if slave is None:
                raise DBMetaException(message=_("查询集群{}stanb_by slave实例为None").format(cluster_class.immute_domain))

            mysql_storage_slave = cluster_class.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.SLAVE.value,
                status=InstanceStatus.RUNNING.value,
                is_stand_by=False,
            )
            for other_slave in mysql_storage_slave:
                if other_slave.db_module_id != info["new_db_module_id"]:
                    raise DBMetaException(message=_("请先升级{}stanb_by的其他slave实例").format(cluster_class.immute_domain))
            if new_charset != origin_chaset:
                raise DBMetaException(
                    message=_("{}升级前后字符集不一致,原字符集：{},新模块的字符集{}").format(
                        cluster_class.immute_domain, origin_chaset, new_charset
                    )
                )
            upgrade_version_check(origin_mysql_ver, new_mysql_ver)


class MySQLStorageLocalUpgradeFlow(object):
    """
    MySQL集群原地升级，先升级从库，在进行主从切换，在升级
    {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        infos:[
            {
                cluster_ids:[],
                cluster_type:"",
                new_mysql_version:"",
                new_db_module_id:""
            }
        ]
    }
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = ticket_data
        self.uid = ticket_data["uid"]
        self.upgrade_cluster_list = ticket_data["infos"]

    def __the_clusters_use_same_machine(self, cluster_ids: list):
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        instances = StorageInstance.objects.filter(
            cluster__in=clusters, machine_type__in=[MachineType.BACKEND, MachineType.SINGLE]
        )
        mach_ip_list = []
        for ins in instances:
            mach_ip_list.append(ins.machine.ip)
        # 根据主机再去查询关联的实例
        # relation_cluster_ids 是根据主机反查得到的关联的集群cluster_ids
        relation_cluster_ids = []
        for ip in mach_ip_list:
            mach_rela_instances = StorageInstance.objects.filter(machine__ip=ip)
            for ins in mach_rela_instances:
                relation_cluster = ins.cluster.get()
                relation_cluster_ids.append(relation_cluster.id)
        # 求差集
        diff_ids = set(cluster_ids) - set(relation_cluster_ids)
        if len(diff_ids) > 0:
            raise DBMetaException(message=_("当前集群,请确认"))
        diff_ids = set(relation_cluster_ids) - set(cluster_ids)
        if len(diff_ids) > 0:
            raise DBMetaException(message=_("必须把主机关联的集群都选上,请确认"))

    def __get_clusters_slave_instance(self, cluster_ids: list):
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        instances = StorageInstance.objects.filter(
            cluster__in=clusters,
            machine_type=MachineType.BACKEND,
            instance_role=InstanceRole.BACKEND_SLAVE,
            is_stand_by=True,
        )
        return instances

    def __get_clusters_master_instance(self, cluster_ids: list):
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        instances = StorageInstance.objects.filter(
            cluster__in=clusters, machine_type=MachineType.BACKEND, instance_role=InstanceRole.BACKEND_MASTER
        )
        return instances

    def __get_pkg_name_by_pkg_id(self, pkg_id: int) -> str:
        # 获取大版本的最新的包名
        mysql_pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
        return mysql_pkg.name

    def upgrade_mysql_flow(self):
        mysql_upgrade_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        cluster_ids = []
        reinstall_ip_list = []
        cluster_type = None
        bk_cloud_id = 0
        # 声明子流程
        for upgrade_info in self.upgrade_cluster_list:
            sub_flow_context = copy.deepcopy(self.data)
            cluster_ids = upgrade_info["cluster_ids"]
            pkg_id = upgrade_info["pkg_id"]
            new_mysql_pkg_name = self.__get_pkg_name_by_pkg_id(pkg_id)
            new_db_module_id = upgrade_info.get("new_db_module_id")
            logger.info("param pkg_id:{},get the pkg name: {}".format(pkg_id, new_mysql_pkg_name))
            # 确保这批集群的master都是一个主机
            self.__the_clusters_use_same_machine(cluster_ids)
            sub_pipeline = SubBuilder(
                root_id=self.root_id, data=copy.deepcopy(sub_flow_context), need_random_pass_cluster_ids=cluster_ids
            )
            first_cluster = Cluster.objects.filter(id__in=cluster_ids).first()
            if first_cluster:
                cluster_type = first_cluster.cluster_type
            bk_cloud_id = first_cluster.bk_cloud_id
            bk_biz_id = first_cluster.bk_biz_id
            # 高可用升级
            if cluster_type == ClusterType.TenDBHA:
                slave_instances = self.__get_clusters_slave_instance(cluster_ids)
                if len(slave_instances) <= 0:
                    raise DBMetaException(message=_("无法找到对应的从实例记录"))

                master_instances = self.__get_clusters_master_instance(cluster_ids)

                master_ip_list = []
                for master_instance in master_instances:
                    master_ip_list.append(master_instance.machine.ip)

                if len(set(master_ip_list)) != 1:
                    raise DBMetaException(message=_("集群的master应该同属于一个机器,当前分布在{}").format(list(set(master_ip_list))))

                master_ip = master_ip_list[0]
                reinstall_ip_list.append(master_ip)
                port_map = defaultdict(list)
                for slave_instance in slave_instances:
                    port_map[slave_instance.machine.ip].append(slave_instance.port)
                    upgrade_version_check(slave_instance.version, new_mysql_pkg_name)

                for slaveIp, ports in port_map.items():
                    sub_pipeline.add_sub_pipeline(
                        sub_flow=self.upgrade_mysql_subflow(
                            bk_cloud_id=bk_cloud_id,
                            ip=slaveIp,
                            mysql_ports=ports,
                            pkg_id=pkg_id,
                            mysql_pkg_name=new_mysql_pkg_name,
                        )
                    )

                # 切换子流程
                switch_sub_pipeline_list = []
                for cluster_id in cluster_ids:
                    switch_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                    cluster_model = Cluster.objects.get(id=cluster_id)
                    master_model = cluster_model.storageinstance_set.get(
                        instance_inner_role=InstanceInnerRole.MASTER.value
                    )

                    standby_slave = cluster_model.storageinstance_set.get(
                        instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
                    )

                    slave_ip = standby_slave.machine.ip

                    other_slave_storage = cluster_model.storageinstance_set.filter(
                        instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=False
                    )

                    other_slaves = [y.machine.ip for y in other_slave_storage]
                    cluster = {
                        "cluster_id": cluster_model.id,
                        "bk_cloud_id": cluster_model.bk_cloud_id,
                        "old_master_ip": master_ip,
                        "old_master_port": master_model.port,
                        "old_slave_ip": slave_ip,
                        "old_slave_port": standby_slave.port,
                        "new_master_ip": slave_ip,
                        "new_master_port": standby_slave.port,
                        "new_slave_ip": master_ip,
                        "new_slave_port": master_model.port,
                        "mysql_port": master_model.port,
                        "master_port": master_model.port,
                        "other_slave_info": other_slaves,
                    }
                    switch_sub_pipeline.add_sub_pipeline(
                        sub_flow=master_and_slave_switch_v2(
                            root_id=self.root_id,
                            ticket_data=copy.deepcopy(self.data),
                            cluster=cluster_model,
                            cluster_info=copy.deepcopy(cluster),
                        )
                    )
                    switch_sub_pipeline.add_act(
                        act_name=_("集群切换完成,写入 {} 的元信息".format(cluster_model.id)),
                        act_component_code=MySQLDBMetaComponent.code,
                        kwargs=asdict(
                            DBMetaOPKwargs(
                                db_meta_class_func=MySQLDBMeta.mysql_migrate_cluster_switch_storage.__name__,
                                cluster=cluster,
                                is_update_trans_data=True,
                            )
                        ),
                    )

                switch_sub_pipeline_list.append(
                    switch_sub_pipeline.build_sub_process(sub_name=_("集群 {} 切换".format(cluster_model.id)))
                )

                sub_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})
                sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_pipeline_list)

                # origin master 升级
                port_map = defaultdict(list)
                for instance in master_instances:
                    port_map[instance.machine.ip].append(instance.port)
                    upgrade_version_check(instance.version, new_mysql_pkg_name)

                for slaveIp, ports in port_map.items():
                    sub_pipeline.add_sub_pipeline(
                        sub_flow=self.upgrade_mysql_subflow(
                            bk_cloud_id=bk_cloud_id,
                            ip=slaveIp,
                            mysql_ports=ports,
                            pkg_id=pkg_id,
                            mysql_pkg_name=new_mysql_pkg_name,
                        )
                    )

                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[TendbHa]本地升级MySQL版本")))

            # tendbsingle 本地升级
            elif cluster_type == ClusterType.TenDBSingle:
                clusters = Cluster.objects.filter(id__in=cluster_ids)
                instances = StorageInstance.objects.filter(
                    cluster__in=clusters, machine_type=MachineType.SINGLE, instance_role=InstanceRole.ORPHAN
                )
                ip_list = []
                ports = []
                for instance in instances:
                    ports.append(instance.port)
                    ip_list.append(instance.machine.ip)
                    upgrade_version_check(instance.version, new_mysql_pkg_name)
                bk_cloud_id = clusters[0].bk_cloud_id
                if len(list(set(ip_list))) != 1:
                    raise DBMetaException(message=_("集群的master应该同属于一个机器,当前分布在{}").format(list(set(ip_list))))

                host_ip = ip_list[0]
                reinstall_ip_list.append(host_ip)
                sub_pipeline.add_sub_pipeline(
                    sub_flow=self.upgrade_mysql_subflow(
                        bk_cloud_id=bk_cloud_id,
                        ip=host_ip,
                        mysql_ports=ports,
                        mysql_pkg_name=new_mysql_pkg_name,
                        pkg_id=pkg_id,
                    )
                )
                # 更新集群模块信息
                if new_db_module_id > 0:
                    charset, major_version = get_version_and_charset(bk_biz_id, new_db_module_id, cluster_type)
                    sub_pipeline.add_act(
                        act_name=_("更新集群db模块信息"),
                        act_component_code=MySQLDBMetaComponent.code,
                        kwargs=asdict(
                            DBMetaOPKwargs(
                                db_meta_class_func=MySQLDBMeta.update_cluster_module.__name__,
                                cluster={
                                    "cluster_ids": cluster_ids,
                                    "new_module_id": new_db_module_id,
                                    "major_version": major_version,
                                },
                            )
                        ),
                    )
                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[TendbSingle]本地升级MySQL版本")))

            else:
                raise DBMetaException(message=_("不支持的集群类型"))

        mysql_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # 升级周边应用
        mysql_upgrade_pipeline.add_sub_pipeline(
            sub_flow=build_surrounding_apps_sub_flow(
                bk_cloud_id=int(bk_cloud_id),
                master_ip_list=reinstall_ip_list,
                root_id=self.root_id,
                parent_global_data=copy.deepcopy(sub_flow_context),
                is_init=True,
                collect_sysinfo=False,
                cluster_type=cluster_type,
            )
        )
        mysql_upgrade_pipeline.run_pipeline(is_drop_random_user=True)

        return

    def upgrade_mysql_subflow(
        self,
        ip: str,
        bk_cloud_id: int,
        pkg_id: int,
        mysql_pkg_name: str,
        mysql_ports: list = None,
    ):
        """
        定义upgrade mysql 的flow
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        sub_pipeline.add_act(
            act_name=_("下发升级的安装包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=ip,
                    file_list=GetFileList(db_type=DBType.MySQL).mysql_upgrade_package(pkg_id=pkg_id, db_version=""),
                )
            ),
        )
        cluster = {"run": False, "ports": mysql_ports, "pkg_id": pkg_id}
        exec_act_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=bk_cloud_id)
        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_upgrade_payload.__name__
        # 执行本地升级
        sub_pipeline.add_act(
            act_name=_("执行本地升级前置检查"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        cluster = {"run": True, "ports": mysql_ports, "pkg_id": pkg_id}
        exec_act_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=bk_cloud_id)
        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_upgrade_payload.__name__
        # 执行本地升级
        sub_pipeline.add_act(
            act_name=_("执行本地升级"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        # 更新mysql instance version 信息
        sub_pipeline.add_act(
            act_name=_("更新mysql instance version meta信息"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_mysql_instance_version.__name__,
                    cluster={"ip": ip, "version": get_sub_version_by_pkg_name(mysql_pkg_name)},
                )
            ),
        )
        return sub_pipeline.build_sub_process(sub_name=_("MySQL实例升级"))
