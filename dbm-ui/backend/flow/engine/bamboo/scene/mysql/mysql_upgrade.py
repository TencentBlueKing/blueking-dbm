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
import datetime
import logging.config
from collections import defaultdict
from dataclasses import asdict
from datetime import timedelta
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import MYSQL8_VER_PARSE_NUM, DBType
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.mysql_upgrade_subflow import (
    get_is_same_tmysql_version,
    mysql_cluster_upgrade_check_subflow,
    mysql_upgrade_subflow,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import (
    standardize_mysql_cluster_by_ip_subflow,
)
from backend.flow.engine.bamboo.scene.mysql.mysql_master_slave_switch import master_slave_mutual_switch_subflow
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLUpgradeContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.mysql_version_parse import (
    get_sub_version_by_pkg_name,
    mysql_version_parse,
    tmysql_version_parse,
)

logger = logging.getLogger("flow")


def upgrade_version_check(origin_ver: str, new_ver: str):
    new_version_num = mysql_version_parse(new_ver)
    original_version_num = mysql_version_parse(origin_ver)
    if new_version_num >= MYSQL8_VER_PARSE_NUM:
        new_version_num = convert_mysql8_version_num(new_version_num)
    if new_version_num // 1000 - original_version_num // 1000 > 1:
        logger.error("upgrades across multiple major versions are not allowed")
        raise DBMetaException(message=_("不允许跨多个大版本升级"))
    if original_version_num > new_version_num:
        logger.error(
            "the upgrade version {} needs to be larger than the current version {}".format(
                new_version_num, original_version_num
            )
        )
        raise DBMetaException(message=_("当前集群MySQL升级版本大于新版本,请确认"))
    elif original_version_num == new_version_num:
        new_tmysql_version = tmysql_version_parse(new_ver)
        origin_tmysql_version = tmysql_version_parse(origin_ver)
        if new_tmysql_version > origin_tmysql_version:
            logger.info("the tmysql version upgrade {} -> {}".format(origin_tmysql_version, new_tmysql_version))
        else:
            logger.error(
                "the tmysql version {} needs to be larger than the current tmysql version {}".format(
                    new_tmysql_version, origin_tmysql_version
                )
            )
            raise DBMetaException(message=_("当前集群MySQL升级版本大于新版本,请确认"))


def convert_mysql8_version_num(ver_num: int) -> int:
    # MySQL的发行版本号并不连续 MySQL 5.5 5.6 5.7 8.0
    # 为了方便比较将8.0 装换成 parse 之后的5.8的版本号来做比较
    return 5008 * 1000 + ver_num % 1000


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
        self.force_upgrade = ticket_data.get("force", False)

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
            # 这批集群是共同的机器，主从机器是一样的
            cluster_ids = upgrade_info["cluster_ids"]
            pkg_id = upgrade_info["pkg_id"]
            new_mysql_pkg_name = self.__get_pkg_name_by_pkg_id(pkg_id)
            new_db_module_id = upgrade_info.get("new_db_module_id")
            logger.info(_("参数pkg_id:{},获取包名: {}").format(pkg_id, new_mysql_pkg_name))

            is_same_tmysql_version = get_is_same_tmysql_version(cluster_ids[0], new_mysql_pkg_name)

            # 确保这批集群的master都是一个主机
            self.__the_clusters_use_same_machine(cluster_ids)
            sub_pipeline = SubBuilder(
                root_id=self.root_id, data=copy.deepcopy(sub_flow_context), need_random_pass_cluster_ids=cluster_ids
            )
            # 获取所有集群名称并拼接
            clusters_qs = Cluster.objects.filter(id__in=cluster_ids)
            cluster_names = "，".join([c.name for c in clusters_qs])
            logger.info(_("本次升级涉及集群: {}").format(cluster_names))
            # 获取集群基本信息
            first_cluster = Cluster.objects.filter(id__in=cluster_ids).first()
            if not first_cluster:
                raise DBMetaException(message=_("无法找到集群 {} 的信息").format(cluster_ids))
            cluster_type = first_cluster.cluster_type
            bk_cloud_id = first_cluster.bk_cloud_id
            bk_biz_id = first_cluster.bk_biz_id
            logger.info(_("开始处理集群类型: {}, 云区域: {}, 业务ID: {}").format(cluster_type, bk_cloud_id, bk_biz_id))

            # 下发介质包
            upgrade_ips = self._collect_upgrade_ips(cluster_ids, cluster_type)
            self._add_media_download_stage(sub_pipeline, list(set(upgrade_ips)), pkg_id, bk_cloud_id)
            # 添加告警屏蔽
            self._add_alarm_shield_act(sub_pipeline, cluster_ids)

            # 添加升级前置检查子流程 - 按集群维度并行检查
            clusters = Cluster.objects.filter(id__in=cluster_ids)
            check_sub_pipelines = []
            for cluster in clusters:
                # 收集当前集群的实例信息
                upgrade_instances = []
                storage_instances = StorageInstance.objects.filter(cluster=cluster)
                ip_port_map = {}
                for instance in storage_instances:
                    ip = instance.machine.ip
                    port = instance.port
                    if ip not in ip_port_map:
                        ip_port_map[ip] = []
                    ip_port_map[ip].append(port)

                # 转换为函数需要的格式
                for ip, ports in ip_port_map.items():
                    upgrade_instances.append({"ip": ip, "ports": ports})

                # 为每个集群创建检查子流程
                check_sub_flow = mysql_cluster_upgrade_check_subflow(
                    uid=self.uid,
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(sub_flow_context),
                    bk_cloud_id=bk_cloud_id,
                    upgrade_instances=upgrade_instances,
                    pkg_id=pkg_id,
                    sub_flow_name=_("MySQL集群[{}]升级检查").format(cluster.name),
                )
                if check_sub_flow:
                    check_sub_pipelines.append(check_sub_flow)
            # 并行执行所有集群的检查子流程
            sub_pipeline.add_parallel_sub_pipeline(check_sub_pipelines)

            # 按集群类型分别处理（跳过介质下发，因为已前置处理）
            if cluster_type == ClusterType.TenDBHA:
                self._handle_tendbha_upgrade(
                    sub_pipeline,
                    cluster_ids,
                    pkg_id,
                    new_mysql_pkg_name,
                    bk_cloud_id,
                    bk_biz_id,
                    reinstall_ip_list,
                    is_same_tmysql_version,
                )
            elif cluster_type == ClusterType.TenDBSingle:
                self._handle_tendbsingle_upgrade(
                    sub_pipeline,
                    cluster_ids,
                    pkg_id,
                    new_mysql_pkg_name,
                    bk_cloud_id,
                    bk_biz_id,
                    new_db_module_id,
                    reinstall_ip_list,
                    is_same_tmysql_version,
                    skip_media_download=True,
                )
            else:
                raise DBMetaException(message=_("不支持的集群类型: {}").format(cluster_type))

            # 解除告警屏蔽
            self._add_alarm_unshield_act(sub_pipeline)

            # 根据集群类型添加相应的子流程名称
            sub_flow_name = self._get_sub_flow_name(cluster_names)
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=sub_flow_name))

        mysql_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 标准化集群
        mysql_upgrade_pipeline.add_sub_pipeline(
            sub_flow=standardize_mysql_cluster_by_ip_subflow(
                root_id=self.root_id,
                data=copy.deepcopy(self.data),
                bk_cloud_id=int(bk_cloud_id),
                bk_biz_id=self.data["bk_biz_id"],
                ips=reinstall_ip_list,
                with_collect_sysinfo=False,
                with_actuator=False,
                with_bk_plugin=False,
            )
        )
        mysql_upgrade_pipeline.run_pipeline(init_trans_data_class=MySQLUpgradeContext(), is_drop_random_user=True)
        return

    def upgrade_mysql_subflow(
        self,
        ip: str,
        bk_cloud_id: int,
        pkg_id: int,
        mysql_pkg_name: str,
        mysql_role: str,
        mysql_ports: list = None,
        skip_send_pkg: bool = True,  # 默认跳过发包，因为已统一下发
        is_same_tmysql_version: bool = False,
    ):
        """
        定义upgrade mysql 的flow
        @param ip: 目标实例IP
        @param bk_cloud_id: 云区域ID
        @param pkg_id: 升级包ID
        @param mysql_pkg_name: MySQL包名
        @param mysql_ports: MySQL端口列表
        @param skip_send_pkg: 是否跳过发包（默认True，因为已统一下发）
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        sub_pipeline.add_sub_pipeline(
            sub_flow=mysql_upgrade_subflow(
                uid=self.data.get("uid"),
                root_id=self.root_id,
                parent_global_data=copy.deepcopy(self.data),
                bk_cloud_id=bk_cloud_id,
                ip=ip,
                mysql_ports=mysql_ports,
                pkg_id=pkg_id,
                sub_flow_name=_("MySQL升级[{}]").format(ip),
                skip_send_pkg=skip_send_pkg,  # 使用参数控制是否跳过发包
                is_same_tmysql_version=is_same_tmysql_version,
            )
        )
        # 更新mysql instance version 信息
        sub_pipeline.add_act(
            act_name=_("更新mysql instance version meta信息 {}").format(ip),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_mysql_instance_version.__name__,
                    cluster={"ip": ip, "version": get_sub_version_by_pkg_name(mysql_pkg_name)},
                )
            ),
        )
        return sub_pipeline.build_sub_process(sub_name=_("MySQL{}实例升级[{}]").format(mysql_role, ip))

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

    def __get_clusters_slave_instance(self, cluster_ids: list, is_stand_by: bool):
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        instances = StorageInstance.objects.filter(
            cluster__in=clusters,
            machine_type=MachineType.BACKEND,
            instance_role=InstanceRole.BACKEND_SLAVE,
            is_stand_by=is_stand_by,
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

    def _get_sub_flow_name(self, multi_cluster_names):
        """根据集群类型返回子流程名称"""
        return _("{}:原地升级").format(multi_cluster_names)

    def _collect_upgrade_ips(self, cluster_ids, cluster_type):
        """收集指定集群需要升级的主机IP"""
        upgrade_ips = set()

        if cluster_type == ClusterType.TenDBHA:
            # TenDBHA: 收集master、slave、standby实例的IP
            ro_slave_instances = self.__get_clusters_slave_instance(cluster_ids, False)
            master_instances = self.__get_clusters_master_instance(cluster_ids)
            stand_by_instances = self.__get_clusters_slave_instance(cluster_ids, is_stand_by=True)

            # 收集master IP
            if master_instances:
                master_ip = self._validate_and_get_master_ip(master_instances)
                upgrade_ips.add(master_ip)

            # 收集slave IP
            for slave_instance in ro_slave_instances:
                upgrade_ips.add(slave_instance.machine.ip)

            # 收集standby IP
            for standby_instance in stand_by_instances:
                upgrade_ips.add(standby_instance.machine.ip)

        elif cluster_type == ClusterType.TenDBSingle:
            # TenDBSingle: 收集所有实例的IP
            clusters = Cluster.objects.filter(id__in=cluster_ids)
            instances = StorageInstance.objects.filter(
                cluster__in=clusters, machine_type=MachineType.SINGLE, instance_role=InstanceRole.ORPHAN
            )
            for instance in instances:
                upgrade_ips.add(instance.machine.ip)

        return upgrade_ips

    def _handle_tendbha_upgrade(
        self,
        sub_pipeline,
        cluster_ids,
        pkg_id,
        new_mysql_pkg_name,
        bk_cloud_id,
        bk_biz_id,
        reinstall_ip_list,
        is_same_tmysql_version,
    ):
        """处理TenDBHA集群升级"""
        # 获取slave和master实例
        ro_slave_instances = self.__get_clusters_slave_instance(cluster_ids, False)
        master_instances = self.__get_clusters_master_instance(cluster_ids)
        stand_by_instances = self.__get_clusters_slave_instance(cluster_ids, is_stand_by=True)
        # 验证master实例都在同一台机器
        master_ip = self._validate_and_get_master_ip(master_instances)
        stand_by_slave_ip = self._validate_and_get_standby_ip(stand_by_instances)
        reinstall_ip_list.append(master_ip)
        reinstall_ip_list.append(stand_by_slave_ip)
        if ro_slave_instances:
            self._upgrade_slave_instances(
                sub_pipeline,
                ro_slave_instances,
                pkg_id,
                new_mysql_pkg_name,
                bk_cloud_id,
                is_same_tmysql_version,
                "ro_slave",
            )
        # 阶段2: 升级slave实例
        self._upgrade_slave_instances(
            sub_pipeline,
            stand_by_instances,
            pkg_id,
            new_mysql_pkg_name,
            bk_cloud_id,
            is_same_tmysql_version,
            "standby_slave",
        )
        # 阶段3: 主从切换
        self._add_master_slave_switch(sub_pipeline, cluster_ids, master_ip, stand_by_slave_ip, bk_biz_id)
        # 人工确认升级原master实例
        # 阶段4: 升级原master实例（现在是slave）
        sub_pipeline.add_act(act_name=_("人工确认升级原master实例"), act_component_code=PauseComponent.code, kwargs={})
        self._upgrade_master_instances(
            sub_pipeline, master_instances, pkg_id, new_mysql_pkg_name, bk_cloud_id, is_same_tmysql_version
        )

    def _handle_tendbsingle_upgrade(
        self,
        sub_pipeline,
        cluster_ids,
        pkg_id,
        new_mysql_pkg_name,
        bk_cloud_id,
        bk_biz_id,
        new_db_module_id,
        reinstall_ip_list,
        is_same_tmysql_version,
        skip_media_download=False,
    ):
        """处理TenDBSingle集群升级"""
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        instances = StorageInstance.objects.filter(
            cluster__in=clusters, machine_type=MachineType.SINGLE, instance_role=InstanceRole.ORPHAN
        )
        # 收集实例信息
        ip_list = []
        ports = []
        for instance in instances:
            ports.append(instance.port)
            ip_list.append(instance.machine.ip)
            # 移除版本检查，因为已在前置检查中完成
            # upgrade_version_check(instance.version, new_mysql_pkg_name)
        # 验证所有实例在同一台机器
        unique_ips = list(set(ip_list))
        if len(unique_ips) != 1:
            raise DBMetaException(message=_("集群的实例应该同属于一个机器,当前分布在{}").format(unique_ips))
        host_ip = unique_ips[0]
        reinstall_ip_list.append(host_ip)

        # 下发介质包（如果未跳过）
        if not skip_media_download:
            self._add_media_download_stage(sub_pipeline, [host_ip], pkg_id, bk_cloud_id)
        # 升级实例
        sub_pipeline.add_sub_pipeline(
            sub_flow=self.upgrade_mysql_subflow(
                bk_cloud_id=bk_cloud_id,
                ip=host_ip,
                mysql_ports=ports,
                mysql_role="orphan",
                mysql_pkg_name=new_mysql_pkg_name,
                pkg_id=pkg_id,
                is_same_tmysql_version=is_same_tmysql_version,
            )
        )
        # 更新集群模块信息
        if new_db_module_id and new_db_module_id > 0:
            self._update_cluster_module_info(
                sub_pipeline, cluster_ids, new_db_module_id, bk_biz_id, clusters[0].cluster_type
            )

    def _validate_and_get_master_ip(self, master_instances):
        """验证master实例并返回IP"""
        master_ip_list = [instance.machine.ip for instance in master_instances]
        unique_master_ips = list(set(master_ip_list))
        if len(unique_master_ips) != 1:
            raise DBMetaException(message=_("集群的master应该同属于一个机器,当前分布在{}").format(unique_master_ips))
        return unique_master_ips[0]

    def _validate_and_get_standby_ip(self, standby_slave_instances):
        """验证standby slave实例并返回IP"""
        master_ip_list = [instance.machine.ip for instance in standby_slave_instances]
        unique_slave_ips = list(set(master_ip_list))
        if len(unique_slave_ips) != 1:
            raise DBMetaException(message=_("集群的standby slave应该同属于一个机器,当前分布在{}").format(unique_slave_ips))
        return unique_slave_ips[0]

    def _add_media_download_stage(self, sub_pipeline, ip_list, pkg_id, bk_cloud_id):
        """添加介质下发阶段"""
        if ip_list:
            sub_pipeline.add_act(
                act_name=_("下发MySQL升级包到主机"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip_list,
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_upgrade_package(
                            pkg_id=pkg_id, db_version=""
                        ),
                    )
                ),
            )

    def _upgrade_slave_instances(
        self, sub_pipeline, slave_instances, pkg_id, new_mysql_pkg_name, bk_cloud_id, is_same_tmysql_version, role
    ):
        """升级slave实例"""
        port_map = defaultdict(list)
        for slave_instance in slave_instances:
            port_map[slave_instance.machine.ip].append(slave_instance.port)
            # 移除版本检查，因为已在前置检查中完成
            # upgrade_version_check(slave_instance.version, new_mysql_pkg_name)
        for slave_ip, ports in port_map.items():
            sub_pipeline.add_sub_pipeline(
                sub_flow=self.upgrade_mysql_subflow(
                    bk_cloud_id=bk_cloud_id,
                    ip=slave_ip,
                    mysql_ports=ports,
                    pkg_id=pkg_id,
                    mysql_role=role,
                    mysql_pkg_name=new_mysql_pkg_name,
                    skip_send_pkg=True,
                    is_same_tmysql_version=is_same_tmysql_version,
                )
            )

    def _upgrade_master_instances(
        self, sub_pipeline, master_instances, pkg_id, new_mysql_pkg_name, bk_cloud_id, is_same_tmysql_version
    ):
        """升级master实例（切换后的slave）"""
        port_map = defaultdict(list)
        for instance in master_instances:
            port_map[instance.machine.ip].append(instance.port)
            # 移除版本检查，因为已在前置检查中完成
            # upgrade_version_check(instance.version, new_mysql_pkg_name)
        for master_ip, ports in port_map.items():
            sub_pipeline.add_sub_pipeline(
                sub_flow=self.upgrade_mysql_subflow(
                    bk_cloud_id=bk_cloud_id,
                    ip=master_ip,
                    mysql_role="master",
                    mysql_ports=ports,
                    pkg_id=pkg_id,
                    mysql_pkg_name=new_mysql_pkg_name,
                    skip_send_pkg=True,
                    is_same_tmysql_version=is_same_tmysql_version,
                )
            )

    def _add_master_slave_switch(self, sub_pipeline, cluster_ids, master_ip, slave_ip, bk_biz_id):
        """添加主从切换逻辑"""
        sub_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})
        sub_pipeline.add_sub_pipeline(
            sub_flow=master_slave_mutual_switch_subflow(
                uid=self.uid,
                root_id=self.root_id,
                context_data=copy.deepcopy(self.data),
                bk_biz_id=bk_biz_id,
                cluster_ids=cluster_ids,
                master_ip=master_ip,
                slave_ip=slave_ip,
                is_verify_checksum=False,
                check_client_conn=self.force_upgrade,
            )
        )

    def _update_cluster_module_info(self, sub_pipeline, cluster_ids, new_db_module_id, bk_biz_id, cluster_type):
        """更新集群模块信息"""
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

    def _add_alarm_shield_act(self, sub_pipeline, cluster_ids):
        """添加告警屏蔽活动"""
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        # 获取集群的所有实例IP
        instance_ips = []
        cluster_names = []

        for cluster in clusters:
            cluster_names.append(cluster.name)
            # 获取所有存储实例IP
            storage_instances = StorageInstance.objects.filter(cluster=cluster)
            for instance in storage_instances:
                instance_ips.append(instance.machine.ip)

        # 去重
        instance_ips = list(set(instance_ips))
        cluster_names_str = ", ".join(cluster_names)

        if instance_ips:
            sub_pipeline.add_act(
                act_name=_("屏蔽集群 {} 告警4小时").format(cluster_names_str),
                act_component_code=AddAlarmShieldComponent.code,
                kwargs={
                    "begin_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": (datetime.datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
                    "description": _("集群 {} MySQL升级操作").format(cluster_names_str),
                    "dimensions": [
                        {
                            "name": "instance_host",
                            "values": instance_ips,
                        }
                    ],
                },
            )
            logger.info(_("为集群 {} 添加告警屏蔽，影响主机: {}").format(cluster_names_str, instance_ips))

    def _add_alarm_unshield_act(self, sub_pipeline):
        """添加解除告警屏蔽活动"""
        sub_pipeline.add_act(act_name=_("解除告警屏蔽"), act_component_code=DisableAlarmShieldComponent.code, kwargs={})
        logger.info(_("添加解除告警屏蔽活动"))
