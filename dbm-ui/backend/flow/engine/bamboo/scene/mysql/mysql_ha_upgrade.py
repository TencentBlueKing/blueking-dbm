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
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Optional

from django.utils import timezone
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import MediumEnum, MysqlVersionToDBBackupForMap
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.cluster_entrys import get_tendb_ha_entry
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_surrounding_apps_sub_flow,
    install_mysql_in_cluster_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_instance_config
from backend.flow.engine.bamboo.scene.mysql.common.master_and_slave_switch import master_and_slave_switch_v2
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import (
    mysql_restore_data_sub_flow,
    mysql_restore_master_slave_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.common.recover_slave_instance import slave_recover_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.slave_recover_switch import slave_migrate_switch_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.uninstall_instance import uninstall_instance_sub_flow
from backend.flow.engine.bamboo.scene.mysql.mysql_upgrade import upgrade_version_check
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBackupInfoFailedException
from backend.flow.engine.bamboo.scene.spider.spider_remote_node_migrate import remote_instance_migrate_sub_flow
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_ports, get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import (
    ClearMachineKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse
from backend.ticket.builders.common.constants import MySQLBackupSource

logger = logging.getLogger("flow")


class DestroyNonStanbySlaveMySQLFlow(object):
    """
    下架非standby slave MySQL实例的流程
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param tick_data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.ticket_data = ticket_data
        if not self.ticket_data.get("force"):
            self.ticket_data["force"] = False

    def destroy(self):
        """
        {
            "uid": "2022051612120001",
            "created_by": "xxxx",
            "bk_biz_id": "152",
            "ticket_type": "MYSQL_RESTORE_SLAVE",
            "infos": {
                    "cluster_ids": [1001,1002],
                    "slave_ip": "1.1.1.1",
            }
        }
        """
        cluster_ids = self.ticket_data["infos"]["cluster_ids"]
        slave_ip = self.ticket_data["infos"]["slave_ip"]
        cluster_class = Cluster.objects.get(id=cluster_ids[0])
        ports = get_ports(cluster_ids)
        slave_ins_list = StorageInstance.objects.filter(machine__ip=slave_ip)

        for slave_ins in slave_ins_list:
            if slave_ins.is_stand_by:
                raise DBMetaException(message=_("{}:{}实例是standby slave,请确认").format(slave_ip, slave_ins.port))

        p = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )

        p.add_act(
            act_name=_("卸载实例前先删除元数据"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.ro_slave_recover_del_instance.__name__,
                    cluster={"uninstall_ip": slave_ip, "cluster_ids": cluster_ids},
                )
            ),
        )

        p.add_act(
            act_name=_("下发db-actor到节点{}").format(slave_ip),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    exec_ip=slave_ip,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        p.add_act(
            act_name=_("清理机器配置"),
            act_component_code=MySQLClearMachineComponent.code,
            kwargs=asdict(
                ClearMachineKwargs(
                    exec_ip=slave_ip,
                    bk_cloud_id=cluster_class.bk_cloud_id,
                )
            ),
        )

        p.add_sub_pipeline(
            sub_flow=uninstall_instance_sub_flow(
                root_id=self.root_id,
                ticket_data=copy.deepcopy(self.ticket_data),
                ip=slave_ip,
                ports=ports,
            )
        )
        p.run_pipeline(is_drop_random_user=False)


class TendbClusterUpgradeFlow(object):
    """
    一主多从非stand by slaves升级
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param ticket_data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.ticket_data = ticket_data
        #  仅添加从库。不切换。不复制账号
        self.add_slave_only = self.ticket_data.get("add_slave_only", False)
        self.check_client_conn = not self.ticket_data.get("force", False)

    def __precheck(self):
        """
        升级前置检查
        """
        for info in self.ticket_data["infos"]:
            cluster_class = Cluster.objects.get(id=info["cluster_ids"][0])
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
            if new_charset != origin_chaset:
                raise DBMetaException(
                    message=_("{}升级前后字符集不一致,原字符集：{},新模块的字符集{}").format(
                        cluster_class.immute_domain, origin_chaset, new_charset
                    )
                )
            upgrade_version_check(origin_mysql_ver, new_mysql_ver)

    def upgrade_ro_slaves(self):
        self.__precheck()
        cluster_ids = []
        for info in self.ticket_data["infos"]:
            cluster_ids.extend(info["cluster_ids"])

        p = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        subflows = []
        created_by = self.ticket_data["ticket_type"]
        for info in self.ticket_data["infos"]:
            subflow = non_standby_slaves_upgrade_subflow(
                uid=str(self.ticket_data["uid"]),
                root_id=self.root_id,
                new_slave=info["new_slave"],
                old_slave=info["old_slave"],
                add_slave_only=self.add_slave_only,
                relation_cluster_ids=info["cluster_ids"],
                pkg_id=info["pkg_id"],
                new_db_module_id=info["new_db_module_id"],
                backup_source=self.ticket_data["backup_source"],
                created_by=created_by,
                force_uninstall=False,
            )
            subflows.append(subflow)

        p.add_parallel_sub_pipeline(subflows)

        p.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)

    def upgrade_tendbha_cluster(self):
        """
        {
            "uid": "2022051612120001",
            "created_by": "xxxx",
            "bk_biz_id": "152",
            "ticket_type": "MYSQL_RESTORE_SLAVE",
            "backup_source": "local",
            "infos": [
                {
                    "cluster_ids": [1001,1002],
                    "pkg_id": 123,
                    "new_db_module_id: "578",
                    "new_slave": {
                        "ip": "1.1.2.1",
                        "bk_biz_id": 200005000,
                        "bk_host_id": 1,
                        "bk_cloud_id": 0
                    },
                    "new_master": {
                        "ip": "1.1.3.1",
                        "bk_biz_id": 200005000,
                        "bk_host_id": 1,
                        "bk_cloud_id": 0
                    },
                    ro_slaves:[
                        {
                            "old_slave": {
                                "bk_biz_id": 200005000,
                                "bk_cloud_id": 0,
                                "bk_host_id": 1,
                                "ip": "1.1.1.1",

                            },
                            "new_slave": {
                                "bk_biz_id": 200005000,
                                "bk_cloud_id": 0,
                                "bk_host_id": 1,
                                "ip": "1.1.1.2"
                            }
                        }
                    ]
                }
            ]
        }
        """
        self.__precheck()
        cluster_ids = []
        for info in self.ticket_data["infos"]:
            cluster_ids.extend(info["cluster_ids"])

        p = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        subflows = []
        created_by = self.ticket_data["created_by"]
        for info in self.ticket_data["infos"]:
            subflow = tendbha_cluster_upgrade_subflow(
                uid=str(self.ticket_data["uid"]),
                root_id=self.root_id,
                new_master=info["new_master"],
                new_slave=info["new_slave"],
                ro_slaves=info["ro_slaves"],
                cluster_ids=info["cluster_ids"],
                pkg_id=info["pkg_id"],
                new_db_module_id=info["new_db_module_id"],
                backup_source=self.ticket_data["backup_source"],
                created_by=created_by,
                force_uninstall=False,
                ticket_type=self.ticket_data["ticket_type"],
                check_client_conn=self.check_client_conn,
            )
            subflows.append(subflow)

        p.add_parallel_sub_pipeline(subflows)

        p.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)


