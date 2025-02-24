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
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.cc_trans_module import cc_trans_module
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.collect_sysinfo import collect_sysinfo
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    DeployPeripheralToolsDepart,
    remove_depart,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.group_ips import group_ips
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
    bk_biz_id: int,
    cluster_type: ClusterType,
    cluster_ids: List[int],
    departs: List[DeployPeripheralToolsDepart],
    with_deploy_binary: bool = True,
    with_push_config: bool = True,
    with_collect_sysinfo: bool = True,
    with_actuator: bool = True,
    with_bk_plugin: bool = True,
    with_cc_standardize: bool = True,
    with_instance_standardize: bool = True,
) -> SubProcess:
    """
    ToDo dbm-ui/backend/flow/views/mysql_push_peripheral_config.py 和这个相关的代码废弃
    proxy_group, storage_group 的结构是
    {
      bk_cloud_id: {
        ip: [port list]
      }
    }
    """
    # TenDBSingle 不需要校验
    if cluster_type == ClusterType.TenDBSingle:
        remove_depart(DeployPeripheralToolsDepart.MySQLTableChecksum, departs)

    cluster_objects = Cluster.objects.filter(
        pk__in=cluster_ids, cluster_type=cluster_type, bk_biz_id=bk_biz_id
    ).prefetch_related(
        "proxyinstance_set", "storageinstance_set", "proxyinstance_set__machine", "storageinstance_set__machine"
    )

    proxy_group, storage_group = group_ips(cluster_objects=list(cluster_objects))

    pipe = SubBuilder(root_id=root_id, data=data)

    pipe.add_sub_pipeline(
        sub_flow=trans_common_files(
            root_id=root_id,
            data=data,
            bk_biz_id=bk_biz_id,
            proxy_group=proxy_group,
            storage_group=storage_group,
            with_actuator=with_actuator,
            with_bk_plugin=with_bk_plugin,
            with_backup_client=DeployPeripheralToolsDepart.BackupClient in departs,
        )
    )

    if with_collect_sysinfo:
        pipe.add_sub_pipeline(
            sub_flow=collect_sysinfo(
                root_id=root_id,
                data=data,
                proxy_group=proxy_group,
                storage_group=storage_group,
            )
        )

    remove_depart(DeployPeripheralToolsDepart.BackupClient, departs)

    # 如果是 TenDBSingle, proxy_group 为空, cc_trans_module 内部也不会构造 proxy 子流程
    if with_cc_standardize:
        pipe.add_sub_pipeline(
            sub_flow=cc_trans_module(
                root_id=root_id,
                data=data,
                cluster_type=cluster_type,
                cluster_objects=list(cluster_objects),
                proxy_group=proxy_group,
                storage_group=storage_group,
            )
        )

    if with_deploy_binary:
        # 如果是 TenDBSingle, proxy_group 为空, prepare_departs_binary 内部也不会构造 proxy 子流程
        pipe.add_sub_pipeline(
            sub_flow=prepare_departs_binary(
                root_id=root_id,
                data=data,
                cluster_type=cluster_type,
                departs=departs,
                proxy_cloud_ip_list={k: list(v.keys()) for k, v in proxy_group.items()},
                storage_cloud_ip_list={k: list(v.keys()) for k, v in storage_group.items()},
            )
        )

    # 实例标准化
    # TenDBHA proxy 会 1) 清理旧 crontab, 2) 确认添加 DBHA 白名单
    # 其他实例会 1) 清理旧 crontab, 2) 清理旧系统账号, 3) 新系统库表初始化
    # 这个不需要按集群来, 每台机器把端口下发下去执行就行
    if with_instance_standardize:
        pipe.add_sub_pipeline(
            sub_flow=instance_standardize(
                root_id=root_id,
                data=data,
                cluster_type=cluster_type,
                proxy_group=proxy_group,
                storage_group=storage_group,
            )
        )

    if with_push_config and {
        DeployPeripheralToolsDepart.MySQLDBBackup,
        DeployPeripheralToolsDepart.MySQLRotateBinlog,
        DeployPeripheralToolsDepart.MySQLMonitor,
        DeployPeripheralToolsDepart.MySQLTableChecksum,
        DeployPeripheralToolsDepart.MySQLCrond,
    } & set(departs):
        # mysql-crond 要提前独立做, 按机器
        if DeployPeripheralToolsDepart.MySQLCrond in departs:
            remove_depart(DeployPeripheralToolsDepart.MySQLCrond, departs)
            pipe.add_sub_pipeline(
                sub_flow=push_mysql_crond_config(
                    root_id=root_id,
                    data=data,
                    bk_biz_id=bk_biz_id,
                    proxy_group=proxy_group,
                    storage_group=storage_group,
                )
            )
        # 如果是 TenDBSingle, proxy_group 为空, push_departs_config 内部也不会构造 proxy 子流程
        pipe.add_sub_pipeline(
            sub_flow=push_departs_config(
                root_id=root_id, data=data, cluster_objects=list(cluster_objects), departs=departs
            )
        )

    return pipe.build_sub_process(sub_name=_("{} 集群标准化".format(cluster_type)))
