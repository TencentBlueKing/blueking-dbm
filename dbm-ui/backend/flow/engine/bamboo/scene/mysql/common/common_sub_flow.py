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
from dataclasses import asdict
from typing import Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import ProxyInstance
from backend.flow.consts import DBA_ROOT_USER, DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

"""
定义一些mysql流程上可能会用到的子流程，以便于减少代码的重复率
"""


def build_surrounding_apps_sub_flow(
    bk_cloud_id: int,
    root_id: str,
    parent_global_data: dict,
    cluster_type: Optional[ClusterType],
    is_init: bool = False,
    master_ip_list: list = None,
    slave_ip_list: list = None,
    proxy_ip_list: list = None,
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
        sub_pipeline.add_act(
            act_name=_("下发MySQL周边程序介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=list(filter(None, list(set(master_ip_list + slave_ip_list)))),
                    file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(),
                )
            ),
        )

    acts_list = []
    if isinstance(master_ip_list, list) and len(master_ip_list) != 0:
        for master_ip in list(set(master_ip_list)):
            acts_list.extend(
                [
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
                            )
                        ),
                    },
                    {
                        "act_name": _("Master[{}]安装rotate_binlog程序".format(master_ip)),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=bk_cloud_id,
                                exec_ip=master_ip,
                                get_mysql_payload_func=MysqlActPayload.get_install_rotate_binlog_payload.__name__,
                                cluster_type=cluster_type,
                                run_as_system_user=DBA_ROOT_USER,
                            )
                        ),
                    },
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
                    },
                ]
            )

            if cluster_type in (ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value):
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

    if isinstance(slave_ip_list, list) and len(slave_ip_list) != 0:
        for slave_ip in list(set(slave_ip_list)):
            acts_list.extend(
                [
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
                            )
                        ),
                    },
                    {
                        "act_name": _("Slave[{}]安装rotate_binlog程序".format(slave_ip)),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=bk_cloud_id,
                                exec_ip=slave_ip,
                                get_mysql_payload_func=MysqlActPayload.get_install_rotate_binlog_payload.__name__,
                                cluster_type=cluster_type,
                                run_as_system_user=DBA_ROOT_USER,
                            )
                        ),
                    },
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
                    },
                ]
            )

            if cluster_type in (ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value):
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

    if isinstance(proxy_ip_list, list) and len(proxy_ip_list) != 0:
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

    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("安装MySql周边程序"))


def build_repl_by_manual_input_sub_flow(
    bk_cloud_id: int,
    root_id: str,
    parent_global_data: dict,
    master_ip: str,
    slave_ip: str,
    mysql_port: int,
    sub_flow_name: str = None,
):
    """
    定义mysql建立主从同步（异步同步）的子流程，只支持一主一从的建立，如果是多从，则调用多次子流程即可
    针对手输IP场景
    @param bk_cloud_id: 操作的云区域id
    @param root_id: flow流程的root_id
    @param parent_global_data: 子流程的上层全局只读上下文
    @param master_ip：主节点ip
    @param slave_ip: 从节点ip
    @param mysql_port: mysql port,系统默认主从都一致
    @param sub_flow_name: 子流程名称
    """
    cluster = {
        "new_slave_ip": slave_ip,
        "new_master_ip": master_ip,
        "mysql_port": mysql_port,
    }

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
                cluster=cluster,
                run_as_system_user=DBA_SYSTEM_USER,
            )
        ),
        write_payload_var=write_payload_var_name,
    )

    sub_pipeline.add_act(
        act_name=_("建立主从关系"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=slave_ip,
                get_mysql_payload_func=MysqlActPayload.get_change_master_payload.__name__,
                cluster=cluster,
                run_as_system_user=DBA_SYSTEM_USER,
            )
        ),
    )
    return sub_pipeline.build_sub_process(sub_name=_("建立主从同步[{}]".format(sub_flow_name)))


def build_apps_for_spider_sub_flow(
    bk_cloud_id: int,
    spiders: list,
    root_id: str,
    parent_global_data: dict,
):
    """
    定义为spider机器部署周边组件的子流程
    @param bk_cloud_id: 操作所属的云区域
    @param spiders: 需要操作的spider机器列表信息
    @param root_id: 整体flow流程的root_id
    @param parent_global_data: 子流程的需要全局只读上下文
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 适配切换类单据场景
    sub_pipeline.add_act(
        act_name=_("下发MySQL周边程序介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=list(filter(None, list(set(spiders)))),
                file_list=GetFileList(db_type=DBType.MySQL).get_spider_apps_package(),
            )
        ),
    )

    acts_list = []
    if isinstance(spiders, list) and len(spiders) != 0:
        for spider_ip in list(set(spiders)):
            acts_list.append(
                {
                    "act_name": _("Slave[{}]安装DBATools工具箱".format(spider_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=spider_ip,
                            get_mysql_payload_func=MysqlActPayload.get_install_dba_toolkit_payload.__name__,
                            cluster_type=ClusterType.TenDBCluster.value,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                }
            )

            acts_list.append(
                {
                    "act_name": _("spider[{}]安装mysql-monitor".format(spider_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=spider_ip,
                            get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
                            cluster_type=ClusterType.TenDBCluster.value,
                            run_as_system_user=DBA_ROOT_USER,
                        )
                    ),
                },
            )
            # 因为同一台机器的只有会有一个spider实例，所以直接根据ip、bk_cloud_id获取对应实例的spider角色，来判断是否安装备份程序
            spider_role = ProxyInstance.objects.get(
                machine__bk_cloud_id=bk_cloud_id, machine__ip=spider_ip
            ).tendbclusterspiderext.spider_role
            if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER.value:
                acts_list.append(
                    {
                        "act_name": _("spider[{}]安装备份程序".format(spider_ip)),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=bk_cloud_id,
                                exec_ip=spider_ip,
                                get_mysql_payload_func=MysqlActPayload.get_install_db_backup_payload.__name__,
                                cluster_type=ClusterType.TenDBCluster.value,
                                run_as_system_user=DBA_ROOT_USER,
                            )
                        ),
                    },
                )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)
    return sub_pipeline.build_sub_process(sub_name=_("安装Spider周边程序"))
