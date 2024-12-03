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
import logging.config
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import MYSQL_DATA_RESTORE_TIME
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.get_binlog_backup import get_backup_binlog
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBinlogFailedException
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import (
    MySQLDownloadBackupfileComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent as MySQLTransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadBackupFileKwargs, ExecActuatorKwargs, P2PFileKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")


def rollback_remote_and_time(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    mysql 定点回档类型 远程备份文件+指定时间
    @param root_id: flow 流程root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info: 关联的cluster对象
    """
    cluster_info["recover_binlog"] = True
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))
    backupinfo = copy.deepcopy(cluster_info["backupinfo"])
    cluster_info["backup_time"] = backupinfo["backup_time"]
    task_files = [{"file_name": i} for i in backupinfo["file_list"]]
    cluster_info["task_files"] = task_files

    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        cluster_type=cluster_info["cluster_type"],
        cluster=cluster_info,
        job_timeout=MYSQL_DATA_RESTORE_TIME,
    )

    exec_act_kwargs.cluster = cluster_info
    task_ids = [i["task_id"] for i in backupinfo["file_list_details"]]
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        task_ids=task_ids,
        dest_ip=cluster_info["rollback_ip"],
        dest_dir=cluster_info["file_target_path"],
        reason="mysql rollback data",
    )
    sub_pipeline.add_act(
        act_name=_("下载定点恢复的全库备份介质到{}").format(cluster_info["rollback_ip"]),
        act_component_code=MySQLDownloadBackupfileComponent.code,
        kwargs=asdict(download_kwargs),
    )

    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之恢复数据{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    )
    backup_time = str2datetime(backupinfo["backup_time"])
    rollback_time = str2datetime(cluster_info["rollback_time"])
    binlog_result = get_backup_binlog(
        cluster_id=cluster_info["cluster_id"],
        start_time=backup_time,
        end_time=rollback_time,
        binlog_info=backupinfo["binlog_info"],
    )
    if "query_binlog_error" in binlog_result.keys():
        raise TendbGetBinlogFailedException(message=binlog_result["query_binlog_error"])
    cluster_info.update(binlog_result)

    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        task_ids=binlog_result["binlog_task_ids"],
        dest_ip=cluster_info["rollback_ip"],
        dest_dir=cluster_info["file_target_path"],
        reason="spider node rollback binlog",
    )
    sub_pipeline.add_act(
        act_name=_("下载定点恢复的binlog到{}").format(cluster_info["rollback_ip"]),
        act_component_code=MySQLDownloadBackupfileComponent.code,
        kwargs=asdict(download_kwargs),
    )
    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_recover_binlog_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之前滚binlog{}".format(exec_act_kwargs.exec_ip)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    return sub_pipeline.build_sub_process(
        sub_name=_("{}:{}定点回滚数据 REMOTE_AND_TIME ".format(cluster_info["rollback_ip"], cluster_info["rollback_port"]))
    )


def rollback_remote_and_backupid(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    mysql 定点回档类型 远程备份+指定备份文件
    @param root_id: flow 流程root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info: 关联的cluster对象
    """
    cluster_info["recover_binlog"] = False
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))
    backupinfo = cluster_info["backupinfo"]
    task_files = [{"file_name": i} for i in backupinfo["file_list"]]
    cluster_info["task_files"] = task_files
    cluster_info["backup_time"] = backupinfo["backup_time"]

    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        cluster_type=cluster_info["cluster_type"],
        cluster=cluster_info,
        job_timeout=MYSQL_DATA_RESTORE_TIME,
    )
    task_ids = [i["task_id"] for i in backupinfo["file_list_details"]]
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        task_ids=task_ids,
        dest_ip=cluster_info["rollback_ip"],
        dest_dir=cluster_info["file_target_path"],
        reason="mysql rollback data",
    )
    sub_pipeline.add_act(
        act_name=_("下载定点恢复的全库备份介质到{}").format(cluster_info["rollback_ip"]),
        act_component_code=MySQLDownloadBackupfileComponent.code,
        kwargs=asdict(download_kwargs),
    )

    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之恢复数据{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    )
    return sub_pipeline.build_sub_process(
        sub_name=_(
            "{}:{}定点回滚数据 REMOTE_AND_BACKUPID ".format(cluster_info["rollback_ip"], cluster_info["rollback_port"])
        )
    )


