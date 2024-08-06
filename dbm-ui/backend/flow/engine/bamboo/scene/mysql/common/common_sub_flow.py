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
import logging.config
from dataclasses import asdict
from typing import List, Optional

from django.utils.translation import gettext as _

from backend import env
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import (
    DBA_ROOT_USER,
    DEPENDENCIES_PLUGINS,
    MediumEnum,
    MysqlVersionToDBBackupForMap,
    WriteContextOpType,
)
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.mysql.check_client_connections import CheckClientConnComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.mysql_os_init import (
    GetOsSysParamComponent,
    MySQLOsInitComponent,
    SysInitComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.verify_checksum import VerifyChecksumComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs, InstallNodemanPluginKwargs
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckClientConnKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    InitCheckKwargs,
    VerifyChecksumKwargs,
    YumInstallPerlKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_commom_query import query_mysql_variables
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")

"""
定义一些mysql流程上可能会用到的子流程，以便于减少代码的重复率
"""


def build_surrounding_apps_sub_flow(  # noqa
    bk_cloud_id: int,
    root_id: str,
    parent_global_data: dict,
    cluster_type: Optional[ClusterType],
    is_init: bool = False,
    master_ip_list: list = None,
    slave_ip_list: list = None,
    proxy_ip_list: list = None,
    is_install_backup: bool = True,
    is_install_monitor: bool = True,
    is_install_checksum: bool = True,
    is_install_rotate_binlog: bool = True,
    collect_sysinfo: bool = False,
    db_backup_pkg_type: MediumEnum = None,
):
    """
    定义重建备、数据检验程序、rotate_binlog程序等组件的子流程，面向整机操作
    提供给切换类单据拼接使用
    @param bk_cloud_id: 操作所属的云区域
    @param master_ip_list: master的ip， None代表这次master不需要操作
    @param slave_ip_list: slave的ip， None代表这次slave不需要操作
    @param proxy_ip_list: proxy的ip列表，[]代表这次没有proxy需要操作
    @param root_id: flow流程的root_id
    @param parent_global_data: 子流程的上层全局只读上下文
    @param is_init: 是否代表首次安装，针对部署、添加场景
    @param cluster_type: 操作的集群类型，涉及到获取配置空间
    @param is_install_backup: 是否安装备份,spider集群切换前忽略安装备份
    @param is_install_monitor: 是否安装监控,定点回档需要
    @param is_install_checksum: 是否安装checksum
    @param is_install_rotate_binlog: 是否安装rotate_binlog
    @param collect_sysinfo: 是否收集机器信息
    @param db_backup_pkg_type: 备份文件类型
    """
    if not master_ip_list:
        master_ip_list = []
    if not slave_ip_list:
        slave_ip_list = []
    if not proxy_ip_list:
        proxy_ip_list = []

    if len(master_ip_list) == 0 and len(slave_ip_list) == 0 and len(proxy_ip_list) == 0:
        raise Exception(_("执行ip信息为空"))

    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    if not is_init:
        # 如果是重建模式，理论上需要重新下发周边的介质包，保证介质包最新版本
        # 适配切换类单据场景
        # 通过ip所在cluster，获取db_dbbackup版本
        if is_install_backup:
            if env.MYSQL_BACKUP_PKG_MAP_ENABLE and not db_backup_pkg_type:
                tmep_inst = StorageInstance.objects.filter(
                    machine__ip__in=list(filter(None, list(set(master_ip_list + slave_ip_list))))
                ).first()
                db_version = tmep_inst.cluster.get().major_version
                db_backup_pkg_type = MysqlVersionToDBBackupForMap[db_version]
            if not db_backup_pkg_type:
                db_backup_pkg_type = MediumEnum.DbBackup

        sub_pipeline.add_act(
            act_name=_("下发MySQL周边程序介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=list(filter(None, list(set(master_ip_list + slave_ip_list)))),
                    file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(
                        is_install_backup=is_install_backup,
                        is_install_monitor=is_install_monitor,
                        db_backup_pkg_type=db_backup_pkg_type,
                    ),
                )
            ),
        )

    acts_list = []
    # 是否采集系统信息
    if collect_sysinfo:
        acts_list.append(
            update_machine_system_info_flow(
                root_id=root_id,
                bk_cloud_id=bk_cloud_id,
                parent_global_data=parent_global_data,
                ip_list=master_ip_list[:] + slave_ip_list[:] + proxy_ip_list[:],
            )
        )
    if isinstance(master_ip_list, list) and len(list(filter(None, list(set(master_ip_list))))) != 0:
        acts_list.extend(
            build_surrounding_apps_for_master(
                bk_cloud_id=bk_cloud_id,
                cluster_type=cluster_type,
                master_ip_list=list(filter(None, list(set(master_ip_list)))),
                is_init=is_init,
                is_install_backup=is_install_backup,
                is_install_monitor=is_install_monitor,
                is_install_checksum=is_install_checksum,
                is_install_rotate_binlog=is_install_rotate_binlog,
                db_backup_pkg_type=db_backup_pkg_type,
            )
        )
    if isinstance(slave_ip_list, list) and len(list(filter(None, list(set(slave_ip_list))))) != 0:
        acts_list.extend(
            build_surrounding_apps_for_slave(
                bk_cloud_id=bk_cloud_id,
                cluster_type=cluster_type,
                slave_ip_list=list(filter(None, list(set(slave_ip_list)))),
                is_init=is_init,
                is_install_backup=is_install_backup,
                is_install_monitor=is_install_monitor,
                is_install_checksum=is_install_checksum,
                is_install_rotate_binlog=is_install_rotate_binlog,
                db_backup_pkg_type=db_backup_pkg_type,
            )
        )
    if isinstance(proxy_ip_list, list) and len(list(filter(None, list(set(proxy_ip_list))))) != 0:
        acts_list.extend(
            build_surrounding_apps_for_proxy(
                bk_cloud_id=bk_cloud_id,
                cluster_type=cluster_type,
                proxy_ip_list=list(filter(None, list(set(proxy_ip_list)))),
            )
        )

    if is_init:
        # 如果非重建模式（上架阶段）， 不需要重建安装backup-client工具,默认情况下部署时 proxy+mysql机器都会安装
        acts_list.append(
            {
                "act_name": _("安装backup-client工具"),
                "act_component_code": DownloadBackupClientComponent.code,
                "kwargs": asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=bk_cloud_id,
                        bk_biz_id=int(parent_global_data["bk_biz_id"]),
                        download_host_list=list(
                            filter(None, list(set(master_ip_list + slave_ip_list + proxy_ip_list)))
                        ),
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("安装MySql周边程序"))


def build_surrounding_apps_for_master(
    bk_cloud_id: int,
    cluster_type: Optional[ClusterType],
    master_ip_list: list = None,
    is_init: bool = False,
    is_install_backup: bool = True,
    is_install_monitor: bool = True,
    is_install_checksum: bool = True,
    is_install_rotate_binlog: bool = True,
    db_backup_pkg_type: MediumEnum = None,
):
    acts_list = []
    for master_ip in list(set(master_ip_list)):
        if is_install_rotate_binlog:
            acts_list.append(
                {
                    "act_name": _("Master[{}]安装rotate_binlog程序".format(master_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=master_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_mysql_rotatebinlog_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                },
            )
        if is_install_monitor:
            acts_list.append(
                {
                    "act_name": _("Master[{}]安装mysql-monitor".format(master_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=master_ip,
                            get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                }
            )

        if is_install_backup:
            acts_list.append(
                {
                    "act_name": _("Master[{}]安装备份程序".format(master_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=master_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_db_backup_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                            cluster={"db_backup_pkg_type": db_backup_pkg_type},
                        )
                    ),
                }
            )

        if cluster_type in (ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value) and is_install_checksum:
            # 主从架构部署mysql-checksum程序
            acts_list.append(
                {
                    "act_name": _("Master[{}]安装校验程序".format(master_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=master_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_mysql_checksum_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                }
            )

        if is_init:
            acts_list.append(
                {
                    "act_name": _("Master[{}]安装DBATools工具箱".format(master_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=master_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_dba_toolkit_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                }
            )
    return acts_list


def build_surrounding_apps_for_slave(
    bk_cloud_id: int,
    cluster_type: Optional[ClusterType],
    slave_ip_list: list = None,
    is_init: bool = False,
    is_install_backup: bool = True,
    is_install_monitor: bool = True,
    is_install_checksum: bool = True,
    is_install_rotate_binlog: bool = True,
    db_backup_pkg_type: MediumEnum = None,
):
    acts_list = []
    for slave_ip in list(set(slave_ip_list)):
        if is_install_rotate_binlog:
            acts_list.append(
                {
                    "act_name": _("Slave[{}]安装rotate_binlog程序".format(slave_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=slave_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_mysql_rotatebinlog_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                },
            )
        if is_install_monitor:
            acts_list.append(
                {
                    "act_name": _("Slave[{}]安装mysql-monitor".format(slave_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=slave_ip,
                            get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                }
            )

        if is_install_backup:
            acts_list.append(
                {
                    "act_name": _("Slave[{}]安装备份程序".format(slave_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=slave_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_db_backup_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                            cluster={"db_backup_pkg_type": db_backup_pkg_type},
                        )
                    ),
                },
            )

        if cluster_type in (ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value) and is_install_checksum:
            # 主从架构部署mysql-checksum程序
            acts_list.append(
                {
                    "act_name": _("Slave[{}]安装校验程序".format(slave_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=slave_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_mysql_checksum_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                }
            )

        if is_init:
            acts_list.append(
                {
                    "act_name": _("Slave[{}]安装DBATools工具箱".format(slave_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=slave_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_dba_toolkit_payload.__name__,
                            cluster_type=cluster_type,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                }
            )
    return acts_list


def build_surrounding_apps_for_proxy(
    bk_cloud_id: int,
    cluster_type: Optional[ClusterType],
    proxy_ip_list: list = None,
):
    acts_list = []
    for proxy_ip in proxy_ip_list:
        acts_list.append(
            {
                "act_name": _("Proxy安装mysql-monitor"),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=proxy_ip,
                        get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
                        cluster_type=cluster_type,
                        run_as_system_user=DBA_ROOT_USER,
                    )
                ),
            }
        )
    return acts_list


def build_repl_by_manual_input_sub_flow(
    bk_cloud_id: int,
    root_id: str,
    parent_global_data: dict,
    master_ip: str,
    slave_ip: str,
    master_port: int,
    slave_port: int,
    sub_flow_name: str = None,
    is_tbinlogdumper: bool = False,
):
    """
    定义mysql建立主从同步（异步同步）的子流程，只支持一主一从的建立，如果是多从，则调用多次子流程即可
    针对手输IP场景
    @param bk_cloud_id: 操作的云区域id
    @param root_id: flow流程的root_id
    @param parent_global_data: 子流程的上层全局只读上下文
    @param master_ip：主节点ip
    @param slave_ip: 从节点ip
    @param master_port: master port,
    @param slave_port: slave port,
    @param sub_flow_name: 子流程名称
    @param is_tbinlogdumper: 是否是tbinlogdumper实例做数据同步
    """

    # write_payload_var_name: pos位点信息存储上下文的变量位置
    write_payload_var_name = "master_ip_sync_info"

    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    sub_pipeline.add_act(
        act_name=_("新增repl帐户"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=master_ip,
                get_mysql_payload_func=MysqlActPayload.get_grant_mysql_repl_user_payload.__name__,
                cluster={"new_slave_ip": slave_ip, "mysql_port": master_port},
                run_as_system_user=DBA_ROOT_USER,
            )
        ),
        write_payload_var=write_payload_var_name,
    )

    if is_tbinlogdumper:
        get_mysql_payload_func = MysqlActPayload.tbinlogdumper_change_master_payload.__name__
    else:
        get_mysql_payload_func = MysqlActPayload.get_change_master_payload.__name__

    sub_pipeline.add_act(
        act_name=_("建立主从关系"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=slave_ip,
                get_mysql_payload_func=get_mysql_payload_func,
                cluster={"new_master_ip": master_ip, "master_port": master_port, "slave_port": slave_port},
                run_as_system_user=DBA_ROOT_USER,
            )
        ),
    )
    return sub_pipeline.build_sub_process(sub_name=_("建立主从同步[{}]".format(sub_flow_name)))


def install_mysql_in_cluster_sub_flow(
    uid: str,
    root_id: str,
    cluster: Cluster,
    new_mysql_list: list,
    install_ports: list,
    bk_host_ids: list = None,
    pkg_id: int = 0,
    db_module_id: str = None,
):
    """
    设计基于某个cluster，以及计算好的实例安装端口列表，对新机器安装mysql实例的公共子流
    子流程并不是提供给部署类单据的，目标是提供tendb_ha/tendb_cluster扩容类单据
    @param uid: 流程uid
    @param root_id: flow流程的root_id
    @param cluster: 关联的cluster对象
    @param new_mysql_list: 新机器列表，每个元素是ip
    @param install_ports: 每台机器按照的实例端口列表
    @param bk_host_ids: 新机器列表，每个元素是bk_host_id
    """

    # 目前先根据cluster对应，请求bk-config服务去获取对应的
    # todo 后续可能继续优化这块逻辑，mysql的版本号通过记录的小版本信息来获取？
    if db_module_id is None:
        db_module_id = str(cluster.db_module_id)

    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(cluster.bk_biz_id),
            "level_name": LevelName.MODULE,
            "level_value": db_module_id,
            "conf_file": "deploy_info",
            "conf_type": "deploy",
            "namespace": cluster.cluster_type,
            "format": FormatType.MAP,
        }
    )["content"]

    parent_global_data = {
        "uid": uid,
        "charset": data["charset"],
        "db_version": data["db_version"],
        "mysql_ports": install_ports,
        "bk_biz_id": cluster.bk_biz_id,
        "clusters": [],
    }
    for port in install_ports:
        parent_global_data["clusters"].append({"mysql_port": port, "master": cluster.immute_domain})
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster.bk_cloud_id,
        cluster_type=cluster.cluster_type,
    )

    # 初始化机器
    master = cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER.value).first()
    sub_pipeline.add_act(
        act_name=_("获取旧实例系统参数"),
        act_component_code=GetOsSysParamComponent.code,
        kwargs=asdict(ExecActuatorKwargs(bk_cloud_id=cluster.bk_cloud_id, exec_ip=master.machine.ip)),
    )

    sub_pipeline.add_sub_pipeline(
        sub_flow=init_machine_sub_flow(
            uid=uid,
            root_id=root_id,
            bk_cloud_id=cluster.bk_cloud_id,
            sys_init_ips=new_mysql_list,
            init_check_ips=new_mysql_list,
            yum_install_perl_ips=new_mysql_list,
            bk_host_ids=bk_host_ids,
        )
    )

    # 阶段1 并行分发安装文件
    if pkg_id > 0:
        sub_pipeline.add_parallel_acts(
            acts_list=[
                {
                    "act_name": _("下发MySQL介质包"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            exec_ip=new_mysql_list,
                            file_list=GetFileList(db_type=DBType.MySQL).mysql_upgrade_package(
                                pkg_id=pkg_id, db_version=data["db_version"]
                            ),
                        )
                    ),
                }
            ]
        )
    else:
        sub_pipeline.add_parallel_acts(
            acts_list=[
                {
                    "act_name": _("下发MySQL介质包"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            exec_ip=new_mysql_list,
                            file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                                db_version=data["db_version"]
                            ),
                        )
                    ),
                }
            ]
        )

    acts_list = []
    for mysql_ip in new_mysql_list:
        exec_act_kwargs.exec_ip = mysql_ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
        acts_list.append(
            {
                "act_name": _("部署mysql-crond {}".format(exec_act_kwargs.exec_ip)),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(exec_act_kwargs),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 阶段3 并发安装mysql实例(一个活动节点部署多实例)
    acts_list = []
    for mysql_ip in new_mysql_list:
        exec_act_kwargs.exec_ip = mysql_ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_mysql_payload.__name__
        acts_list.append(
            {
                "act_name": _("安装MySQL实例 {}".format(exec_act_kwargs.exec_ip)),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(exec_act_kwargs),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("安装mysql实例flow"))


def check_sub_flow(
    uid: str,
    root_id: str,
    cluster: Cluster,
    is_check_client_conn: bool = False,
    check_client_conn_inst: list = None,
    is_verify_checksum: bool = False,
    verify_checksum_tuples: list = None,
):
    """
    设计预检测的公共子流程，主要服务于切换类的流程，做前置检查，方便管控
    @param uid: 流程单据的uid
    @param root_id: flow流程的root_id
    @param cluster: 关联的cluster对象
    @param is_check_client_conn: 是否做客户端连接检测
    @param check_client_conn_inst: 如果做客户端连接检测，则传入待检测的实例列表，["ip:port"...]
    @param is_verify_checksum: 是否做验证checksum结果
    @param verify_checksum_tuples: 如果验证checksum，则传入待检测的实例列表，每个元素[{"master":"ip:port", "slave":"ip:port"}..]
    """

    if is_check_client_conn and not check_client_conn_inst:
        raise Exception(_("构建子流程失败，联系系统管理员, check_client_conn_inst is null"))
    if is_verify_checksum and not verify_checksum_tuples:
        raise Exception(_("构建子流程失败，联系系统管理员, verify_checksum_tuples is null"))

    act_list = []
    if is_check_client_conn:
        act_list.append(
            {
                "act_name": _("检测客户端连接情况"),
                "act_component_code": CheckClientConnComponent.code,
                "kwargs": asdict(
                    CheckClientConnKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        check_instances=check_client_conn_inst,
                    )
                ),
            }
        )

    if is_verify_checksum:
        act_list.append(
            {
                "act_name": _("检测checksum结果"),
                "act_component_code": VerifyChecksumComponent.code,
                "kwargs": asdict(
                    VerifyChecksumKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        checksum_instance_tuples=verify_checksum_tuples,
                    )
                ),
            }
        )

    if not act_list:
        return None

    sub_pipeline = SubBuilder(root_id=root_id, data={"uid": uid})
    sub_pipeline.add_parallel_acts(acts_list=act_list)

    return sub_pipeline.build_sub_process(sub_name=_("[{}]预检测".format(cluster.name)))


def init_machine_sub_flow(
    uid: str,
    root_id: str,
    bk_cloud_id: int,
    sys_init_ips: list,
    init_check_ips: list = None,
    yum_install_perl_ips: list = None,
    bk_host_ids: List[int] = None,
):
    """
    定义初始化机器的公共子流程，提供给mysql/spider/proxy新机器的初始化适用，不支持跨云区域处理
    @param uid: 流程单据的uid
    @param root_id: flow流程的root_id
    @param bk_cloud_id: 需要操作的机器的对应云区域ID
    @param sys_init_ips: 需要初始化的机器ip列表
    @param init_check_ips: 需要做空闲检查的机器ip列表
    @param yum_install_perl_ips:需要按照perl环境的机器ip列表
    @param bk_host_ids: List[int] 操作的主机
    """
    if not sys_init_ips and not init_check_ips and not yum_install_perl_ips:
        raise Exception(
            _("构建init_machine_sub子流程失败，联系系统管理员, sys_init_ips & init_check_ips & yum_install_perl_ips is null")
        )

    sub_pipeline = SubBuilder(root_id=root_id, data={"uid": uid})
    # 并行执行空闲检查
    if env.SA_CHECK_TEMPLATE_ID and init_check_ips:
        acts_list = []
        for ip in init_check_ips:
            acts_list.append(
                {
                    "act_name": _("空闲检查[{}]".format(ip)),
                    "act_component_code": CheckMachineIdleComponent.code,
                    "kwargs": asdict(InitCheckKwargs(ips=[ip], bk_cloud_id=bk_cloud_id)),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 初始化机器
    if sys_init_ips:
        sub_pipeline.add_act(
            act_name=_("初始化机器"),
            act_component_code=SysInitComponent.code,
            kwargs={
                "exec_ip": sys_init_ips,
                "bk_cloud_id": bk_cloud_id,
            },
        )

    # 安装插件
    acts_list = []
    # 这里用 bk_host_ids 临时兼容，更合理的做法是，参数流转都不使用 IP，统一使用 bk_host_id
    if bk_host_ids:
        for plugin_name in DEPENDENCIES_PLUGINS:
            acts_list.append(
                {
                    "act_name": _("安装[{}]插件".format(plugin_name)),
                    "act_component_code": InstallNodemanPluginServiceComponent.code,
                    "kwargs": asdict(InstallNodemanPluginKwargs(bk_host_ids=bk_host_ids, plugin_name=plugin_name)),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 判断是否需要执行按照MySQL Perl依赖
    if env.YUM_INSTALL_PERL and yum_install_perl_ips:
        sub_pipeline.add_act(
            act_name=_("安装MySQL Perl相关依赖"),
            act_component_code=MySQLOsInitComponent.code,
            kwargs=asdict(
                YumInstallPerlKwargs(
                    exec_ip=yum_install_perl_ips,
                    bk_cloud_id=bk_cloud_id,
                )
            ),
        )
    return sub_pipeline.build_sub_process(sub_name=_("机器初始化"))


def update_machine_system_info_flow(
    root_id: str,
    parent_global_data: dict,
    bk_cloud_id: int,
    ip_list: list = None,
):
    """
    采集机器系统信息
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)
    sub_pipeline.add_act(
        act_name=_("获取机器系统信息"),
        act_component_code=GetOsSysParamComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=ip_list,
                write_op=WriteContextOpType.APPEND.value,
            )
        ),
    )
    cluster = {"ip_list": ip_list, "bk_cloud_id": bk_cloud_id}
    sub_pipeline.add_act(
        act_name=_("更新主机system info"),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.update_machine_system_info.__name__,
                cluster=cluster,
                is_update_trans_data=True,
            )
        ),
    )
    return sub_pipeline.build_sub_process(sub_name=_("获取机器系统信息"))


def sync_mycnf_item_sub_flow(
    uid: str,
    root_id: str,
    bk_cloud_id: int,
    src_host: str,
    src_port: int,
    master_slave_hosts: list,
    dest_port: int,
    var_list: list,
):
    """
    同步修改mysql配置
    """
    var_map = query_mysql_variables(
        host=src_host,
        port=src_port,
        bk_cloud_id=bk_cloud_id,
    )
    item = {}
    act_lists = []
    for var_name in var_list:
        key = "mysqld.{}".format(var_name)
        val = var_map.get(var_name)
        item[key] = {"conf_value": val, "op_type": "upsert"}

    sub_pipeline = SubBuilder(root_id=root_id, data={"uid": uid})
    for host in master_slave_hosts:
        act_lists.append(
            {
                "act_name": _("修改{}上实例的的my.cnf配置".format(host)),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=host,
                        bk_cloud_id=bk_cloud_id,
                        cluster={"ports": [dest_port], "items": item},
                        get_mysql_payload_func=MysqlActPayload.get_change_mycnf_payload.__name__,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=act_lists)
    return sub_pipeline.build_sub_process(sub_name=_("同步修改my.cnf配置"))
