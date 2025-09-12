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
import logging
from dataclasses import asdict
from typing import List

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_version_parse import get_online_mysql_version, tmysql_version_parse

logger = logging.getLogger("flow")


def get_storage_actual_version(cluster_id: int) -> str:
    """
    获取存储层的实际版本 select version();
    返回值如下
    #  select version()
    #  tmysql:  select version();==> 5.7.20-tmysql-3.4.2-log
    #  社区版本 mysql:> select version(); 8.0.32
    #  txsql: select version(); 8.0.30-txsql
    """
    cluster = Cluster.objects.get(id=cluster_id)
    instance = StorageInstance.objects.filter(
        cluster=cluster,
    ).first()
    return get_online_mysql_version(instance.machine.ip, instance.port, cluster.bk_cloud_id)


def get_is_same_tmysql_version(cluster_id: int, pkg_name: str) -> bool:
    """
    获取存储层的实际版本是否与升级包的版本相同 tmysql版本
    """
    storage_real_version = get_storage_actual_version(cluster_id)
    if storage_real_version.startswith("tmysql") and pkg_name.startswith("tmysql"):
        return False
    tmysql_version_num = tmysql_version_parse(storage_real_version)
    pkg_version_num = tmysql_version_parse(pkg_name)
    if tmysql_version_num // 1000000 == pkg_version_num // 1000000:
        return True
    return False


def mysql_upgrade_subflow(
    uid: str,
    root_id: str,
    parent_global_data: dict,
    bk_cloud_id: int,
    ip: str,
    mysql_ports: List[int],
    pkg_id: int,
    sub_flow_name: str = None,
    skip_send_pkg: bool = False,
    is_same_tmysql_version: bool = False,
) -> SubBuilder:
    """
    MySQL升级子流程，包含完整的升级步骤
    步骤顺序：mysql-relink → upgrade_start → upgrade_prepare → upgrade_exec → upgrade_restart(可选)

    @param uid: 流程单据的uid
    @param root_id: flow流程的root_id
    @param parent_global_data: 父流程的全局数据
    @param bk_cloud_id: 云区域ID
    @param ip: 目标MySQL实例IP
    @param mysql_ports: MySQL端口列表
    @param pkg_id: 升级包ID
    @param force: 是否强制升级
    @param need_restart: 是否需要执行upgrade_restart步骤
    @param sub_flow_name: 子流程名称
    @return: SubBuilder对象
    """

    if sub_flow_name is None:
        sub_flow_name = _("MySQL升级[{}]").format(ip)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # ============ 步骤1: 下发MySQL升级包 ============
    if not skip_send_pkg:
        sub_pipeline.add_act(
            act_name=_("下发MySQL升级包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=ip,
                    file_list=GetFileList(db_type=DBType.MySQL).mysql_upgrade_package(pkg_id=pkg_id, db_version=""),
                )
            ),
        )

    # ============ 步骤2: MySQL重新链接 (机器级别，只执行一次) ============
    relink_kwargs = ExecActuatorKwargs(
        bk_cloud_id=bk_cloud_id,
        exec_ip=ip,
        run_as_system_user=DBA_ROOT_USER,
        cluster={
            "pkg_id": pkg_id,
        },
        get_mysql_payload_func=MysqlActPayload.get_mysql_upgrade_relink_payload.__name__,
    )
    sub_pipeline.add_act(
        act_name=_("MySQL重新链接版本介质"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(relink_kwargs),
    )

    # ============ 步骤3-6: 实例级别操作（按端口串行执行） ============

    # 为每个端口串行执行升级步骤
    sub_ins_pipelines = []
    for port in mysql_ports:
        # 通用参数配置（按端口）
        base_kwargs = {
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": ip,
            "run_as_system_user": DBA_ROOT_USER,
            "cluster": {
                "port": port,  # 单个端口，不是数组
                "pkg_id": pkg_id,
            },
        }
        sub_ins_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)
        # 步骤3: upgrade_prepare, will stop mysqld and change my.cnf
        prepare_kwargs = ExecActuatorKwargs(
            **base_kwargs,
            get_mysql_payload_func=MysqlActPayload.get_mysql_upgrade_prepare_payload.__name__,
        )
        sub_ins_pipeline.add_act(
            act_name=_("替换配置、关闭MySQL[{}:{}]").format(ip, port),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(prepare_kwargs),
        )

        # 步骤4: upgrade_start
        start_kwargs = ExecActuatorKwargs(
            **base_kwargs,
            get_mysql_payload_func=MysqlActPayload.get_mysql_upgrade_start_payload.__name__,
        )
        sub_ins_pipeline.add_act(
            act_name=_("启动[{}:{}]").format(ip, port),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(start_kwargs),
        )
        # 如果是相同的tmysql版本，跳过upgrade_exec和upgrade_restart步骤
        if not is_same_tmysql_version:
            # 步骤5: upgrade_exec
            exec_kwargs = ExecActuatorKwargs(
                **base_kwargs,
                get_mysql_payload_func=MysqlActPayload.get_mysql_upgrade_exec_payload.__name__,
            )
            sub_ins_pipeline.add_act(
                act_name=_("MySQL升级执行[{}:{}]").format(ip, port),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_kwargs),
            )

            # 步骤6: upgrade_restart
            restart_kwargs = ExecActuatorKwargs(
                **base_kwargs,
                get_mysql_payload_func=MysqlActPayload.get_mysql_upgrade_restart_payload.__name__,
            )
            sub_ins_pipeline.add_act(
                act_name=_("重启[{}:{}]").format(ip, port),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(restart_kwargs),
            )
        built_sub_process = sub_ins_pipeline.build_sub_process(sub_name=_("MySQL实例升级[{}:{}]").format(ip, port))
        sub_ins_pipelines.append(built_sub_process)

    sub_pipeline.add_parallel_sub_pipeline(sub_ins_pipelines)
    logger.info(_("MySQL升级子流程构建完成，IP: {}，端口: {}").format(ip, mysql_ports))

    return sub_pipeline.build_sub_process(sub_name=sub_flow_name)


