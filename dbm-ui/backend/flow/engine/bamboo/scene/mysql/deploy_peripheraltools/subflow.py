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

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.cc_trans_module import cc_trans_module
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.clusters_detail_helper import (
    clusters_detail_ips,
    is_empty_clusters_detail,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.collect_sysinfo import collect_sysinfo
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    ALLDEPARTS,
    DeployPeripheralToolsDepart,
    remove_depart,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.instance_standardize import instance_standardize
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.prepare_departs_binary import prepare_departs_binary
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.push_config import (
    push_departs_config,
    push_mysql_crond_config,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.trans_files import trans_common_files


def standardize_mysql_cluster_subflow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,
    cluster_type: ClusterType,
    clusters_detail: Dict[str, Dict[str, List[str]]],
    departs: List[DeployPeripheralToolsDepart] = ALLDEPARTS,
    with_deploy_binary: bool = True,
    with_push_config: bool = True,
    with_collect_sysinfo: bool = True,
    with_actuator: bool = True,
    with_bk_plugin: bool = True,
    with_cc_standardize: bool = True,
    with_instance_standardize: bool = True,
) -> SubProcess:
    """
    cluster_details: {
      "single.test.db": {
        "proxy": ["1.1.1.1:1000", "2.2.2.2:20000"],
        "storage": [...],
        }
    }
    """
    departs = copy.deepcopy(departs)

    pipe = SubBuilder(root_id=root_id, data=data)

    # 下发公共文件, actuator, bk plugin, backup client
    if not is_empty_clusters_detail(clusters_detail) and (
        with_actuator or with_bk_plugin or DeployPeripheralToolsDepart.BackupClient in departs
    ):
        pipe.add_sub_pipeline(
            sub_flow=trans_common_files(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=bk_biz_id,
                ips=clusters_detail_ips(clusters_detail),
                with_actuator=with_actuator,
                with_bk_plugin=with_bk_plugin,
                with_backup_client=DeployPeripheralToolsDepart.BackupClient in departs,
            )
        )

    remove_depart(DeployPeripheralToolsDepart.BackupClient, departs)

    # 收集系统信息, 比如 glibc 版本
    if with_collect_sysinfo and not is_empty_clusters_detail(clusters_detail):
        pipe.add_sub_pipeline(
            sub_flow=collect_sysinfo(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                ips=clusters_detail_ips(clusters_detail),
            )
        )

    # cc 模块标准化, 推送 exporter 配置
    if with_cc_standardize and not is_empty_clusters_detail(clusters_detail):
        pipe.add_sub_pipeline(
            sub_flow=cc_trans_module(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                cluster_type=cluster_type,
                cluster_details=clusters_detail,
            )
        )

    if with_deploy_binary and not is_empty_clusters_detail(clusters_detail):
        pipe.add_sub_pipeline(
            sub_flow=prepare_departs_binary(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                cluster_type=cluster_type,
                cluster_details=clusters_detail,
                departs=departs,
            )
        )

    if with_instance_standardize and not is_empty_clusters_detail(clusters_detail):
        pipe.add_sub_pipeline(
            sub_flow=instance_standardize(
                root_id=root_id,
                data=data,
                bk_cloud_id=bk_cloud_id,
                cluster_type=cluster_type,
                cluster_details=clusters_detail,
            )
        )

    if (
        with_push_config
        and {
            DeployPeripheralToolsDepart.MySQLDBBackup,
            DeployPeripheralToolsDepart.MySQLRotateBinlog,
            DeployPeripheralToolsDepart.MySQLMonitor,
            DeployPeripheralToolsDepart.MySQLTableChecksum,
            DeployPeripheralToolsDepart.MySQLCrond,
        }
        & set(departs)
        and not is_empty_clusters_detail(clusters_detail)
    ):
        if DeployPeripheralToolsDepart.MySQLCrond in departs:
            remove_depart(DeployPeripheralToolsDepart.MySQLCrond, departs)
            pipe.add_sub_pipeline(
                sub_flow=push_mysql_crond_config(
                    root_id=root_id,
                    data=data,
                    bk_cloud_id=bk_cloud_id,
                    bk_biz_id=bk_biz_id,
                    ips=clusters_detail_ips(clusters_detail),
                )
            )

        sf = push_departs_config(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            bk_biz_id=bk_biz_id,
            cluster_type=cluster_type,
            cluster_details=clusters_detail,
            departs=departs,
        )
        if sf:
            pipe.add_sub_pipeline(sub_flow=sf)

    return pipe.build_sub_process(sub_name=_("{} 集群标准化".format(cluster_type)))
