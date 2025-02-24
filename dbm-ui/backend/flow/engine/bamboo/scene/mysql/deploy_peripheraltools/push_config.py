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
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, List

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.db_meta.enums import AccessLayer, ClusterMachineAccessTypeDefine, ClusterType, MachineType
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    DeployPeripheralToolsDepart,
    remove_depart,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def push_mysql_crond_config(
    root_id: str, data: Dict, bk_biz_id: int, proxy_group: Dict, storage_group: Dict
) -> SubProcess:
    """
    按机器独立推送 mysql-crond 配置
    """
    acts = []
    for bk_cloud_id, ip_dicts in {
        k: {**proxy_group[k], **storage_group[k]} for k in set(list(proxy_group.keys()) + list(storage_group.keys()))
    }.items():
        ips = list(ip_dicts.keys())
        for ip in ips:
            acts.append(
                {
                    "act_name": _(f"{ip}"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            exec_ip=ip,
                            run_as_system_user=DBA_ROOT_USER,
                            get_mysql_payload_func=MysqlActPayload.push_mysql_crond_config.__name__,
                            cluster={"bk_biz_id": bk_biz_id},
                            bk_cloud_id=bk_cloud_id,
                        )
                    ),
                }
            )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_acts(acts_list=acts)
    return sp.build_sub_process(sub_name=_("推送 mysql-crond 配置"))


def push_departs_config(
    root_id: str,
    data: Dict,
    cluster_objects: List[Cluster],
    departs: List[DeployPeripheralToolsDepart],
) -> SubProcess:
    """
    按集群推送配置
    """
    pipes = []
    for cluster_obj in cluster_objects:
        pipes.append(
            push_departs_config_for_cluster(root_id=root_id, data=data, cluster_obj=cluster_obj, departs=departs)
        )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_sub_pipeline(sub_flow_list=pipes)
    return sp.build_sub_process(sub_name=_("推送周边工具配置"))


def push_departs_config_for_cluster(
    root_id: str,
    data: Dict,
    cluster_obj: Cluster,
    departs: List[DeployPeripheralToolsDepart],
) -> SubProcess:
    """
    集群内同机器上的多实例按机器推送
    """
    # 聚合机器端口
    proxy_ip_ports = defaultdict(list)
    storage_ip_ports = defaultdict(list)
    for i in cluster_obj.proxyinstance_set.all():
        proxy_ip_ports[i.machine.ip].append(i.port)
    for i in cluster_obj.storageinstance_set.all():
        storage_ip_ports[i.machine.ip].append(i.port)

    pipes = [
        # 存储机器推送所有组件配置
        push_departs_config_for_cluster_ips(
            root_id=root_id,
            data=data,
            cluster_obj=cluster_obj,
            ip_ports=storage_ip_ports,
            departs=departs,
            machine_type=ClusterMachineAccessTypeDefine[cluster_obj.cluster_type][AccessLayer.STORAGE],
        )
    ]

    # TenDBSingle 没有 proxy, 不用跑这个分支
    # 但是有人提过想要有 proxy 的 TenDBSingle
    if cluster_obj.cluster_type != ClusterType.TenDBSingle:
        departs_on_proxy = deepcopy(departs)
        # 接入层不跑校验, 强制删除
        remove_depart(DeployPeripheralToolsDepart.MySQLTableChecksum, departs_on_proxy)
        if cluster_obj.cluster_type == ClusterType.TenDBHA:
            # proxy 不 rotate 和 备份
            # spider 要, 所以不会进入这里
            remove_depart(DeployPeripheralToolsDepart.MySQLRotateBinlog, departs_on_proxy)
            remove_depart(DeployPeripheralToolsDepart.MySQLDBBackup, departs_on_proxy)

        # 接入层组件配置推送
        if {
            DeployPeripheralToolsDepart.MySQLDBBackup,
            DeployPeripheralToolsDepart.MySQLRotateBinlog,
            DeployPeripheralToolsDepart.MySQLMonitor,
        } & set(departs_on_proxy):
            pipes.append(
                push_departs_config_for_cluster_ips(
                    root_id=root_id,
                    data=data,
                    cluster_obj=cluster_obj,
                    ip_ports=proxy_ip_ports,
                    departs=departs_on_proxy,
                    machine_type=ClusterMachineAccessTypeDefine[cluster_obj.cluster_type][AccessLayer.PROXY],
                )
            )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_sub_pipeline(sub_flow_list=pipes)
    return sp.build_sub_process(sub_name=_(f"{cluster_obj.immute_domain}"))


def push_departs_config_for_cluster_ips(
    root_id: str,
    data: Dict,
    cluster_obj: Cluster,
    ip_ports: Dict[str, List[int]],
    departs: List[DeployPeripheralToolsDepart],
    machine_type: MachineType,
):
    pipes = []
    for ip, port_list in ip_ports.items():
        pipe = SubBuilder(root_id=root_id, data=data)
        # 不能并行, 不然有可能 mysql-crond 没起来导致其他任务失败
        for act in make_push_departs_config_for_ip(
            ip=ip, port_list=port_list, departs=departs, cluster_obj=cluster_obj, machine_type=machine_type
        ):
            pipe.add_act(**act)

        pipes.append(pipe.build_sub_process(sub_name=_(f"{ip}")))

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_sub_pipeline(sub_flow_list=pipes)
    return sp.build_sub_process(sub_name=_(f"{machine_type}"))