def tendbha_cluster_upgrade_subflow(
    uid: str,
    root_id: str,
    new_slave: dict,
    new_master: dict,
    ro_slaves: list,
    cluster_ids: list,
    pkg_id: int,
    new_db_module_id: int,
    backup_source: str,
    created_by: str,
    force_uninstall: bool,
    ticket_type: str,
    check_client_conn: bool,
):
    """
    一主多从，整个集群升级
    """
    cluster_cls = Cluster.objects.get(id=cluster_ids[0])
    ports = get_ports(cluster_ids)
    pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
    charset, db_version = get_version_and_charset(
        cluster_cls.bk_biz_id, db_module_id=new_db_module_id, cluster_type=cluster_cls.cluster_type
    )
    # 确定要迁移的主节点，从节点.
    master_model = cluster_cls.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
    slave = cluster_cls.storageinstance_set.filter(
        instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
    ).first()
    old_master_ip = master_model.machine.ip
    old_slave_ip = slave.machine.ip
    parent_global_data = {
        "uid": uid,
        "root_id": root_id,
        "bk_biz_id": cluster_cls.bk_biz_id,
        "bk_cloud_id": cluster_cls.bk_cloud_id,
        "db_module_id": new_db_module_id,
        "time_zone": cluster_cls.time_zone,
        "cluster_type": cluster_cls.cluster_type,
        "created_by": created_by,
        "cluster_ids": cluster_ids,
        "package": pkg.name,
        "master_ip": old_master_ip,
        "old_slave_ip": old_slave_ip,
        "ports": ports,
        "charset": charset,
        "db_version": db_version,
        "force": force_uninstall,
        "ticket_type": ticket_type,
    }
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)
    old_ro_slave_ips = []
    new_ro_slave_ips = []

    local_backup = False
    if backup_source == MySQLBackupSource.LOCAL:
        local_backup = True

    if len(ro_slaves) > 0:
        ro_sub_piplelines = []
        ro_switch_ro_sub_piplelines = []
        for ro_slave in ro_slaves:
            ro_sub_pipleline = SubBuilder(root_id=root_id, data=parent_global_data)
            old_ro_slave = ro_slave["old_ro_slave"]
            new_ro_slave = ro_slave["new_ro_slave"]
            new_ro_slave_ip = new_ro_slave["ip"]
            new_ro_slave_ips.append(new_ro_slave_ip)
            bk_host_ids = [new_slave["bk_host_id"]]
            old_ro_slave_ip = old_ro_slave["ip"]
            old_ro_slave_ips.append(old_ro_slave_ip)
            origin_config = get_instance_config(cluster_cls.bk_cloud_id, old_ro_slave_ip, ports=ports)
            db_config = deal_mycnf(pkg.name, db_version, origin_config)
            install_ro_slave_sub_pipeline = build_install_slave_sub_pipeline(
                uid,
                root_id,
                parent_global_data,
                cluster_cls,
                new_ro_slave_ip,
                ports,
                bk_host_ids,
                db_config,
                pkg_id,
                pkg.name,
                cluster_ids,
                new_db_module_id,
            )
            ro_sub_pipleline.add_sub_pipeline(sub_flow=install_ro_slave_sub_pipeline)
            # 恢复主从数据
            sync_data_sub_pipeline_list = build_sync_data_sub_pipelines(
                root_id, parent_global_data, cluster_ids, new_ro_slave_ip, local_backup, charset
            )
            ro_sub_pipleline.add_parallel_sub_pipeline(sync_data_sub_pipeline_list)
            ro_sub_piplelines.append(ro_sub_pipleline.build_sub_process(sub_name=_("安装非stanbySlave节点并数据同步")))
            # 切换换subpipeline
            ro_switch_ro_sub_pipleline = SubBuilder(root_id=root_id, data=parent_global_data)
            switch_sub_pipeline_list = build_switch_sub_pipelines(
                root_id, parent_global_data, cluster_ids, old_ro_slave_ip, new_ro_slave_ip
            )
            ro_switch_ro_sub_pipleline.add_parallel_sub_pipeline(switch_sub_pipeline_list)
            ro_switch_ro_sub_pipleline.add_act(
                act_name=_("更新[NewSlave]{} db module id".format(new_ro_slave_ip)),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_upgrade_slaves_dbmodule.__name__,
                        is_update_trans_data=True,
                        cluster={
                            "db_module_id": new_db_module_id,
                            "new_slave_ip": new_ro_slave_ip,
                        },
                    )
                ),
            )
            ro_switch_ro_sub_piplelines.append(ro_switch_ro_sub_pipleline.build_sub_process(sub_name=_("切换RO从节点")))
    # 安装mysql
    ms_sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)
    bk_host_ids = [new_master["bk_host_id"], new_slave["bk_host_id"]]
    master = cluster_cls.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
    origin_config = get_instance_config(cluster_cls.bk_cloud_id, master.machine.ip, ports)
    db_config = deal_mycnf(pkg.name, db_version, origin_config)
    install_ms_pair_subflow = build_install_ms_pair_sub_pipeline(
        uid=uid,
        root_id=root_id,
        parent_global_data=parent_global_data,
        cluster=cluster_cls,
        new_master_ip=new_master["ip"],
        new_slave_ip=new_slave["ip"],
        ports=ports,
        bk_host_ids=bk_host_ids,
        pkg_id=pkg.id,
        db_config=db_config,
        db_module_id=new_db_module_id,
    )
    ms_sub_pipeline.add_sub_pipeline(sub_flow=install_ms_pair_subflow)
    new_master_ip = new_master["ip"]
    new_slave_ip = new_slave["ip"]
    # 同步数据
    sync_data_sub_pipeline_list = build_ms_pair_sync_data_sub_pipelines(
        root_id=root_id,
        parent_global_data=parent_global_data,
        relation_cluster_ids=cluster_ids,
        new_master_ip=new_master_ip,
        new_slave_ip=new_slave_ip,
        old_slave_ip=old_slave_ip,
        local_backup=local_backup,
        charset=charset,
    )
    ms_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
    ms_process = ms_sub_pipeline.build_sub_process(sub_name=_("安装主从节点,并同步数据"))
    if len(ro_slaves) > 0:
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=[ms_process] + ro_sub_piplelines)
    else:
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=[ms_process])
    sub_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})
    # 先切ro slaves
    if len(ro_slaves) > 0:
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=ro_switch_ro_sub_piplelines)
    logger.info(_("old_ro_slave ip list {}").format(old_ro_slave_ips))
    # 切换主从对
    ms_switch_subflows = build_ms_pair_switch_sub_pipelines(
        root_id=root_id,
        parent_global_data=parent_global_data,
        relation_cluster_ids=cluster_ids,
        old_master_ip=old_master_ip,
        old_slave_ip=old_slave_ip,
        new_master_ip=new_master_ip,
        new_slave_ip=new_slave_ip,
        old_ro_slave_ips=old_ro_slave_ips,
        new_ro_slave_ips=new_ro_slave_ips,
        check_client_conn=check_client_conn,
    )
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=ms_switch_subflows)
    # 清理实例级别周边配置
    uninstall_surrounding_sub_pipeline = build_uninstall_surrounding_sub_pipeline(
        root_id=root_id,
        parent_global_data=parent_global_data,
        uninstall_ip_list=[old_master_ip, old_slave_ip],
        relation_cluster_ids=cluster_ids,
        ports=ports,
        bk_cloud_id=cluster_cls.bk_cloud_id,
    )
    sub_pipeline.add_sub_pipeline(sub_flow=uninstall_surrounding_sub_pipeline)
    # 更新集群模块信息
    sub_pipeline.add_act(
        act_name=_("更新集群db模块信息"),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.update_cluster_module.__name__,
                cluster={
                    "cluster_ids": cluster_ids,
                    "new_module_id": new_db_module_id,
                    "major_version": db_version,
                },
            )
        ),
    )
    # 重新安装备份,监控等
    sub_pipeline.add_sub_pipeline(
        sub_flow=build_surrounding_apps_sub_flow(
            bk_cloud_id=cluster_cls.bk_cloud_id,
            master_ip_list=[new_master_ip],
            slave_ip_list=new_ro_slave_ips + [new_slave_ip],
            root_id=root_id,
            parent_global_data=copy.deepcopy(parent_global_data),
            collect_sysinfo=True,
            is_init=True,
            is_install_backup=True,
            is_install_monitor=True,
            is_install_rotate_binlog=True,
            is_install_checksum=True,
            cluster_type=ClusterType.TenDBHA.value,
            db_backup_pkg_type=MysqlVersionToDBBackupForMap[db_version],
        )
    )
    # 下架确认节点
    sub_pipeline.add_act(act_name=_("人工确认下架旧节点"), act_component_code=PauseComponent.code, kwargs={})
    # 下架被替换的机器
    uninstall_flows = []
    uninstall_ip_list = [old_master_ip, old_slave_ip] + old_ro_slave_ips
    for uninstall_ip in uninstall_ip_list:
        uninstall_flows.append(
            build_uninstall_old_machine_sub_pipeline(
                root_id=root_id,
                parent_global_data=parent_global_data,
                uninstall_ip=uninstall_ip,
                relation_cluster_ids=cluster_ids,
                bk_cloud_id=cluster_cls.bk_cloud_id,
                ports=ports,
            )
        )
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_flows)
    return sub_pipeline.build_sub_process(sub_name=_("{}:整体迁移升级").format(cluster_cls.immute_domain))


