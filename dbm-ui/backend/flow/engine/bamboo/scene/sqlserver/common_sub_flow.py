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
from dataclasses import asdict
from pathlib import PureWindowsPath
from typing import Dict, List, Optional

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import (
    DBM_SQLSERVER_JOB_LONG_TIMEOUT,
    WINDOW_ADMIN_USER_FOR_CHECK,
    SqlserverBackupFileTagEnum,
    SqlserverBackupJobExecMode,
    SqlserverBackupMode,
    SqlserverCleanMode,
    SqlserverRestoreMode,
    SqlserverSyncMode,
    SqlserverSyncModeMaps,
    SqlserverVersion,
)
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.common.install_plugins import install_nodeman_plugins
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.common.sa_udns_add import UdnsAddInMachineComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.sqlserver.backup_path_file_trans import (
    SqlserverTransBackupFileFor2P2Component,
)
from backend.flow.plugins.components.collections.sqlserver.check_no_sync_db import CheckNoSyncDBComponent
from backend.flow.plugins.components.collections.sqlserver.clone_linkserver import CloneLinkServerComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.exec_sqlserver_backup_job import (
    ExecSqlserverBackupJobComponent,
)
from backend.flow.plugins.components.collections.sqlserver.init_dbm_nginx_proxy import (
    InitDBMNginxForSQLServerComponent,
)
from backend.flow.plugins.components.collections.sqlserver.insert_app_setting import InsertAppSettingComponent
from backend.flow.plugins.components.collections.sqlserver.restore_for_do_dr import RestoreForDoDrComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_download_backup_file import (
    SqlserverDownloadBackupFileComponent,
)
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.plugins.components.collections.sqlserver.update_window_gse_config import (
    UpdateWindowGseConfigComponent,
)
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs, InitCheckKwargs
from backend.flow.utils.mysql.mysql_act_dataclass import UpdateDnsRecordKwargs
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    DownloadBackupFileKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    ExecBackupJobsKwargs,
    InsertAppSettingKwargs,
    P2PFileForWindowKwargs,
    RestoreForDoDrKwargs,
    SqlserverBackupIDContext,
    UpdateWindowGseConfigKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_bk_config import get_sqlserver_backup_config
from backend.flow.utils.sqlserver.sqlserver_db_function import get_backup_path
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.validate import SqlserverCluster, SqlserverInstance


def init_machine_sub_flow(uid: str, bk_biz_id: int, bk_cloud_id: int, root_id: str, target_hosts: list):
    # 构造只读上下文
    global_data = {
        "uid": uid,
        "bk_biz_id": bk_biz_id,
        "bk_cloud_id": bk_cloud_id,
    }
    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 空闲检查
    if env.SA_CHECK_TEMPLATE_ID:
        sub_pipeline.add_act(
            act_name=_("空闲检查"),
            act_component_code=CheckMachineIdleComponent.code,
            kwargs=asdict(
                InitCheckKwargs(
                    ips=[host.ip for host in target_hosts],
                    bk_cloud_id=bk_cloud_id,
                    account_name=WINDOW_ADMIN_USER_FOR_CHECK,
                )
            ),
        )

    # 强制添加udns解析
    if env.UPDATE_WINDOW_UDNS_CONFIG:
        sub_pipeline.add_act(
            act_name=_("更新机器的udns配置"),
            act_component_code=UdnsAddInMachineComponent.code,
            kwargs=asdict(
                UdnsAddInMachineComponent.kwargs(
                    ips=[host.ip for host in target_hosts],
                    bk_cloud_id=bk_cloud_id,
                    account_name=WINDOW_ADMIN_USER_FOR_CHECK,
                    template_id=env.UPDATE_WINDOW_UDNS_CONFIG,
                )
            ),
        )

    # 更新window机器的gse配置信息
    if env.UPDATE_WINDOW_GSE_CONFIG:
        sub_pipeline.add_act(
            act_name=_("更新gse配置信息"),
            act_component_code=UpdateWindowGseConfigComponent.code,
            kwargs=asdict(
                UpdateWindowGseConfigKwargs(
                    ips=[host.ip for host in target_hosts],
                    bk_cloud_id=bk_cloud_id,
                )
            ),
        )

    # 安装蓝鲸插件
    bk_host_ids = [t.bk_host_id for t in target_hosts]
    sub_pipeline.add_sub_pipeline(install_nodeman_plugins(root_id, uid, bk_host_ids))

    return sub_pipeline.build_sub_process(sub_name=_("初始化机器"))