def rollback_local_and_backupid(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    mysql 定点回档类型 本地备份+指定备份文件
    @param root_id: flow 流程root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info: 关联的cluster对象
    """
    cluster_info["recover_binlog"] = False
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        cluster_type=cluster_info["cluster_type"],
        cluster=cluster_info,
        job_timeout=MYSQL_DATA_RESTORE_TIME,
    )
    #  改为从本地表 local_backup_report 获取备份
    backup_info = cluster_info["backupinfo"]
    task_ids = ["{}/{}".format(backup_info["backup_dir"], i["file_name"]) for i in backup_info["file_list"]]
    if backup_info["backup_meta_file"] not in task_ids:
        task_ids.append(backup_info["backup_meta_file"])
    sub_pipeline.add_act(
        act_name=_("本地备份文件下载"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            P2PFileKwargs(
                bk_cloud_id=cluster_info["bk_cloud_id"],
                file_list=task_ids,
                file_target_path=cluster_info["file_target_path"],
                source_ip_list=[backup_info["instance_ip"]],
                exec_ip=cluster_info["rollback_ip"],
            )
        ),
    )

    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之恢复数据{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    )
    return sub_pipeline.build_sub_process(
        sub_name=_(
            "{}:{}定点回滚数据 LOCAL_AND_BACKUPID ".format(cluster_info["rollback_ip"], cluster_info["rollback_port"])
        )
    )


def rollback_local_and_time(root_id: str, ticket_data: dict, cluster_info: dict, cluster_model: Cluster):
    """
    mysql 定点回档类型 本地备份+时间
    @param root_id: 流程 root_id
    @param ticket_data: 单据输入的tick_data
    @param cluster_info:  流程信息
    @param cluster_model: 集群元数据
    @return:
    cluster: new_slave_ip,new_slave_port,master_ip,master_port,file_target_path,charset,change_master_force,backup_time
    """
    rollback_time = str2datetime(cluster_info["rollback_time"], "%Y-%m-%d %H:%M:%S")
    cluster_info["recover_binlog"] = True
    cluster_info["change_master"] = False
    backupinfo = copy.deepcopy(cluster_info["backupinfo"])

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_model.bk_cloud_id,
        cluster_type=cluster_model.cluster_type,
        cluster=cluster_info,
    )

    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    sub_pipeline.add_act(
        act_name=_("创建目录 {}".format(cluster_info["file_target_path"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 下载备份文件  backup_info["file_list"] 需要确认
    task_ids = ["{}/{}".format(backupinfo["backup_dir"], i["file_name"]) for i in backupinfo["file_list"]]
    if backupinfo["backup_meta_file"] not in task_ids:
        task_ids.append(backupinfo["backup_meta_file"])
    sub_pipeline.add_act(
        act_name=_("下载备份到{}".format(cluster_info["rollback_ip"])),
        act_component_code=MySQLTransFileComponent.code,
        kwargs=asdict(
            P2PFileKwargs(
                bk_cloud_id=cluster_model.bk_cloud_id,
                file_list=task_ids,
                file_target_path=cluster_info["file_target_path"],
                source_ip_list=[backupinfo["instance_ip"]],
                exec_ip=cluster_info["rollback_ip"],
            )
        ),
    )

    cluster_info["change_master"] = False
    exec_act_kwargs.cluster = copy.deepcopy(cluster_info)
    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.job_timeout = MYSQL_DATA_RESTORE_TIME
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
    sub_pipeline.add_act(
        act_name=_("恢复新从节点数据 {}:{}".format(exec_act_kwargs.exec_ip, cluster_info["rollback_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    )

    backup_time = str2datetime(backupinfo["backup_time"], "%Y-%m-%d %H:%M:%S")
    cluster_info["backup_time"] = backupinfo["backup_time"]
    binlog_result = get_backup_binlog(
        cluster_id=cluster_model.id,
        start_time=backup_time,
        end_time=rollback_time,
        binlog_info=backupinfo["binlog_info"],
    )
    if "query_binlog_error" in binlog_result.keys():
        raise TendbGetBinlogFailedException(message=binlog_result["query_binlog_error"])

    cluster_info.update(binlog_result)

    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster_model.bk_cloud_id,
        task_ids=binlog_result["binlog_task_ids"],
        dest_ip=cluster_info["rollback_ip"],
        dest_dir=cluster_info["file_target_path"],
        reason="rollback node rollback binlog",
        cluster=cluster_info,
    )
    sub_pipeline.add_act(
        act_name=_("下载定点恢复的binlog到{}").format(cluster_info["rollback_ip"]),
        act_component_code=MySQLDownloadBackupfileComponent.code,
        kwargs=asdict(download_kwargs),
    )
    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_recover_binlog_payload.__name__
    exec_act_kwargs.cluster = copy.deepcopy(cluster_info)
    sub_pipeline.add_act(
        act_name=_("定点恢复之前滚binlog{}".format(exec_act_kwargs.exec_ip)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    return sub_pipeline.build_sub_process(
        sub_name=_("用本地备份恢复数据{}:{}".format(exec_act_kwargs.exec_ip, cluster_info["rollback_port"]))
    )