def deal_mycnf(pkg_name, db_version: str, db_config: dict):
    if mysql_version_parse(db_version) >= mysql_version_parse("5.7.0"):
        will_del_keys = ["slave_parallel_type", "replica_parallel_type"]
        # 如果不是tmysql的话，需要删除一些配置
        if "tmysql" not in pkg_name:
            will_del_keys.append("log_bin_compress")
            will_del_keys.append("relay_log_uncompress")
        for port in db_config:
            for key in will_del_keys:
                if db_config[port].get(key):
                    del db_config[port][key]
    if mysql_version_parse(db_version) >= mysql_version_parse("8.0.0"):
        will_del_keys = ["innodb_large_prefix"]
        for port in db_config:
            for key in will_del_keys:
                if db_config[port].get(key):
                    del db_config[port][key]
    return db_config


def non_standby_slaves_upgrade_subflow(
    uid: str,
    root_id: str,
    new_slave: dict,
    old_slave: dict,
    add_slave_only: bool,
    relation_cluster_ids: list,
    pkg_id: int,
    new_db_module_id: int,
    backup_source: str,
    created_by: str,
    force_uninstall: bool,
):
    """
    一主多从非stanby slaves升级subflow
    """
    cluster_cls = Cluster.objects.get(id=relation_cluster_ids[0])
    ports = get_ports(relation_cluster_ids)
    pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
    charset, db_version = get_version_and_charset(
        cluster_cls.bk_biz_id, db_module_id=new_db_module_id, cluster_type=cluster_cls.cluster_type
    )
    parent_global_data = {
        "uid": uid,
        "root_id": root_id,
        "bk_biz_id": cluster_cls.bk_biz_id,
        "bk_cloud_id": cluster_cls.bk_cloud_id,
        "db_module_id": new_db_module_id,
        "time_zone": cluster_cls.time_zone,
        "cluster_type": cluster_cls.cluster_type,
        "created_by": created_by,
        "package": pkg.name,
        "ports": ports,
        "charset": charset,
        "db_version": db_version,
        "force": force_uninstall,
    }

    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)
    new_slave_ip = new_slave["ip"]
    bk_host_ids = [new_slave["bk_host_id"]]
    old_slave_ip = old_slave["ip"]
    db_config = get_instance_config(cluster_cls.bk_cloud_id, old_slave_ip, ports=ports)

    # 安装mysql
    install_sub_pipeline = build_install_slave_sub_pipeline(
        uid,
        root_id,
        parent_global_data,
        cluster_cls,
        new_slave_ip,
        ports,
        bk_host_ids,
        db_config,
        pkg_id,
        pkg.name,
        relation_cluster_ids,
        new_db_module_id,
    )
    sub_pipeline.add_sub_pipeline(sub_flow=install_sub_pipeline)

    # 恢复主从数据
    local_backup = False
    if backup_source == MySQLBackupSource.LOCAL:
        local_backup = True
    sync_data_sub_pipeline_list = build_sync_data_sub_pipelines(
        root_id, parent_global_data, relation_cluster_ids, new_slave_ip, local_backup, charset
    )
    sub_pipeline.add_parallel_sub_pipeline(sync_data_sub_pipeline_list)

    # 切换到新从节点
    if not add_slave_only:
        switch_sub_pipeline_list = build_switch_sub_pipelines(
            root_id, parent_global_data, relation_cluster_ids, old_slave_ip, new_slave_ip
        )
        sub_pipeline.add_parallel_sub_pipeline(switch_sub_pipeline_list)
    # 更新新的从节点db module id
    sub_pipeline.add_act(
        act_name=_("更新[NewSlave]{} db module id".format(new_slave_ip)),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.update_upgrade_slaves_dbmodule.__name__,
                is_update_trans_data=True,
                cluster={
                    "db_module_id": new_db_module_id,
                    "new_slave_ip": new_slave_ip,
                },
            )
        ),
    )
    # 解除old从节点和集群的元数据的关系
    sub_pipeline.add_act(
        act_name=_("解除[OldSlave]{}相关从实例和集群的元数据的关系".format(old_slave_ip)),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.dissolve_master_slave_relationship.__name__,
                is_update_trans_data=True,
                cluster={
                    "cluster_ids": relation_cluster_ids,
                    "old_slave_ip": old_slave_ip,
                },
            )
        ),
    )

    # 切换完成后，确认卸载旧的从节点
    sub_pipeline.add_act(act_name=_("确认卸载旧实例"), act_component_code=PauseComponent.code, kwargs={})
    # 卸载旧从节点
    uninstall_svr_sub_pipeline = build_uninstall_old_machine_sub_pipeline(
        root_id, parent_global_data, old_slave_ip, relation_cluster_ids, cluster_cls.bk_cloud_id, ports
    )
    sub_pipeline.add_sub_pipeline(sub_flow=uninstall_svr_sub_pipeline)

    return sub_pipeline.build_sub_process(sub_name=_("{}:slave迁移升级到:{}").format(old_slave_ip, new_slave_ip))


