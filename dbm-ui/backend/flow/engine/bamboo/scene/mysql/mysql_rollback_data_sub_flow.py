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

from backend.configuration.constants import DBType
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import TenDBGetBackupInfoFailedException
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBackupInfoFailedException
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import (
    MySQLDownloadBackupfileComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_rollback_data_download_binlog import (
    MySQLRollbackDownloadBinlogComponent,
)
from backend.flow.plugins.components.collections.mysql.rollback_local_trans_flies import (
    RollBackLocalTransFileComponent,
)
from backend.flow.plugins.components.collections.mysql.rollback_trans_flies import RollBackTransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DownloadBackupFileKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    RollBackTransFileKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")


def rollback_local_and_time(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    mysql 定点回档类型 本地备份+指定时间
    @param root_id: flow 流程root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info: 关联的cluster对象
    """
    cluster_info["recover_binlog"] = True
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))
    sub_pipeline.add_act(
        act_name=_("下发db_actuator介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster_info["bk_cloud_id"],
                exec_ip=[cluster_info["master_ip"], cluster_info["old_slave_ip"]],
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        cluster_type=cluster_info["cluster_type"],
        cluster=cluster_info,
    )
    exec_act_kwargs.exec_ip = cluster_info["master_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之获取MASTER节点备份介质{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="master_backup_file",
    )

    exec_act_kwargs.exec_ip = cluster_info["old_slave_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之获取SLAVE节点备份介质{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="slave_backup_file",
    )

    sub_pipeline.add_act(
        act_name=_("判断备份文件来源,并传输备份文件到新定点恢复节点{}").format(cluster_info["rollback_ip"]),
        act_component_code=RollBackTransFileComponent.code,
        kwargs=asdict(
            RollBackTransFileKwargs(
                bk_cloud_id=cluster_info["bk_cloud_id"],
                file_list=[],
                file_target_path=cluster_info["file_target_path"],
                source_ip_list=[],
                exec_ip=cluster_info["rollback_ip"],
                cluster=cluster_info,
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

    # backup_time 在活动节点里。到flow下载binlog
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        task_ids=[],
        dest_ip=cluster_info["rollback_ip"],
        dest_dir=cluster_info["file_target_path"],
        reason="spider node rollback binlog",
        cluster=cluster_info,
    )
    sub_pipeline.add_act(
        act_name=_("下载定点恢复的binlog到{}").format(cluster_info["rollback_ip"]),
        act_component_code=MySQLRollbackDownloadBinlogComponent.code,
        kwargs=asdict(download_kwargs),
    )

    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_recover_binlog_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之前滚binlog{}".format(exec_act_kwargs.exec_ip)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    return sub_pipeline.build_sub_process(sub_name=_("{}定点回滚数据 LOCAL_AND_TIME ".format(cluster_info["rollback_ip"])))


def rollback_remote_and_time(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    mysql 定点回档类型 远程备份文件+指定时间
    @param root_id: flow 流程root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info: 关联的cluster对象
    """
    cluster_info["recover_binlog"] = True
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))
    rollback_time = cluster_info["rollback_time"]
    rollback_handler = FixPointRollbackHandler(cluster_info["cluster_id"])
    # 查询接口
    backupinfo = rollback_handler.query_latest_backup_log(str2datetime(rollback_time))
    if backupinfo is None:
        logger.error("cluster {} backup info not exists".format(cluster_info["cluster_id"]))
        raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(cluster_info["cluster_id"])))
    cluster_info["backupinfo"] = copy.deepcopy(backupinfo)
    cluster_info["backup_time"] = backupinfo["backup_time"]

    task_files = [{"file_name": i} for i in backupinfo["file_list"]]
    cluster_info["task_files"] = task_files
    cluster_info["backup_time"] = backupinfo["backup_time"]

    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        cluster_type=cluster_info["cluster_type"],
        cluster=cluster_info,
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
    rollback_handler = FixPointRollbackHandler(cluster_info["cluster_id"])
    backup_binlog = rollback_handler.query_binlog_from_bklog(
        start_time=backup_time,
        end_time=rollback_time,
        minute_range=30,
        host_ip=cluster_info["master_ip"],
        port=cluster_info["master_port"],
    )
    if backup_binlog is None:
        raise TenDBGetBackupInfoFailedException(message=_("获取实例 {} 的备份信息失败".format(cluster_info["master_ip"])))

    task_ids = [i["task_id"] for i in backup_binlog["file_list_details"]]
    binlog_files = [i["file_name"] for i in backup_binlog["file_list_details"]]
    cluster_info["binlog_files"] = ",".join(binlog_files)
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster_info["bk_cloud_id"],
        task_ids=task_ids,
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
    return sub_pipeline.build_sub_process(sub_name=_("{}定点回滚数据 REMOTE_AND_TIME ".format(cluster_info["rollback_ip"])))


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
        sub_name=_("{}定点回滚数据 REMOTE_AND_BACKUPID ".format(cluster_info["rollback_ip"]))
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
    )

    # backupinfo = cluster_info["backupinfo"]
    # backupinfo["backup_begin_time"] = backupinfo["backup_time"]

    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.cluster = cluster_info
    sub_pipeline.add_act(
        act_name=_("传输文件{}").format(cluster_info["rollback_ip"]),
        act_component_code=RollBackLocalTransFileComponent.code,
        kwargs=asdict(
            RollBackTransFileKwargs(
                bk_cloud_id=cluster_info["bk_cloud_id"],
                file_list=[],
                file_target_path=cluster_info["file_target_path"],
                source_ip_list=[],
                exec_ip=cluster_info["rollback_ip"],
                cluster=cluster_info,
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
        sub_name=_("{}定点回滚数据 LOCAL_AND_BACKUPID ".format(cluster_info["rollback_ip"]))
    )