def mysql_cluster_upgrade_check_subflow(
    uid: str,
    root_id: str,
    parent_global_data: dict,
    bk_cloud_id: int,
    upgrade_instances: List[dict],
    pkg_id: int,
    sub_flow_name: str = None,
) -> SubBuilder:
    """
    MySQL集群升级检查子流程，仅执行升级前检查

    @param uid: 流程单据的uid
    @param root_id: flow流程的root_id
    @param parent_global_data: 父流程的全局数据
    @param bk_cloud_id: 云区域ID
    @param upgrade_instances: 升级实例列表，格式：[{"ip": "x.x.x.x", "ports": [3306, 3307]}]
    @param pkg_id: 升级包ID
    @param force: 是否强制升级
    @param sub_flow_name: 子流程名称
    @return: SubBuilder对象
    """

    if sub_flow_name is None:
        sub_flow_name = _("MySQL集群升级检查")

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 收集所有实例信息用于检查
    all_instances = []
    check_ips = []

    for instance in upgrade_instances:
        ip = instance["ip"]
        ports = instance["ports"]
        if ip not in check_ips:
            check_ips.append(ip)
        for port in ports:
            all_instances.append({"ip": ip, "port": port})

    # 并行检查所有机器
    check_acts = []
    for ip in check_ips:
        # 获取该IP上的所有端口
        ip_ports = []
        for instance in upgrade_instances:
            if instance["ip"] == ip:
                ip_ports.extend(instance["ports"])

        # 创建该IP的检查活动
        check_kwargs = ExecActuatorKwargs(
            bk_cloud_id=bk_cloud_id,
            exec_ip=ip,
            run_as_system_user=DBA_ROOT_USER,
            cluster={
                "ports": ip_ports,
                "pkg_id": pkg_id,
            },
            get_mysql_payload_func=MysqlActPayload.get_mysql_upgrade_check_payload.__name__,
        )

        check_acts.append(
            {
                "act_name": _("MySQL升级检查[{}]").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(check_kwargs),
            }
        )

    # 并行执行所有检查
    if check_acts:
        sub_pipeline.add_parallel_acts(acts_list=check_acts)

    logger.info(_("MySQL集群升级检查子流程构建完成，检查IP数量: {}").format(len(check_ips)))

    return sub_pipeline.build_sub_process(sub_name=sub_flow_name)