def build_install_slave_sub_pipeline(
    uid,
    root_id,
    parent_global_data,
    cluster,
    new_slave_ip,
    ports,
    bk_host_ids,
    db_config,
    pkg_id,
    pkg_name,
    relation_cluster_ids,
    db_module_id,
):
    install_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(parent_global_data))

    install_sub_pipeline.add_sub_pipeline(
        sub_flow=install_mysql_in_cluster_sub_flow(
            uid=uid,
            root_id=root_id,
            cluster=cluster,
            new_mysql_list=[new_slave_ip],
            install_ports=ports,
            bk_host_ids=bk_host_ids,
            pkg_id=pkg_id,
            db_config=db_config,
            db_module_id=str(db_module_id),
        )
    )

    cluster_info = {
        "install_ip": new_slave_ip,
        "cluster_ids": relation_cluster_ids,
        "package": pkg_name,
    }

    install_sub_pipeline.add_act(
        act_name=_("写入初始化实例的db_meta元信息"),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.slave_recover_add_instance.__name__,
                cluster=copy.deepcopy(cluster_info),
                is_update_trans_data=False,
            )
        ),
    )

    install_sub_pipeline.add_act(
        act_name=_("安装backup-client工具"),
        act_component_code=DownloadBackupClientComponent.code,
        kwargs=asdict(
            DownloadBackupClientKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                bk_biz_id=int(cluster.bk_biz_id),
                download_host_list=[new_slave_ip],
            )
        ),
    )

    exec_act_kwargs = ExecActuatorKwargs(
        cluster=cluster_info,
        bk_cloud_id=cluster.bk_cloud_id,
        cluster_type=cluster.cluster_type,
        get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
        exec_ip=[new_slave_ip],
    )
    install_sub_pipeline.add_act(
        act_name=_("安装临时备份程序"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    return install_sub_pipeline.build_sub_process(sub_name=_("{}:安装MySQL实例").format(new_slave_ip))


def build_sync_data_sub_pipelines(
    root_id, parent_global_data, relation_cluster_ids, new_slave_ip, local_backup: bool, charset: str
):
    """build 数据同步 sub pipeline

    Args:
        root_id (_type_): _description_
        parent_global_data (_type_): _description_
        relation_cluster_ids (_type_): _description_
        new_slave_ip (_type_): _description_
        local_backup (bool): _description_
        charset (str): _description_

    Returns:
        _type_: _description_
    """
    sync_data_sub_pipeline_list = []
    for cluster_id in relation_cluster_ids:
        cluster_model = Cluster.objects.get(id=cluster_id)
        master = cluster_model.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        cluster = {
            "mysql_port": master.port,
            "cluster_id": cluster_model.id,
            "cluster_type": cluster_model.cluster_type,
            "master_ip": master.machine.ip,
            "master_port": master.port,
            "new_slave_ip": new_slave_ip,
            "new_slave_port": master.port,
            "bk_cloud_id": cluster_model.bk_cloud_id,
            "file_target_path": f"/data/dbbak/{root_id}/{master.port}",
            "charset": charset,
            "change_master_force": True,
            "change_master": True,
        }
        sync_data_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(parent_global_data))
        if local_backup:
            # 获取本地备份并恢复
            inst_list = ["{}{}{}".format(master.machine.ip, IP_PORT_DIVIDER, master.port)]
            stand_by_slaves = cluster_model.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.SLAVE.value,
                is_stand_by=True,
                status=InstanceStatus.RUNNING.value,
            ).exclude(machine__ip__in=[new_slave_ip])
            if len(stand_by_slaves) > 0:
                inst_list.append(
                    "{}{}{}".format(stand_by_slaves[0].machine.ip, IP_PORT_DIVIDER, stand_by_slaves[0].port)
                )
            sync_data_sub_pipeline.add_sub_pipeline(
                sub_flow=mysql_restore_data_sub_flow(
                    root_id=root_id,
                    ticket_data=copy.deepcopy(parent_global_data),
                    cluster=cluster,
                    cluster_model=cluster_model,
                    ins_list=inst_list,
                )
            )
        else:
            sync_data_sub_pipeline.add_sub_pipeline(
                sub_flow=slave_recover_sub_flow(
                    root_id=root_id, ticket_data=copy.deepcopy(parent_global_data), cluster_info=cluster
                )
            )

        sync_data_sub_pipeline.add_act(
            act_name=_("同步完毕,写入主从关系,设置节点为running状态"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.mysql_add_slave_info.__name__,
                    cluster=cluster,
                    is_update_trans_data=True,
                )
            ),
        )
        sync_data_sub_pipeline_list.append(
            sync_data_sub_pipeline.build_sub_process(sub_name=_("{}:恢复实例数据").format(cluster_model.immute_domain))
        )
    return sync_data_sub_pipeline_list


