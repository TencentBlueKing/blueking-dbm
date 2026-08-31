# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing terms of the License.
"""
from dataclasses import asdict
from typing import List, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.push_config import gen_reload_departs_config
from backend.flow.engine.bamboo.scene.mysql.dts.subflow_common import build_master_addr
from backend.flow.plugins.components.collections.mysql.dts.deploy.cc_standardize import MysqlDtsCcStandardizeComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload
from backend.flow.utils.mysql.dts.monitor_config import get_dts_monitor_media, group_monitor_roles
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs

_DTS_MONITOR_DEPARTS = [
    DeployPeripheralToolsDepart.MySQLCrond,
    DeployPeripheralToolsDepart.MySQLMonitor,
]


def _resolve_monitor_context(
    *,
    cluster_name: str,
    master_nodes: Optional[List[dict]],
    worker_nodes: Optional[List[dict]],
    dts_cluster_id: Optional[int],
    dts_master_addr: str,
) -> tuple[list[dict], list[dict], str, str]:
    masters = list(master_nodes or [])
    workers = list(worker_nodes or [])
    name = cluster_name or ""
    addr = dts_master_addr or ""
    if dts_cluster_id and (not masters or not workers or not name or not addr):
        from backend.db_meta.models import MysqlDtsCluster

        cluster = MysqlDtsCluster.objects.filter(id=dts_cluster_id).first()
        if cluster:
            masters = masters or list(cluster.master_nodes or [])
            workers = workers or list(cluster.worker_nodes or [])
            name = name or cluster.name
            addr = addr or cluster.master_addr
    if not addr and masters:
        addr = build_master_addr(masters)
    return masters, workers, name, addr


def _add_dts_monitor_acts(
    sub: SubBuilder,
    *,
    root_id: str,
    data: dict,
    bk_cloud_id: int,
    master_nodes: List[dict],
    worker_nodes: List[dict],
) -> None:
    by_ip = group_monitor_roles(master_nodes, worker_nodes)
    if not by_ip:
        return
    monitor_files, _crond_name, _monitor_name = get_dts_monitor_media()
    actuator_files = GetFileList(db_type=DBType.MySQL).get_db_actuator_package()
    ips = list(by_ip.keys())
    sub.add_act(
        act_name=_("下发 DTS 监控介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=ips,
                file_list=actuator_files + monitor_files,
                file_target_path="/data/install",
            )
        ),
    )
    deploy_acts = []
    for ip in ips:
        deploy_acts.append(
            {
                "act_name": _("部署监控二进制 {}").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=[ip],
                        run_as_system_user=DBA_ROOT_USER,
                        payload_class=PeripheralToolsPayload.payload_class_path(),
                        get_mysql_payload_func=PeripheralToolsPayload.deploy_binary.__name__,
                        bk_cloud_id=bk_cloud_id,
                        cluster={"departs": _DTS_MONITOR_DEPARTS},
                    )
                ),
            }
        )
    if deploy_acts:
        sub.add_parallel_acts(acts_list=deploy_acts)

    instances = [f"{ip}:{role['port']}" for ip, rec in by_ip.items() for role in rec["roles"]]
    sub.add_sub_pipeline(
        sub_flow=gen_reload_departs_config(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            instances=instances,
            departs=[DeployPeripheralToolsDepart.MySQLCrond],
        )
    )
    sub.add_sub_pipeline(
        sub_flow=gen_reload_departs_config(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            instances=instances,
            departs=[DeployPeripheralToolsDepart.MySQLMonitor],
        )
    )


def mysql_dts_cc_standardize_subflow(
    *,
    root_id: str,
    bk_biz_id: int,
    bk_cloud_id: int,
    cluster_name: str = "",
    master_nodes: Optional[List[dict]] = None,
    worker_nodes: Optional[List[dict]] = None,
    dts_cluster_id: Optional[int] = None,
    creator: str = "",
    dts_master_addr: str = "",
) -> SubBuilder:
    """DTS 标准化：CC 挪机后按官方三拍部署 mysql-crond / mysql-monitor。"""
    data = {
        "bk_biz_id": bk_biz_id,
        "bk_cloud_id": bk_cloud_id,
        "cluster_name": cluster_name,
        "uid": root_id,
        "creator": creator,
    }
    sub = SubBuilder(root_id=root_id, data=data)
    kwargs = {
        "bk_biz_id": bk_biz_id,
        "bk_cloud_id": bk_cloud_id,
        "cluster_name": cluster_name,
        "master_nodes": master_nodes or [],
        "worker_nodes": worker_nodes or [],
    }
    if dts_cluster_id is not None:
        kwargs["dts_cluster_id"] = dts_cluster_id
    sub.add_act(
        act_name=_("DTS CC 模块标准化"),
        act_component_code=MysqlDtsCcStandardizeComponent.code,
        kwargs=kwargs,
    )
    masters, workers, _name, _addr = _resolve_monitor_context(
        cluster_name=cluster_name,
        master_nodes=master_nodes,
        worker_nodes=worker_nodes,
        dts_cluster_id=dts_cluster_id,
        dts_master_addr=dts_master_addr,
    )
    _add_dts_monitor_acts(
        sub,
        root_id=root_id,
        data=data,
        bk_cloud_id=bk_cloud_id,
        master_nodes=masters,
        worker_nodes=workers,
    )
    return sub