def install_sqlserver_sub_flow(
    uid: str,
    root_id: str,
    bk_biz_id: int,
    bk_cloud_id: int,
    db_module_id: int,
    install_ports: list,
    clusters: List[SqlserverCluster],
    cluster_type: ClusterType,
    target_hosts: List[Host],
    db_version: SqlserverVersion,
):
    """
    拼接安装Sqlserver的子流程，以机器维度安装
    @param uid: 单据id
    @param root_id: 主流程的id
    @param bk_biz_id: 对应的业务id
    @param bk_cloud_id: 云区域ID
    @param db_module_id: 对应的db模块id
    @param install_ports: 机器部署的端口列表，多实例场景
    @param clusters: 机器部署所关联的集群列表，多实例场景
    @param cluster_type: 集群类型
    @param target_hosts: 部署新机器列表
    @param db_version: 部署版本
    """
    # 预防性检测
    is_err = False
    err_messages = ""
    for host in target_hosts:
        if not host.bk_host_id:
            is_err = True
            err_messages += _("流程中安装机器【{}】没有存入bk_host_id,请联系系统管理员\n".format(host.ip))
    if is_err:
        raise Exception(err_messages)

    # 构造只读上下文
    global_data = {
        "uid": uid,
        "bk_biz_id": bk_biz_id,
        "bk_cloud_id": bk_cloud_id,
        "db_module_id": db_module_id,
        "install_ports": install_ports,
        "clusters": [asdict(i) for i in clusters],
        "cluster_type": cluster_type,
    }
    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 下发安装包
    sub_pipeline.add_act(
        act_name=_("下发安装包介质"),
        act_component_code=TransFileInWindowsComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                target_hosts=target_hosts,
                file_list=GetFileList(db_type=DBType.Sqlserver).get_sqlserver_package(db_version=db_version),
            ),
        ),
    )
    # 机器初始化
    sub_pipeline.add_act(
        act_name=_("机器初始化"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=target_hosts, get_payload_func=SqlserverActPayload.system_init_payload.__name__
            ),
        ),
    )
    # 安装机器维度安装实例
    acts_list = []
    for hosts in target_hosts:
        acts_list.append(
            {
                "act_name": _("安装Sqlserver实例:{}".format(hosts.ip)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[hosts], get_payload_func=SqlserverActPayload.get_install_sqlserver_payload.__name__
                    ),
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 安装机器维度初始化实例
    acts_list = []
    for hosts in target_hosts:
        acts_list.append(
            {
                "act_name": _("初始化Sqlserver实例:{}".format(hosts.ip)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[hosts], get_payload_func=SqlserverActPayload.get_init_sqlserver_payload.__name__
                    ),
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("安装sqlserver实例"))


def switch_domain_sub_flow_for_cluster(
    uid: str,
    root_id: str,
    cluster: Cluster,
    # old_master: StorageInstance,
    # new_master: StorageInstance,
    old_master_host: Host,
    old_master_port: int,
    old_master_dns_list: List[ClusterEntry],
    new_master_host: Host,
    new_master_port: int,
    new_master_dns_list: List[ClusterEntry],
    is_force: bool = False,
):
    """
    主从切换后做域名切换处理
    @param uid: 单据id
    @param root_id: 主流程的id
    @param old_master_host: 集群原主实例
    @param old_master_port: 集群新主实例
    @param old_master_dns_list: 原主实例当前的域名列表
    @param new_master_host: 集群新主实例
    @param new_master_port: 集群新主实例
    @param new_master_dns_list: 新主实例当前的域名列表
    @param cluster: 集群元信息
    @param is_force: 是否属于强切行为，默认不是，强切行为认为主故障，从域名不切换到旧主上
    """
    # 构造只读上下文
    global_data = {"uid": uid, "bk_biz_id": cluster.bk_biz_id}

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 替换主域名映射
    acts_list = []
    for old_master_dns in old_master_dns_list:
        acts_list.append(
            {
                "act_name": _("[{}]替换主域名映射".format(old_master_dns.entry)),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    UpdateDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        old_instance=f"{old_master_host.ip}#{old_master_port}",
                        new_instance=f"{new_master_host.ip}#{new_master_port}",
                        update_domain_name=old_master_dns.entry,
                    ),
                ),
            }
        )
    # 并发替换从域名映射
    if not is_force:
        for slave_dns in new_master_dns_list:
            acts_list.append(
                {
                    "act_name": _("[{}]替换从域名映射".format(slave_dns.entry)),
                    "act_component_code": MySQLDnsManageComponent.code,
                    "kwargs": asdict(
                        UpdateDnsRecordKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            old_instance=f"{new_master_host.ip}#{new_master_port}",
                            new_instance=f"{old_master_host.ip}#{old_master_port}",
                            update_domain_name=slave_dns.entry,
                        ),
                    ),
                }
            )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("变更集群[{}]域名映射".format(cluster.name)))