def build_switch_sub_pipelines(root_id, parent_global_data, relation_cluster_ids, old_slave_ip, new_slave_ip):
    """构建ro slaves 切换的sub pipeline

    Args:
        root_id (_type_): _description_
        parent_global_data (_type_): _description_
        relation_cluster_ids (_type_): _description_
        old_slave_ip (_type_): _description_
        new_slave_ip (_type_): _description_

    Returns:
        _type_: _description_
    """
    switch_sub_pipeline_list = []
    for cluster_id in relation_cluster_ids:
        cluster_model = Cluster.objects.get(id=cluster_id)
        switch_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(parent_global_data))
        switch_sub_pipeline.add_sub_pipeline(
            sub_flow=slave_migrate_switch_sub_flow(
                root_id=root_id,
                ticket_data=copy.deepcopy(parent_global_data),
                cluster=cluster_model,
                old_slave_ip=old_slave_ip,
                new_slave_ip=new_slave_ip,
            )
        )
        domain_map = get_tendb_ha_entry(cluster_model.id)
        cluster_info = {
            "slave_domain": domain_map[old_slave_ip],
            "new_slave_ip": new_slave_ip,
            "old_slave_ip": old_slave_ip,
            "cluster_id": cluster_model.id,
        }
        switch_sub_pipeline.add_act(
            act_name=_("slave切换完毕,修改集群 {} 数据").format(cluster_model.immute_domain),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.mysql_restore_slave_change_cluster_info.__name__,
                    cluster=cluster_info,
                    is_update_trans_data=True,
                )
            ),
        )
        switch_sub_pipeline_list.append(
            switch_sub_pipeline.build_sub_process(sub_name=_("切换到新从节点:{}").format(new_slave_ip))
        )
    return switch_sub_pipeline_list


