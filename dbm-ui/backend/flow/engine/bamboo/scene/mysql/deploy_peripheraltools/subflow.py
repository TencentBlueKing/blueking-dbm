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
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.cc_trans_module import cc_standardize
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.collect_sysinfo import collect_sysinfo
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    ALLDEPARTS,
    DeployPeripheralToolsDepart,
    remove_departs,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.instance_standardize import standardize_instance
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.prepare_departs_binary import deploy_binary
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.push_config import gen_reload_departs_config
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.trans_files import trans_common_files


def standardize_mysql_cluster_subflow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,  # 这个参数其实根本不需要
    instances: List[str],
    departs: List[DeployPeripheralToolsDepart] = ALLDEPARTS,
    with_deploy_binary: bool = True,
    with_push_config: bool = True,
    with_collect_sysinfo: bool = True,
    with_actuator: bool = True,
    with_bk_plugin: bool = True,
    with_cc_standardize: bool = False,
    with_instance_standardize: bool = True,
    with_backup_client: bool = True,
    with_exporter_config: bool = True,
) -> SubProcess:
    """
    使用反向接口生成周边配置
    所以根本不要业务, 集群等信息
    只要知道实例地址, 去机器上执行配置生成就行
    参数输入了 bk_cloud_id, 所以隐式的约束是 instances 都是这个 bk_cloud_id
    """
    if not instances or not departs:
        # ToDo
        raise Exception  # noqa

    departs = copy.deepcopy(departs)
    ips = list(set(ele.split(":")[0] for ele in instances))

    pipe = SubBuilder(root_id=root_id, data=data)

    # 肯定会刷新 nginx 地址和实例信息
    pipe.add_sub_pipeline(
        sub_flow=trans_common_files(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            bk_biz_id=bk_biz_id,
            ips=ips,
            with_actuator=with_actuator,
            with_bk_plugin=with_bk_plugin,
            with_backup_client=with_backup_client,
        )
    )

    # departs = remove_departs(departs, DeployPeripheralToolsDepart.BackupClient)

    # 收集系统信息
    if with_collect_sysinfo:
        pipe.add_sub_pipeline(
            sub_flow=collect_sysinfo(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                ips=ips,
            )
        )

    # cc 模块标准化, 推送 exporter 配置
    if with_cc_standardize or with_exporter_config:
        pipe.add_sub_pipeline(
            sub_flow=cc_standardize(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                instances=instances,
                with_cc_standardize=with_cc_standardize,
                with_exporter_config=with_exporter_config,
            )
        )

    if with_deploy_binary:
        pipe.add_sub_pipeline(
            sub_flow=deploy_binary(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                ips=ips,
                departs=departs,
            )
        )

    if with_instance_standardize:
        pipe.add_sub_pipeline(
            sub_flow=standardize_instance(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                instances=instances,
            )
        )

    if with_push_config and {
        DeployPeripheralToolsDepart.MySQLDBBackup,
        DeployPeripheralToolsDepart.MySQLRotateBinlog,
        DeployPeripheralToolsDepart.MySQLMonitor,
        DeployPeripheralToolsDepart.MySQLTableChecksum,
        DeployPeripheralToolsDepart.MySQLCrond,
    } & set(departs):
        # toolkit 没有配置
        # exporter 的前面生成了
        departs = remove_departs(departs, DeployPeripheralToolsDepart.DBAToolKit, DeployPeripheralToolsDepart.Exporter)

        if DeployPeripheralToolsDepart.MySQLCrond in departs:
            departs = remove_departs(departs, DeployPeripheralToolsDepart.MySQLCrond)
            pipe.add_sub_pipeline(
                sub_flow=gen_reload_departs_config(
                    root_id=root_id,
                    data=data,
                    bk_cloud_id=bk_cloud_id,
                    instances=instances,
                    departs=[DeployPeripheralToolsDepart.MySQLCrond],
                )
            )

        pipe.add_sub_pipeline(
            sub_flow=gen_reload_departs_config(
                root_id=root_id, data=data, bk_cloud_id=bk_cloud_id, instances=instances, departs=departs
            )
        )

    return pipe.build_sub_process(sub_name=_("标准化"))


def standardize_mysql_cluster_by_ip_subflow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,  # 这个参数其实根本不需要
    ips: List[str],
    departs: List[DeployPeripheralToolsDepart] = ALLDEPARTS,
    with_deploy_binary: bool = True,
    with_push_config: bool = True,
    with_collect_sysinfo: bool = True,
    with_actuator: bool = True,
    with_bk_plugin: bool = True,
    with_cc_standardize: bool = False,
    with_instance_standardize: bool = True,
    with_backup_client: bool = True,
) -> SubProcess:
    instances = [
        ele.ip_port for ele in StorageInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip__in=ips)
    ]
    instances.extend(
        [ele.ip_port for ele in ProxyInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip__in=ips)]
    )
    return standardize_mysql_cluster_subflow(
        root_id=root_id,
        data=data,
        bk_cloud_id=bk_cloud_id,
        bk_biz_id=bk_biz_id,
        instances=list(set(instances)),
        departs=departs,
        with_deploy_binary=with_deploy_binary,
        with_push_config=with_push_config,
        with_collect_sysinfo=with_collect_sysinfo,
        with_actuator=with_actuator,
        with_bk_plugin=with_bk_plugin,
        with_cc_standardize=with_cc_standardize,
        with_instance_standardize=with_instance_standardize,
        with_backup_client=with_backup_client,
    )


def standardize_mysql_cluster_by_cluster_subflow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,  # 这个参数其实根本不需要
    cluster_ids: List[int],
    departs: List[DeployPeripheralToolsDepart] = ALLDEPARTS,
    with_deploy_binary: bool = True,
    with_push_config: bool = True,
    with_collect_sysinfo: bool = True,
    with_actuator: bool = True,
    with_bk_plugin: bool = True,
    with_cc_standardize: bool = False,
    with_instance_standardize: bool = True,
) -> SubProcess:
    instances = []
    for cluster_obj in Cluster.objects.filter(bk_cloud_id=bk_cloud_id, pk__in=cluster_ids):
        instances.extend([e.ip_port for e in cluster_obj.storageinstance_set.all()])
        instances.extend([e.ip_port for e in cluster_obj.proxyinstance_set.all()])

    if with_cc_standardize:
        d = {
            **copy.deepcopy(data),
            "cluster_ids": cluster_ids,
        }
        data = d

    return standardize_mysql_cluster_subflow(
        root_id=root_id,
        data=data,
        bk_cloud_id=bk_cloud_id,
        bk_biz_id=bk_biz_id,
        instances=list(set(instances)),
        departs=departs,
        with_deploy_binary=with_deploy_binary,
        with_push_config=with_push_config,
        with_collect_sysinfo=with_collect_sysinfo,
        with_actuator=with_actuator,
        with_bk_plugin=with_bk_plugin,
        with_cc_standardize=with_cc_standardize,
        with_instance_standardize=with_instance_standardize,
    )
