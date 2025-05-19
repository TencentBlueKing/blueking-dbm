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
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, List, Optional

from bamboo_engine.builder import SubProcess
from deprecated import deprecated
from django.utils.translation import ugettext as _

from backend.db_meta.enums import AccessLayer, ClusterMachineAccessTypeDefine, ClusterType, MachineType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.clusters_detail_helper import (
    clusters_detail_ip_ports_by_access_layer,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    DeployPeripheralToolsDepart,
    remove_depart,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


@deprecated
def push_mysql_crond_config(
    root_id: str,
    data: Dict,
    bk_cloud_id,
    bk_biz_id: int,
    ips: List[str],
) -> SubProcess:
    """
    按机器独立推送 mysql-crond 配置
    """
    acts = []

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


@deprecated
def push_departs_config(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,
    cluster_type: ClusterType,
    cluster_details: Dict,
    departs: List[DeployPeripheralToolsDepart],
) -> Optional[SubProcess | None]:
    """
    按集群推送配置
    """
    pipes = []
    for immute_domain, cluster_detail in cluster_details.items():
        p = push_departs_config_for_cluster(
            root_id=root_id,
            data=data,
            bk_biz_id=bk_biz_id,
            bk_cloud_id=bk_cloud_id,
            cluster_type=cluster_type,
            immute_domain=immute_domain,
            cluster_detail=cluster_detail,
            departs=departs,
        )
        if p:
            pipes.append(p)

    if pipes:
        sp = SubBuilder(root_id=root_id, data=data)
        sp.add_parallel_sub_pipeline(sub_flow_list=pipes)
        return sp.build_sub_process(sub_name=_("推送周边工具配置"))

    return None


@deprecated
def push_departs_config_for_cluster(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,
    cluster_type: ClusterType,
    immute_domain: str,
    cluster_detail: Dict[str, List[str]],
    departs: List[DeployPeripheralToolsDepart],
) -> Optional[SubProcess | None]:
    """
    集群内同机器上的多实例按机器推送
    """
    proxy_ip_port_dict, storage_ip_port_dict = clusters_detail_ip_ports_by_access_layer({"": cluster_detail})

    pipes = []

    if storage_ip_port_dict:
        p = push_departs_config_for_cluster_ips(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            bk_biz_id=bk_biz_id,
            cluster_type=cluster_type,
            immute_domain=immute_domain,
            ip_ports=storage_ip_port_dict,
            departs=departs,
            machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.STORAGE],
        )
        if p:
            pipes.append(p)

    # TenDBSingle 没有 proxy, 不用跑这个分支
    # 但是有人提过想要有 proxy 的 TenDBSingle
    if cluster_type != ClusterType.TenDBSingle and proxy_ip_port_dict:
        departs_on_proxy = deepcopy(departs)
        # 接入层不跑校验, 强制删除
        remove_depart(DeployPeripheralToolsDepart.MySQLTableChecksum, departs_on_proxy)
        remove_depart(DeployPeripheralToolsDepart.MySQLRotateBinlog, departs_on_proxy)

        if cluster_type == ClusterType.TenDBHA:
            # proxy 不 rotate 和 备份
            remove_depart(DeployPeripheralToolsDepart.MySQLDBBackup, departs_on_proxy)

        logger.info("{} proxy push departs config {}".format(cluster_type, departs_on_proxy))

        # 接入层组件配置推送
        if {
            DeployPeripheralToolsDepart.MySQLDBBackup,
            DeployPeripheralToolsDepart.MySQLRotateBinlog,
            DeployPeripheralToolsDepart.MySQLMonitor,
        } & set(departs_on_proxy):
            p = push_departs_config_for_cluster_ips(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=bk_biz_id,
                cluster_type=cluster_type,
                immute_domain=immute_domain,
                ip_ports=proxy_ip_port_dict,
                departs=departs_on_proxy,
                machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.PROXY],
            )
            if p:
                pipes.append(p)

    if pipes:
        sp = SubBuilder(root_id=root_id, data=data)
        sp.add_parallel_sub_pipeline(sub_flow_list=pipes)
        return sp.build_sub_process(sub_name=_(f"{immute_domain}"))

    return None


@deprecated
def push_departs_config_for_cluster_ips(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,
    cluster_type: ClusterType,
    immute_domain: str,
    ip_ports: Dict[str, List[int]],
    departs: List[DeployPeripheralToolsDepart],
    machine_type: MachineType,
) -> Optional[None | SubProcess]:
    pipes = []
    for ip, port_list in ip_ports.items():
        acts = make_push_departs_config_for_ip(
            bk_cloud_id=bk_cloud_id,
            bk_biz_id=bk_biz_id,
            cluster_type=cluster_type,
            immute_domain=immute_domain,
            ip=ip,
            port_list=port_list,
            departs=departs,
            machine_type=machine_type,
        )

        if acts:
            pipe = SubBuilder(root_id=root_id, data=data)
            for act in acts:
                pipe.add_act(**act)

            pipes.append(pipe.build_sub_process(sub_name=_(f"{ip}:{port_list}")))

    if pipes:
        sp = SubBuilder(root_id=root_id, data=data)
        sp.add_parallel_sub_pipeline(sub_flow_list=pipes)
        return sp.build_sub_process(sub_name=_(f"{machine_type}"))

    return None