def build_uninstall_old_machine_sub_pipeline(
    root_id, parent_global_data, uninstall_ip, relation_cluster_ids, bk_cloud_id, ports
):
    """构建下架旧节点的sub pipeline

    Args:
        root_id (_type_): _description_
        parent_global_data (_type_): _description_
        uninstall_ip (_type_): _description_
        relation_cluster_ids (_type_): _description_
        bk_cloud_id (_type_): _description_
        ports (_type_): _description_

    Returns:
        _type_: _description_
    """
    uninstall_svr_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(parent_global_data))
    cluster_info = {"uninstall_ip": uninstall_ip, "cluster_ids": relation_cluster_ids}

    uninstall_svr_sub_pipeline.add_act(
        act_name=_("卸载实例前先删除元数据"),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.del_cluster_old_machine_meta.__name__,
                is_update_trans_data=True,
                cluster=cluster_info,
            )
        ),
    )

    uninstall_svr_sub_pipeline.add_act(
        act_name=_("下发db-actor到节点{}").format(uninstall_ip),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=uninstall_ip,
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )

    uninstall_svr_sub_pipeline.add_act(
        act_name=_("清理机器配置"),
        act_component_code=MySQLClearMachineComponent.code,
        kwargs=asdict(
            ClearMachineKwargs(
                exec_ip=uninstall_ip,
                bk_cloud_id=bk_cloud_id,
            )
        ),
    )

    uninstall_svr_sub_pipeline.add_sub_pipeline(
        sub_flow=uninstall_instance_sub_flow(
            root_id=root_id,
            ticket_data=copy.deepcopy(parent_global_data),
            ip=uninstall_ip,
            ports=ports,
        )
    )

    return uninstall_svr_sub_pipeline.build_sub_process(sub_name=_("卸载remote节点{}").format(uninstall_ip))