def migrate_domain_for_cluster_ha(
    uid: str,
    root_id: str,
    cluster: Cluster,
    old_master: StorageInstance,
    old_stand_by: StorageInstance,
    new_master_host: Host,
    new_stand_by_host: Host,
):
    """
    主从切换后做域名切换处理
    @param uid: 单据id
    @param root_id: 主流程的id
    @param old_master: 集群原主实例
    @param old_stand_by: 集群原备实例
    @param new_master_host: 集群新主机器
    @param new_stand_by_host: 集群新备机器
    @param cluster: 集群id
    """
    # 构造只读上下文
    global_data = {"uid": uid, "bk_biz_id": cluster.bk_biz_id}

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 替换主域名映射
    acts_list = []
    old_master_dns_list = old_master.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
    for old_master_dns in old_master_dns_list:
        acts_list.append(
            {
                "act_name": _("[{}]替换主域名映射".format(old_master_dns.entry)),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    UpdateDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        old_instance=f"{old_master.machine.ip}#{old_master.port}",
                        new_instance=f"{new_master_host.ip}#{old_master.port}",
                        update_domain_name=old_master_dns.entry,
                    ),
                ),
            }
        )
    # 并发替换从域名映射
    slave_dns_list = old_stand_by.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
    for slave_dns in slave_dns_list:
        acts_list.append(
            {
                "act_name": _("[{}]替换从域名映射".format(slave_dns.entry)),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    UpdateDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        old_instance=f"{old_stand_by.machine.ip}#{old_stand_by.port}",
                        new_instance=f"{new_stand_by_host.ip}#{old_stand_by.port}",
                        update_domain_name=slave_dns.entry,
                    ),
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("变更集群[{}]域名映射".format(cluster.immute_domain)))


def migrate_domain_for_cluster_single(
    uid: str,
    root_id: str,
    cluster: Cluster,
    old_instance: StorageInstance,
    new_host: Host,
):
    """
    定义单节点集群迁移，做域名切换的子流程
    @param uid: 单据ID
    @param root_id: 主流程的id
    @param cluster: 集群元数据
    @param old_instance: 原来的实例
    @param new_host: 待替换新的机器信息
    """
    # 构造只读上下文
    global_data = {"uid": uid, "bk_biz_id": cluster.bk_biz_id}

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 替换主域名映射
    acts_list = []
    dns_list = old_instance.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
    for dns_info in dns_list:
        acts_list.append(
            {
                "act_name": _("[{}]替换主域名映射".format(dns_info.entry)),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    UpdateDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        old_instance=f"{old_instance.machine.ip}#{old_instance.port}",
                        new_instance=f"{new_host.ip}#{old_instance.port}",
                        update_domain_name=dns_info.entry,
                    ),
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("变更集群[{}]域名映射".format(cluster.name)))