@deprecated
def make_push_departs_config_for_ip(
    bk_cloud_id,
    bk_biz_id: int,
    cluster_type: ClusterType,
    immute_domain: str,
    ip: str,
    port_list: List[int],
    departs: List[DeployPeripheralToolsDepart],
    machine_type: MachineType,
) -> List:
    """
    这肯定是同一个集群的, 所以配置只会有端口差异
    """

    acts = []

    # 不再区别对待运维节点, 在 pay load 种会硬编码假数据
    if DeployPeripheralToolsDepart.MySQLMonitor in departs:
        acts.append(
            make_push_mysql_monitor_config_act(
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=bk_biz_id,
                cluster_type=cluster_type,
                immute_domain=immute_domain,
                ip=ip,
                port_list=port_list,
                machine_type=machine_type,
            )
        )

    if DeployPeripheralToolsDepart.MySQLDBBackup in departs:
        acts.append(
            make_push_mysql_dbbackup_config_act(
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=bk_biz_id,
                cluster_type=cluster_type,
                immute_domain=immute_domain,
                ip=ip,
                port_list=port_list,
                machine_type=machine_type,
            )
        )

    if DeployPeripheralToolsDepart.MySQLTableChecksum in departs:
        acts.append(
            make_push_mysql_table_checksum_config_act(
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=bk_biz_id,
                cluster_type=cluster_type,
                immute_domain=immute_domain,
                ip=ip,
                port_list=port_list,
            )
        )
    if DeployPeripheralToolsDepart.MySQLRotateBinlog in departs:
        acts.append(
            make_push_mysql_rotatebinlog_config_act(
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=bk_biz_id,
                cluster_type=cluster_type,
                immute_domain=immute_domain,
                ip=ip,
                port_list=port_list,
            )
        )

    return acts


@deprecated
def make_push_mysql_monitor_config_act(
    bk_cloud_id,
    bk_biz_id: int,
    cluster_type: ClusterType,
    immute_domain: str,
    ip: str,
    port_list: List[int],
    machine_type: MachineType,
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
                    "bk_biz_id": bk_biz_id,
                    "cluster_type": cluster_type,
                    "immute_domain": immute_domain,
                    "machine_type": machine_type,
                },
                bk_cloud_id=bk_cloud_id,
            )
        ),
    }


@deprecated
def make_push_mysql_dbbackup_config_act(
    bk_cloud_id,
    bk_biz_id: int,
    cluster_type: ClusterType,
    immute_domain: str,
    ip: str,
    port_list: List[int],
    machine_type: MachineType,
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
                    "bk_biz_id": bk_biz_id,
                    "immute_domain": immute_domain,
                    "machine_type": machine_type,
                    "cluster_type": cluster_type,
                    # "db_module_id": cluster_obj.db_module_id,
                    # "cluster_id": cluster_obj.pk,
                },
                bk_cloud_id=bk_cloud_id,
            )
        ),
    }


@deprecated
def make_push_mysql_rotatebinlog_config_act(
    bk_cloud_id, bk_biz_id: int, cluster_type: ClusterType, immute_domain: str, ip: str, port_list: List[int]
) -> Dict:
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
                    "bk_biz_id": bk_biz_id,
                    "immute_domain": immute_domain,
                    "cluster_type": cluster_type,
                },
                bk_cloud_id=bk_cloud_id,
            )
        ),
    }


@deprecated
def make_push_mysql_table_checksum_config_act(
    bk_cloud_id, bk_biz_id: int, cluster_type: ClusterType, immute_domain: str, ip: str, port_list: List[int]
) -> Dict:
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
                    "bk_biz_id": bk_biz_id,
                    "immute_domain": immute_domain,
                    "cluster_type": cluster_type,
                },
                bk_cloud_id=bk_cloud_id,
            )
        ),
    }


def gen_reload_departs_config(
    root_id: str, data: Dict, bk_cloud_id: int, instances: List[str], departs: List[DeployPeripheralToolsDepart]
) -> SubProcess:
    ip_ports_dict = defaultdict(list)
    for inst in instances:
        ip, port = inst.split(":")
        ip_ports_dict[ip].append(int(port))

    ipsubs = []
    for ip, ports in ip_ports_dict.items():
        ipsub = SubBuilder(root_id=root_id, data=data)
        ipsub.add_act(
            act_name=_("生成配置: {}".format([d.value for d in departs])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=[ip],
                    run_as_system_user=DBA_ROOT_USER,
                    payload_class=PeripheralToolsPayload.payload_class_path(),
                    get_mysql_payload_func=PeripheralToolsPayload.gen_config.__name__,
                    bk_cloud_id=bk_cloud_id,
                    cluster={"ports": ports, "departs": departs},
                )
            ),
        )
        ipsub.add_act(
            act_name=_("重载配置: {}".format([d.value for d in departs])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=[ip],
                    bk_cloud_id=bk_cloud_id,
                    run_as_system_user=DBA_ROOT_USER,
                    payload_class=PeripheralToolsPayload.payload_class_path(),
                    get_mysql_payload_func=PeripheralToolsPayload.reload_config.__name__,
                    cluster={"ports": ports, "departs": departs},
                )
            ),
        )

        ipsubs.append(ipsub.build_sub_process(sub_name="{}:{}".format(ip, ports)))

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_sub_pipeline(sub_flow_list=ipsubs)
    return sp.build_sub_process(sub_name=_("推送加载 {} 配置".format(departs)))