def build_install_ms_pair_sub_pipeline(
    uid,
    root_id,
    parent_global_data,
    cluster,
    new_master_ip,
    new_slave_ip,
    ports,
    bk_host_ids,
    db_config,
    pkg_id,
    db_module_id,
):
    install_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(parent_global_data))

    install_sub_pipeline.add_sub_pipeline(
        sub_flow=install_mysql_in_cluster_sub_flow(
            uid=uid,
            root_id=root_id,
            cluster=cluster,
            new_mysql_list=[new_master_ip, new_slave_ip],
            install_ports=ports,
            bk_host_ids=bk_host_ids,
            pkg_id=pkg_id,
            db_config=db_config,
            db_module_id=str(db_module_id),
        )
    )

    cluster_info = {
        "cluster_ports": ports,
        "new_master_ip": new_master_ip,
        "new_slave_ip": new_slave_ip,
        "bk_cloud_id": cluster.bk_cloud_id,
    }

    install_sub_pipeline.add_act(
        act_name=_("写入初始化实例的db_meta元信息"),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.migrate_cluster_add_instance.__name__,
                cluster=copy.deepcopy(cluster_info),
                is_update_trans_data=True,
            )
        ),
    )

    install_sub_pipeline.add_act(
        act_name=_("安装backup-client工具"),
        act_component_code=DownloadBackupClientComponent.code,
        kwargs=asdict(
            DownloadBackupClientKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                bk_biz_id=int(cluster.bk_biz_id),
                download_host_list=[new_master_ip, new_slave_ip],
            )
        ),
    )

    exec_act_kwargs = ExecActuatorKwargs(
        cluster=cluster_info,
        bk_cloud_id=cluster.bk_cloud_id,
        cluster_type=cluster.cluster_type,
        get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
        exec_ip=[new_master_ip, new_slave_ip],
    )
    install_sub_pipeline.add_act(
        act_name=_("安装临时备份程序"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    return install_sub_pipeline.build_sub_process(sub_name=_("安装MySQL主从实例"))


def build_ms_pair_sync_data_sub_pipelines(
    root_id,
    parent_global_data,
    relation_cluster_ids,
    new_master_ip,
    new_slave_ip,
    old_slave_ip,
    local_backup: bool,
    charset: str,
):
    sync_data_sub_pipeline_list = []
    for cluster_id in relation_cluster_ids:
        cluster_model = Cluster.objects.get(id=cluster_id)
        master_model = cluster_model.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        rollback_time = datetime.now(timezone.utc)
        rollback_handler = FixPointRollbackHandler(cluster_id=cluster_model.id)
        backup_info = rollback_handler.query_latest_backup_log(rollback_time)
        if backup_info is None:
            logger.error("cluster {} backup info not exists".format(cluster_model.id))
            raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(cluster_id)))
        cluster = {
            "backupinfo": backup_info,
            "new_master_ip": new_master_ip,
            "new_slave_ip": new_slave_ip,
            "new_master_port": master_model.port,
            "new_slave_port": master_model.port,
            "cluster_type": cluster_model.cluster_type,
            "master_ip": master_model.machine.ip,
            "slave_ip": old_slave_ip,
            "master_port": master_model.port,
            "slave_port": master_model.port,
            "mysql_port": master_model.port,
            "file_target_path": f"/data/dbbak/{root_id}/{master_model.port}",
            "cluster_id": cluster_model.id,
            "bk_cloud_id": cluster_model.bk_cloud_id,
            "charset": charset,
            "change_master_force": True,
            "change_master": True,
        }
        sync_data_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(parent_global_data))
        if local_backup:
            stand_by_slaves = cluster_model.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.SLAVE.value,
                is_stand_by=True,
                status=InstanceStatus.RUNNING.value,
            ).exclude(machine__ip__in=[new_master_ip, new_slave_ip])
            #     从standby从库找备份
            inst_list = ["{}{}{}".format(master_model.machine.ip, IP_PORT_DIVIDER, master_model.port)]
            if len(stand_by_slaves) > 0:
                inst_list.append(
                    "{}{}{}".format(stand_by_slaves[0].machine.ip, IP_PORT_DIVIDER, stand_by_slaves[0].port)
                )
            sync_data_sub_pipeline.add_sub_pipeline(
                sub_flow=mysql_restore_master_slave_sub_flow(
                    root_id=root_id,
                    ticket_data=copy.deepcopy(parent_global_data),
                    cluster=cluster,
                    cluster_model=cluster_model,
                    ins_list=inst_list,
                )
            )
        else:
            sync_data_sub_pipeline.add_sub_pipeline(
                sub_flow=remote_instance_migrate_sub_flow(
                    root_id=root_id, ticket_data=copy.deepcopy(parent_global_data), cluster_info=cluster
                )
            )
        sync_data_sub_pipeline.add_act(
            act_name=_("同步完毕,写入主从关系,设置节点为running状态"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.migrate_cluster_add_tuple.__name__,
                    cluster=cluster,
                    is_update_trans_data=True,
                )
            ),
        )
        sync_data_sub_pipeline_list.append(
            sync_data_sub_pipeline.build_sub_process(sub_name=_("{}:恢复实例数据").format(cluster_model.immute_domain))
        )
    return sync_data_sub_pipeline_list