def pre_check_sub_flow(
    uid: str,
    root_id: str,
    cluster_id: int,
    check_host: Host,
    check_port: int,
    is_check_abnormal_db: bool = True,
    is_check_inst_process: bool = True,
    is_check_sync_db: bool = True,
):
    """
    实例切换前的预检查
    @param uid: 单据id
    @param root_id: 主流程的id
    @param cluster_id: 集群id
    @param check_host: 需要检查的实例对象
    @param check_port: 需要检查的port
    @param is_check_abnormal_db: 是否检查异常数据库
    @param is_check_inst_process: 是否检查业务连接存在
    @param is_check_sync_db: 是否检查未同步的数据库
    """
    # 构造只读上下文
    global_data = {"uid": uid, "port": check_port}

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 并发检测异常状态DB
    acts_list = []
    if is_check_sync_db:
        acts_list.append(
            {
                "act_name": _("检查实例{}:{}是否存在没有同步的数据库".format(check_host.ip, check_port)),
                "act_component_code": CheckNoSyncDBComponent.code,
                "kwargs": {"cluster_id": cluster_id},
            }
        )

    if is_check_abnormal_db:
        acts_list.append(
            {
                "act_name": _("检查实例{}:{}是否有异常状态DB".format(check_host.ip, check_port)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[check_host],
                        get_payload_func=SqlserverActPayload.get_check_abnormal_db_payload.__name__,
                    )
                ),
            }
        )
    # 并发检测是否有业务链接
    if is_check_inst_process:
        acts_list.append(
            {
                "act_name": _("检查实例{}:{}是否有业务链接".format(check_host.ip, check_port)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[check_host],
                        get_payload_func=SqlserverActPayload.get_check_inst_process_payload.__name__,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("预检测"))


def clone_configs_sub_flow(
    uid: str,
    root_id: str,
    bk_biz_id: int,
    source_host: Host,
    source_port: int,
    target_host: Host,
    target_port: int,
    is_clone_user: bool = True,
    is_clone_jobs: bool = True,
    is_clone_linkserver: bool = True,
    is_clone_backup_filter: bool = True,
    is_clone_mirroring_filter: bool = True,
    sub_flow_name: str = _("克隆实例周边配置"),
):
    """
    实例之间克隆子流程
    @param uid: 单据id
    @param root_id: 主流程的id
    @param bk_biz_id: 业务id，用于 CloneLinkServer 组件从 DBM 授权中心按业务隔离查询密码
    @param source_host: 源实例
    @param source_port: 源实例端口
    @param target_host: 目标实例
    @param target_port: 目标实例端口
    @param is_clone_user: 是否选择克隆实例用户权限
    @param is_clone_jobs: 是否选择克隆实例的作业
    @param is_clone_linkserver: 是否选择克隆实例的linkserver配置
    @param is_clone_backup_filter: 是否选择克隆实例backup_filter配置
    @param is_clone_mirroring_filter: 是否选择克隆实例mirroring_filter配置
    @param sub_flow_name: 子流程名称
    """
    if not is_clone_user and not is_clone_jobs and not is_clone_linkserver:
        raise Exception("is_clone_user, is_clone_jobs and is_clone_linkserver is False, check")

    # 构造只读上下文
    global_data = {
        "uid": uid,
        "port": target_port,
        "source_host": source_host.ip,
        "source_port": source_port,
    }
    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)
    acts_list = []
    # 并发克隆Users
    if is_clone_user:
        acts_list.append(
            {
                "act_name": _("克隆Users"),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_user_payload.__name__,
                    )
                ),
            }
        )
    # 并发克隆LinkServer
    if is_clone_linkserver:
        acts_list.append(
            {
                "act_name": _("克隆LinkServer"),
                "act_component_code": CloneLinkServerComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_linkserver_payload.__name__,
                        component_kwargs={
                            "bk_biz_id": bk_biz_id,
                            "target_port": target_port,
                            "source_host": source_host.ip,
                            "source_port": source_port,
                            "bk_cloud_id": target_host.bk_cloud_id,
                        },
                    )
                ),
            }
        )
    # 并发克隆Jobs
    if is_clone_jobs:
        acts_list.append(
            {
                "act_name": _("克隆Jobs"),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_jobs_payload.__name__,
                    )
                ),
            }
        )

    # 并发克隆backup_filter
    if is_clone_backup_filter:
        acts_list.append(
            {
                "act_name": _("克隆备份忽略表"),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_backup_filter_payload.__name__,
                    )
                ),
            }
        )

    # 并发克隆mirroring_filter
    if is_clone_mirroring_filter:
        acts_list.append(
            {
                "act_name": _("克隆同步忽略表"),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[target_host],
                        get_payload_func=SqlserverActPayload.get_clone_mirroring_filter_payload.__name__,
                    )
                ),
            }
        )

    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=sub_flow_name)