def make_push_departs_config_for_ip(
    cluster_obj: Cluster,
    ip: str,
    port_list: List[int],
    departs: List[DeployPeripheralToolsDepart],
    machine_type: MachineType,
) -> List:
    """
    这肯定是同一个集群的, 所以配置只会有端口差异
    """
    acts = []
    if DeployPeripheralToolsDepart.MySQLMonitor in departs:
        acts.append(
            make_push_mysql_monitor_config_act(
                cluster_obj=cluster_obj, ip=ip, port_list=port_list, machine_type=machine_type
            )
        ),
    if DeployPeripheralToolsDepart.MySQLDBBackup in departs:
        acts.append(
            make_push_mysql_dbbackup_config_act(
                cluster_obj=cluster_obj, ip=ip, port_list=port_list, machine_type=machine_type
            )
        ),
    if DeployPeripheralToolsDepart.MySQLTableChecksum in departs:
        acts.append(make_push_mysql_table_checksum_config_act(cluster_obj=cluster_obj, ip=ip, port_list=port_list))
    if DeployPeripheralToolsDepart.MySQLRotateBinlog in departs:
        acts.append(make_push_mysql_rotatebinlog_config_act(cluster_obj=cluster_obj, ip=ip, port_list=port_list))

    return acts


def make_push_mysql_monitor_config_act(
    cluster_obj: Cluster, ip: str, port_list: List[int], machine_type: MachineType
) -> Dict:
    """
    每个端口都有独立配置, 需要端口信息
    这些端口肯定属于同一个集群
    """
    return {
        "act_name": DeployPeripheralToolsDepart.MySQLMonitor,
        "act_component_code": ExecuteDBActuatorScriptComponent.code,
        "kwargs": asdict(
            ExecActuatorKwargs(
                exec_ip=ip,
                run_as_system_user=DBA_ROOT_USER,
                get_mysql_payload_func=MysqlActPayload.push_mysql_monitor_config.__name__,
                cluster={
                    "port_list": port_list,
                    "bk_biz_id": cluster_obj.bk_biz_id,
                    "immute_domain": cluster_obj.immute_domain,
                    "machine_type": machine_type,
                    "db_module_id": cluster_obj.db_module_id,
                    "cluster_id": cluster_obj.pk,
                },
                bk_cloud_id=cluster_obj.bk_cloud_id,
            )
        ),
    }


def make_push_mysql_dbbackup_config_act(
    cluster_obj: Cluster, ip: str, port_list: List[int], machine_type: MachineType
) -> Dict:
    """
    每个端口都有独立配置, 需要端口信息
    """
    return {
        "act_name": DeployPeripheralToolsDepart.MySQLDBBackup,
        "act_component_code": ExecuteDBActuatorScriptComponent.code,
        "kwargs": asdict(
            ExecActuatorKwargs(
                exec_ip=ip,
                run_as_system_user=DBA_ROOT_USER,
                get_mysql_payload_func=MysqlActPayload.push_mysql_dbbackup_config.__name__,
                cluster={
                    "port_list": port_list,
                    "bk_biz_id": cluster_obj.bk_biz_id,
                    "immute_domain": cluster_obj.immute_domain,
                    "machine_type": machine_type,
                    "cluster_type": cluster_obj.cluster_type,
                    "db_module_id": cluster_obj.db_module_id,
                    "cluster_id": cluster_obj.pk,
                },
                bk_cloud_id=cluster_obj.bk_cloud_id,
            )
        ),
    }


def make_push_mysql_rotatebinlog_config_act(cluster_obj: Cluster, ip: str, port_list: List[int]) -> Dict:
    """
    每个端口都有独立配置, 需要端口信息
    """
    return {
        "act_name": DeployPeripheralToolsDepart.MySQLRotateBinlog,
        "act_component_code": ExecuteDBActuatorScriptComponent.code,
        "kwargs": asdict(
            ExecActuatorKwargs(
                exec_ip=ip,
                run_as_system_user=DBA_ROOT_USER,
                get_mysql_payload_func=MysqlActPayload.push_mysql_rotatebinlog_config.__name__,
                cluster={
                    "port_list": port_list,
                    "bk_biz_id": cluster_obj.bk_biz_id,
                    "immute_domain": cluster_obj.immute_domain,
                    "cluster_type": cluster_obj.cluster_type,
                },
                bk_cloud_id=cluster_obj.bk_cloud_id,
            )
        ),
    }


def make_push_mysql_table_checksum_config_act(cluster_obj: Cluster, ip: str, port_list: List[int]) -> Dict:
    """
    每个端口都有独立配置, 需要端口信息
    """
    return {
        "act_name": DeployPeripheralToolsDepart.MySQLTableChecksum,
        "act_component_code": ExecuteDBActuatorScriptComponent.code,
        "kwargs": asdict(
            ExecActuatorKwargs(
                exec_ip=ip,
                run_as_system_user=DBA_ROOT_USER,
                get_mysql_payload_func=MysqlActPayload.push_mysql_table_checksum_config.__name__,
                cluster={
                    "port_list": port_list,
                    "bk_biz_id": cluster_obj.bk_biz_id,
                    "immute_domain": cluster_obj.immute_domain,
                    "cluster_type": cluster_obj.cluster_type,
                },
                bk_cloud_id=cluster_obj.bk_cloud_id,
            )
        ),
    }
