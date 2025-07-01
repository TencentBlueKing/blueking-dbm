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
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import MYSQL_DATA_RESTORE_TIME, DBType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import MysqlChangeMasterType, TendbSingleRestoreEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import (
    MySQLDownloadBackupfileComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent as MySQLTransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DownloadBackupFileKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    P2PFileKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def restore_single_remote_sub_flow(root_id: str, ticket_data: dict, cluster: dict):
    """
    tendb single 迁移。(只做流程,元数据请在主流程控制)
    @param root_id:  flow流程的root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster:  关联的cluster对象
    """
    backup_info = cluster["backupinfo"]
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=int(cluster["bk_cloud_id"]), cluster_type=ClusterType.TenDBCluster, cluster=cluster
    )
    # 1. 创建恢复目录
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
    exec_act_kwargs.exec_ip = [cluster["new_orphan_ip"]]
    sub_pipeline.add_act(
        act_name=_("创建目录 {}".format(cluster["file_target_path"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    # 2.下发dbactor
    sub_pipeline.add_act(
        act_name=_("下发db-actor到节点"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=int(cluster["bk_cloud_id"]),
                exec_ip=[cluster["new_orphan_ip"]],
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )
    # 3. 下载备份文件
    if cluster["orphan_restore_type"] in [
        TendbSingleRestoreEnum.LocalBackupAndData,
        TendbSingleRestoreEnum.LocalBackupAndSchema,
    ]:
        # 从原节点点对点传输备份文件
        task_ids = ["{}/{}".format(backup_info["backup_dir"], i["file_name"]) for i in backup_info["file_list"]]
        if backup_info["backup_meta_file"] not in task_ids:
            task_ids.append(backup_info["backup_meta_file"])
        sub_pipeline.add_act(
            act_name=_("本地备份文件下载"),
            act_component_code=MySQLTransFileComponent.code,
            kwargs=asdict(
                P2PFileKwargs(
                    bk_cloud_id=cluster["bk_cloud_id"],
                    file_list=task_ids,
                    file_target_path=cluster["file_target_path"],
                    source_ip_list=[backup_info["instance_ip"]],
                    exec_ip=[cluster["new_orphan_ip"]],
                )
            ),
        )
    else:
        # 从远程下载备份文件
        task_ids = [i["task_id"] for i in backup_info["file_list_details"]]
        download_kwargs = DownloadBackupFileKwargs(
            bk_cloud_id=cluster["bk_cloud_id"],
            task_ids=task_ids,
            dest_ip=cluster["new_orphan_ip"],
            dest_dir=cluster["file_target_path"],
            reason="single node sync data",
        )
        sub_pipeline.add_act(
            act_name=_("下载全库备份介质到 {}".format(cluster["new_orphan_ip"])),
            act_component_code=MySQLDownloadBackupfileComponent.code,
            kwargs=asdict(download_kwargs),
        )

    # 4. 恢复数据到新的节点
    cluster["restore_ip"] = cluster["new_orphan_ip"]
    cluster["restore_port"] = cluster["new_orphan_port"]
    cluster["source_ip"] = cluster["orphan_ip"]
    cluster["source_port"] = cluster["orphan_port"]
    cluster["change_master"] = False
    exec_act_kwargs.exec_ip = cluster["new_orphan_ip"]
    exec_act_kwargs.job_timeout = MYSQL_DATA_RESTORE_TIME
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_restore_remotedb_payload.__name__
    sub_pipeline.add_act(
        act_name=_("恢复新节点数据 {}:{}".format(exec_act_kwargs.exec_ip, cluster["restore_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    ),

    if cluster["binlog_sync"]:
        # 6. 如果需要建立实时同步主库数据。搭建数据同步链路
        sub_pipeline.add_act(
            act_name=_("下发db-actor到节点"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=int(cluster["bk_cloud_id"]),
                    exec_ip=[cluster["orphan_ip"]],
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        cluster["target_ip"] = cluster["orphan_ip"]
        cluster["target_port"] = cluster["orphan_port"]
        cluster["repl_ip"] = cluster["new_orphan_ip"]
        exec_act_kwargs.cluster = copy.deepcopy(cluster)
        exec_act_kwargs.exec_ip = cluster["orphan_ip"]
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_grant_remotedb_repl_user.__name__
        sub_pipeline.add_act(
            act_name=_("新增repl帐户{}".format(exec_act_kwargs.exec_ip)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        cluster["repl_ip"] = cluster["new_orphan_ip"]
        cluster["repl_port"] = cluster["new_orphan_port"]
        cluster["target_ip"] = cluster["orphan_ip"]
        cluster["target_port"] = cluster["orphan_port"]
        cluster["change_master_type"] = MysqlChangeMasterType.BACKUPFILE.value
        exec_act_kwargs.cluster = copy.deepcopy(cluster)
        exec_act_kwargs.exec_ip = cluster["new_orphan_ip"]
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_remotedb_change_master.__name__
        sub_pipeline.add_act(
            act_name=_("建立主从关系:新主库指向旧主库 {}:{}".format(exec_act_kwargs.exec_ip, cluster["repl_port"])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
    return sub_pipeline.build_sub_process(sub_name=_("single节点迁移数据子流程{}".format(exec_act_kwargs.exec_ip)))