def sync_dbs_for_cluster_sub_flow(
    uid: str,
    root_id: str,
    cluster: Cluster,
    master_host: Host,
    sync_slaves: List[Host],
    port: int,
    sync_dbs: list,
    clean_dbs: list = None,
    sub_flow_name: str = _("建立数据库同步子流程"),
    is_recalc_sync_dbs: bool = False,
    is_recalc_clean_dbs: bool = False,
    sync_mode: SqlserverSyncMode = None,
):
    """
    数据库建立同步的子流程
    @param uid: 单据id
    @param root_id: 主流程的id
    @param cluster: 关联的集群对象
    @param sync_slaves: 待同步的从实例
    @param sync_dbs: 待同步的db列表
    @param clean_dbs: 这次清理的db列表，默认为空，则用sync_dbs列表作为清理db
    @param sub_flow_name: 子流程名称
    @param is_recalc_sync_dbs: 控制在流程运行是否在传输上下文获取sync_dbs,适配于原地重建slave场景
    @param is_recalc_clean_dbs: 控制在流程运行是否在传输上下文获取clean_dbs,适配于原地重建slave场景
    @param master_host: 当前指定的master主机
    @param port: 端口号
    @param sync_mode: 数据的同步模式，默认不需要传递，如果传递，则以传入为准。目的是兼容单节点集群迁移的场景
    """

    # 获取集群的备份路径
    cluster_backup_path = get_backup_path(cluster.id)
    if cluster_backup_path == "":
        # 如果没有配置，则用默认路径
        backup_path = str(PureWindowsPath("d:/") / "dbbak" / f"restore_dr_{root_id}_{port}")
    else:
        backup_path = str(PureWindowsPath(cluster_backup_path) / f"restore_dr_{root_id}_{port}")
    # 获取集群的同步模式
    # 如果cluster_sync_mode 为空，则默认是mirror
    cluster_sync_mode = (
        sync_mode if sync_mode else SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
    )

    # 生成切换payload的字典
    sync_payload_func_map = {
        SqlserverSyncMode.MIRRORING: SqlserverActPayload.get_build_database_mirroring.__name__,
        SqlserverSyncMode.ALWAYS_ON: SqlserverActPayload.get_build_add_dbs_in_always_on.__name__,
    }
    #  判断必要参数
    if len(sync_slaves) == 0 or (len(sync_dbs) == 0 and is_recalc_sync_dbs is False):
        raise Exception("sync_slaves or sync_dbs is null, check")

    # 做判断, cluster_sync_mode 如果是mirror，原则上不允许一主多从的架构, 所以判断传入的slave是否有多个
    if cluster_sync_mode == SqlserverSyncMode.MIRRORING and len(sync_slaves) > 1:
        raise Exception(f"[{cluster_sync_mode}] does not support multiple slaves")

    global_data = {
        "uid": uid,
        "port": port,
        "backup_dbs": sync_dbs,
        "target_backup_dir": backup_path,
        "is_set_full_model": True,
        "job_id": f"restore_dr_{root_id}_{port}",
        "clean_dbs": clean_dbs if clean_dbs else sync_dbs,
        "clean_mode": SqlserverCleanMode.DROP_DBS.value,
        "clean_tables": ["*"],
        "ignore_clean_tables": [],
        "sync_mode": SqlserverSyncModeMaps[cluster_sync_mode],
        "slaves": [],
        "is_recalc_sync_dbs": is_recalc_sync_dbs,  # 判断标志位待入到全局上下文，获取payload进行判断
        "is_recalc_clean_dbs": is_recalc_clean_dbs,  # 判断标志位待入到全局上下文，获取payload进行判断
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 先禁用例行备份逻辑
    sub_pipeline.add_act(
        act_name=_("禁用backup jobs"),
        act_component_code=ExecSqlserverBackupJobComponent.code,
        kwargs=asdict(
            ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.DISABLE),
        ),
    )
    # 给所有的sync_slave下发执行器
    sub_pipeline.add_act(
        act_name=_("下发执行器"),
        act_component_code=TransFileInWindowsComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                target_hosts=sync_slaves + [master_host],
                file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
            ),
        ),
    )
    # 清理从库对应的数据库
    acts_list = []
    for slave in sync_slaves:
        acts_list.append(
            {
                "act_name": _("清理slave实例数据库[{}]".format(slave.ip)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[slave],
                        get_payload_func=SqlserverActPayload.get_clean_dbs_payload.__name__,
                        custom_params={"is_force": True},
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 执行备份
    sub_pipeline.add_act(
        act_name=_("执行数据库备份"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[master_host],
                get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                custom_params={
                    "port": port,
                    "file_tag": SqlserverBackupFileTagEnum.DBFILE1M.value,
                    "backup_type": SqlserverBackupMode.FULL_BACKUP.value,
                },
            )
        ),
        write_payload_var=SqlserverBackupIDContext.full_backup_id_var_name(),
    )
    # 执行数据库日志备份
    sub_pipeline.add_act(
        act_name=_("执行数据库日志备份"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[master_host],
                get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                custom_params={
                    "port": port,
                    "file_tag": SqlserverBackupFileTagEnum.INCREMENT_BACKUP.value,
                    "backup_type": SqlserverBackupMode.LOG_BACKUP.value,
                },
            )
        ),
        write_payload_var=SqlserverBackupIDContext.log_backup_id_var_name(),
    )
    # 传送备份文件
    sub_pipeline.add_act(
        act_name=_("传送文件到目标机器"),
        act_component_code=SqlserverTransBackupFileFor2P2Component.code,
        kwargs=asdict(
            P2PFileForWindowKwargs(
                source_hosts=[master_host],
                target_hosts=sync_slaves,
                file_target_path=backup_path,
                cluster_id=cluster.id,
                is_rolling=True,
            ),
        ),
    )
    # 恢复全量备份文件
    acts_list = []
    for slave in sync_slaves:
        acts_list.append(
            {
                "act_name": _("恢复全量备份数据[{}:{}]".format(slave.ip, port)),
                "act_component_code": RestoreForDoDrComponent.code,
                "kwargs": asdict(
                    RestoreForDoDrKwargs(
                        cluster_id=cluster.id,
                        job_id=global_data["job_id"],
                        restore_dbs=sync_dbs,
                        restore_mode=SqlserverRestoreMode.FULL,
                        exec_ips=[slave],
                        port=port,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    # 恢复日志备份文件
    acts_list = []
    for slave in sync_slaves:
        acts_list.append(
            {
                "act_name": _("恢复增量备份数据[{}:{}]".format(slave.ip, port)),
                "act_component_code": RestoreForDoDrComponent.code,
                "kwargs": asdict(
                    RestoreForDoDrKwargs(
                        cluster_id=cluster.id,
                        job_id=global_data["job_id"],
                        restore_dbs=sync_dbs,
                        restore_mode=SqlserverRestoreMode.LOG,
                        exec_ips=[slave],
                        port=port,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    # 建立数据库级别同步关系
    if cluster_sync_mode == SqlserverSyncMode.MIRRORING:
        custom_params = {"dr_host": sync_slaves[0].ip, "dr_port": port, "dbs": sync_dbs}
    else:
        custom_params = {
            "add_slaves": [{"host": i.ip, "port": port} for i in sync_slaves],
            "dbs": sync_dbs,
        }
    # 建立数据同步
    sub_pipeline.add_act(
        act_name=_("在master建立数据同步[{}]".format(master_host.ip)),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[master_host],
                get_payload_func=sync_payload_func_map[cluster_sync_mode],
                custom_params=custom_params,
            )
        ),
    )
    # 先禁用例行备份逻辑
    sub_pipeline.add_act(
        act_name=_("启动backup jobs"),
        act_component_code=ExecSqlserverBackupJobComponent.code,
        kwargs=asdict(
            ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.ENABLE),
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=sub_flow_name)


def install_surrounding_apps_sub_flow(
    uid: str,
    root_id: str,
    bk_biz_id: int,
    bk_cloud_id: int,
    slave_host: List[Host],
    master_host: List[Host],
    cluster_domain_list: list,
    is_install_backup_client: bool = True,
    is_init_app_setting: bool = True,
    is_init_nginx: bool = True,
    is_get_old_backup_config: bool = False,
):
    """
    安装sqlserver的周边程序的通用子流程, 暂时不能跨业务, 不能跨云区域
    @param uid: 单据id
    @param root_id: 主流程的id
    @param bk_biz_id: 业务id
    @param bk_cloud_id: 云区域id
    @param cluster_domain_list: 集群主域名列表
    @param slave_host: 从实例列表
    @param master_host: 主实例列表
    @param is_install_backup_client 是不是安装backup_client
    @param is_init_app_setting 是否初始化app_setting表
    @param is_init_nginx 是否初始化nginx配置
    @param is_get_old_backup_config 是否获取旧备份配置，内部导入标准化专属
    """
    # 构建子流程global_data
    global_data = {
        "uid": uid,
        "root_id": root_id,
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 提取所有主从实例的去重 IP 列表（过滤空值）
    unique_ips = list({host.ip for host in master_host + slave_host if host.ip})

    acts_list = []
    if is_install_backup_client:
        acts_list.append(
            {
                "act_name": _("安装backup-client工具"),
                "act_component_code": DownloadBackupClientComponent.code,
                "kwargs": asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=bk_cloud_id,
                        bk_biz_id=bk_biz_id,
                        ip_list=unique_ips,
                    )
                ),
            }
        )
    if is_init_app_setting:
        for cluster_domain in cluster_domain_list:
            acts_list.append(
                {
                    "act_name": _("集群[{}]初始化app_setting表".format(cluster_domain)),
                    "act_component_code": InsertAppSettingComponent.code,
                    "kwargs": asdict(
                        InsertAppSettingKwargs(
                            cluster_domain=cluster_domain,
                            ips=unique_ips,
                            is_get_old_backup_config=is_get_old_backup_config,
                        )
                    ),
                }
            )
    # 对dbm的nginx初始化
    if is_init_nginx:
        for cluster_domain in cluster_domain_list:
            acts_list.append(
                {
                    "act_name": _("集群[{}]初始化nginx配置".format(cluster_domain)),
                    "act_component_code": InitDBMNginxForSQLServerComponent.code,
                    "kwargs": asdict(InitDBMNginxForSQLServerComponent.kwargs(cluster_domain=cluster_domain)),
                }
            )
    if not acts_list:
        raise Exception(_("install_surrounding_apps_sub_flow的子流程列表为空"))

    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("部署sqlserver周边程序"))


def build_always_on_sub_flow(
    uid: str,
    root_id: str,
    master_instance: SqlserverInstance,
    slave_instances: List[SqlserverInstance],
    cluster_name: str,
    group_name: str,
    is_use_sa: bool = False,
):
    """
    建立集群always_on可用组的子流程
    @param uid: 单据id
    @param root_id: 主流程id
    @param master_instance: 集群主实例
    @param slave_instances: 集群从实例
    @param cluster_name: 集群名称
    @param group_name: 可用组名称
    @param is_use_sa: 是否使用sa账号，兼容集群部署时调用的场景
    """
    global_data = {
        "uid": uid,
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 为配置AlwaysOn可用组，对所有新加入的机器做对应初始化
    acts_list = []
    cluster_instances = [master_instance] + slave_instances
    for inst in cluster_instances:
        add_instances = copy.deepcopy(cluster_instances)
        # add_instances.remove(inst)
        if inst.is_new:
            # 表示机器是新加入，应该加入集群所有的节点信息到新机器上
            add_instances.remove(inst)
            add_members = [asdict(s) for s in add_instances]
        else:
            # 表示机器已经加入到集群内，则只加入新机器节点信息即可
            add_members = [asdict(s) for s in add_instances if s.is_new]

        acts_list.append(
            {
                "act_name": _("[{}]为alwaysOn做别名初始化".format(inst.host)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=inst.host, bk_cloud_id=inst.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_init_machine_for_always_on.__name__,
                        custom_params={
                            "port": inst.port,
                            "add_members": add_members,
                            "is_first": inst.is_new,
                            "is_use_sa": is_use_sa,
                        },
                    )
                ),
            }
        )

    sub_pipeline.add_parallel_acts(acts_list)

    # 在主实例配置AlwaysOn可用组
    sub_pipeline.add_act(
        act_name=_("[{}]集群配置可用组".format(cluster_name)),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[Host(ip=master_instance.host, bk_cloud_id=master_instance.bk_cloud_id)],
                get_payload_func=SqlserverActPayload.get_build_always_on.__name__,
                custom_params={
                    "port": master_instance.port,
                    "add_slaves": [asdict(s) for s in slave_instances if s.is_new],
                    "group_name": group_name,
                    "is_first": master_instance.is_new,
                    "is_use_sa": is_use_sa,
                },
            )
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=_("集群[{}]建立AlwaysOn可用组".format(cluster_name)))


def download_backup_file_sub_flow(
    uid: str,
    root_id: str,
    backup_file_list: list,
    target_path: str,
    write_payload_var: str,
    target_instance: StorageInstance,
    sub_name: str = _("下载备份文件"),
):
    # 构建子流程global_data
    global_data = {
        "uid": uid,
        "root_id": root_id,
    }

    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    # 判断备份文件是否存在，如果存在则移动对应恢复目录, 结果写入上下文
    sub_pipeline.add_act(
        act_name=_("判断备份文件存在本地机器"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[Host(ip=target_instance.machine.ip, bk_cloud_id=target_instance.machine.bk_cloud_id)],
                get_payload_func=SqlserverActPayload.check_backup_file_is_in_local.__name__,
                custom_params={"target_path": target_path, "file_list": backup_file_list},
            )
        ),
        write_payload_var=write_payload_var,
    )

    # 备份系统下载文件
    sub_pipeline.add_act(
        act_name=_("下载备份文件"),
        act_component_code=SqlserverDownloadBackupFileComponent.code,
        kwargs=asdict(
            DownloadBackupFileKwargs(
                bk_cloud_id=target_instance.machine.bk_cloud_id,
                dest_ip=target_instance.machine.ip,
                dest_dir=target_path,
                get_backup_file_info_var=write_payload_var,
            )
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=sub_name)


def switch_cluster_sub_flow(
    uid: str,
    root_id: str,
    cluster: Cluster,
    old_master_host: Host,
    new_master_host: Host,
    port: int,
    sync_mode_number: int,
    other_slaves: List[Dict],
    force: bool = False,
    sub_name: str = _("切换集群"),
) -> Optional[SubProcess]:
    """
    切换集群的子流程
    @param uid: 单据id
    @param root_id: 主流程id
    @param cluster: 集群对象
    @param old_master_host: 旧主机
    @param new_master_host: 新主机
    @param port: 端口
    @param sync_mode_number: 同步模式编号
    @param force: 是否强制切换
    @param other_slaves: 兼容一主多从集群，填入其余slaves
    @param sub_name: 子流程名称
    @return: 子流程
    """
    # 获取集群的备份位置
    backup_space = get_sqlserver_backup_config(
        bk_biz_id=cluster.bk_biz_id,
        db_module_id=cluster.db_module_id,
        cluster_domain=cluster.immute_domain,
    )["backup_space"]

    sub_pipeline = SubBuilder(root_id=root_id, data={"uid": uid, "root_id": root_id})

    if not force:
        # 如果是强制模式，不做预检测, 不做克隆
        sub_pipeline.add_sub_pipeline(
            sub_flow=pre_check_sub_flow(
                uid=uid,
                root_id=root_id,
                check_host=old_master_host,
                check_port=port,
                cluster_id=cluster.id,
            )
        )

        # 先做克隆user和link_server，保证这块内容切换前是同步的
        sub_pipeline.add_sub_pipeline(
            sub_flow=clone_configs_sub_flow(
                uid=uid,
                root_id=root_id,
                bk_biz_id=cluster.bk_biz_id,
                source_host=old_master_host,
                source_port=port,
                target_host=new_master_host,
                target_port=port,
                is_clone_user=True,
                is_clone_jobs=False,
                is_clone_linkserver=True,
                sub_flow_name=_("克隆user和Link_server配置"),
            )
        )

    # 执行切换
    sub_pipeline.add_act(
        act_name=_("执行切换"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=[new_master_host],
                get_payload_func=SqlserverActPayload.get_switch_payload.__name__,
                component_kwargs={
                    "target_port": port,
                    "master_host": old_master_host.ip,
                    "master_port": port,
                    "sync_mode": sync_mode_number,
                    "other_slaves": other_slaves,
                    "force": force,
                    "backup_space": backup_space,
                },
            )
        ),
    )

    if not force:
        # 再克隆job
        sub_pipeline.add_sub_pipeline(
            sub_flow=clone_configs_sub_flow(
                uid=uid,
                root_id=root_id,
                bk_biz_id=cluster.bk_biz_id,
                source_host=old_master_host,
                source_port=port,
                target_host=new_master_host,
                target_port=port,
                is_clone_user=False,
                is_clone_jobs=True,
                is_clone_linkserver=False,
                sub_flow_name=_("克隆job配置"),
            )
        )

    return sub_pipeline.build_sub_process(sub_name=sub_name)