def build_ms_pair_switch_sub_pipelines(
    root_id: str,
    parent_global_data: dict,
    relation_cluster_ids: list,
    old_master_ip: str,
    old_slave_ip: str,
    new_master_ip: str,
    new_slave_ip: str,
    old_ro_slave_ips: list,
    new_ro_slave_ips: list,
    check_client_conn: bool,
):
    switch_sub_pipeline_list = []
    for cluster_id in relation_cluster_ids:
        switch_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(parent_global_data))
        cluster_model = Cluster.objects.get(id=cluster_id)
        master_model = cluster_model.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        cluster_info = {
            "cluster_id": cluster_model.id,
            "bk_cloud_id": cluster_model.bk_cloud_id,
            "old_master_ip": old_master_ip,
            "old_master_port": master_model.port,
            "old_slave_ip": old_slave_ip,
            "old_slave_port": master_model.port,
            "new_master_ip": new_master_ip,
            "new_master_port": master_model.port,
            "new_slave_ip": new_slave_ip,
            "new_slave_port": master_model.port,
            "mysql_port": master_model.port,
            "master_port": master_model.port,
            "old_ro_slave_ips": old_ro_slave_ips,
            "new_ro_slave_ips": new_ro_slave_ips,
        }
        switch_sub_pipeline.add_sub_pipeline(
            sub_flow=master_and_slave_switch_v2(
                root_id=root_id,
                ticket_data=copy.deepcopy(parent_global_data),
                cluster=cluster_model,
                cluster_info=copy.deepcopy(cluster_info),
                check_client_conn=check_client_conn,
            )
        )
        switch_sub_pipeline.add_act(
            act_name=_("集群切换完成,写入 {} 的元信息".format(cluster_model.name)),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.mysql_migrate_cluster_switch_storage.__name__,
                    cluster=cluster_info,
                    is_update_trans_data=True,
                )
            ),
        )
        switch_sub_pipeline_list.append(
            switch_sub_pipeline.build_sub_process(
                sub_name=_("集群切换到新主从节点:new-master:{},new-slave:{}").format(new_master_ip, new_slave_ip)
            )
        )
    return switch_sub_pipeline_list


def build_uninstall_surrounding_sub_pipeline(
    root_id, parent_global_data, uninstall_ip_list, relation_cluster_ids, bk_cloud_id, ports
):
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(parent_global_data))

    sub_pipeline.add_act(
        act_name=_("下发db-actor到节点{}".format(uninstall_ip_list)),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=uninstall_ip_list,
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )
    acts = []
    for ip in uninstall_ip_list:
        context = {"uninstall_ip": ip, "remote_port": ports, "backend_port": ports, "bk_cloud_id": bk_cloud_id}
        act = {
            "act_name": _("清理{}的实例级别周边配置".format(ip)),
            "act_component_code": ExecuteDBActuatorScriptComponent.code,
            "kwargs": asdict(
                ExecActuatorKwargs(
                    exec_ip=ip,
                    cluster_type=ClusterType.TenDBHA,
                    bk_cloud_id=bk_cloud_id,
                    cluster=context,
                    get_mysql_payload_func=MysqlActPayload.get_clear_surrounding_config_payload.__name__,
                )
            ),
        }
        acts.append(act)

    sub_pipeline.add_parallel_acts(
        acts_list=acts,
    )
    return sub_pipeline.build_sub_process(sub_name=_("清理实例级别周边配置"))
