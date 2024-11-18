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

from backend.configuration.constants import MYSQL_DATA_RESTORE_TIME, MYSQL_USUAL_JOB_TIME, DBType
from backend.db_meta.models import Cluster
from backend.flow.consts import MysqlChangeMasterType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.get_binlog_backup import get_backup_binlog
from backend.flow.engine.bamboo.scene.mysql.common.get_local_backup import get_local_backup
from backend.flow.engine.bamboo.scene.spider.common.exceptions import (
    TendbGetBackupInfoFailedException,
    TendbGetBinlogFailedException,
)
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
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")


def mysql_restore_data_sub_flow(
    root_id: str, ticket_data: dict, cluster: dict, cluster_model: Cluster, ins_list: list
):
    """
    @param root_id: 流程 root_id
    @param ticket_data: 单据输入的tick_data
    @param cluster:  流程信息
    @param cluster_model: 集群元数据
    @param ins_list: 查询实例列表
    @return:
    cluster: new_slave_ip,new_slave_port,master_ip,master_port,file_target_path,charset,change_master_force,backup_time
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    cluster["change_master"] = False
    backup_info = get_local_backup(ins_list, cluster_model)
    if backup_info is None:
        logger.error("cluster {} backup info not exists".format(cluster_model.id))
        raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的本地备份信息失败".format(cluster_model.id)))
    cluster["backupinfo"] = backup_info
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_model.bk_cloud_id,
        cluster_type=cluster_model.cluster_type,
        cluster=cluster,
    )
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    sub_pipeline.add_act(
        act_name=_("创建目录 {}".format(cluster["file_target_path"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    sub_pipeline.add_act(
        act_name=_("下发db-actor到节点{}".format(cluster["master_ip"])),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster_model.bk_cloud_id,
                exec_ip=[cluster["master_ip"], cluster["new_slave_ip"]],
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )

    task_ids = ["{}/{}".format(backup_info["backup_dir"], i["file_name"]) for i in backup_info["file_list"]]
    if backup_info["backup_meta_file"] not in task_ids:
        task_ids.append(backup_info["backup_meta_file"])
    sub_pipeline.add_act(
        act_name=_("本地备份文件下载"),
        act_component_code=MySQLTransFileComponent.code,
        kwargs=asdict(
            P2PFileKwargs(
                bk_cloud_id=cluster_model.bk_cloud_id,
                file_list=task_ids,
                file_target_path=cluster["file_target_path"],
                source_ip_list=[backup_info["instance_ip"]],
                exec_ip=cluster["new_slave_ip"],
            )
        ),
    )

    # 阶段4 恢复数据remote主从节点的数据
    cluster["restore_ip"] = cluster["new_slave_ip"]
    cluster["restore_port"] = cluster["new_slave_port"]
    cluster["source_ip"] = cluster["master_ip"]
    cluster["source_port"] = cluster["master_port"]
    cluster["change_master"] = False
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    exec_act_kwargs.job_timeout = MYSQL_DATA_RESTORE_TIME
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_restore_remotedb_payload.__name__
    sub_pipeline.add_act(
        act_name=_("恢复新从节点数据 {}:{}".format(exec_act_kwargs.exec_ip, cluster["restore_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    )

    # 阶段5 change master: 新从库指向旧主库
    cluster["target_ip"] = cluster["master_ip"]
    cluster["target_port"] = cluster["master_port"]
    cluster["repl_ip"] = cluster["new_slave_ip"]
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["master_ip"]
    exec_act_kwargs.job_timeout = MYSQL_USUAL_JOB_TIME
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_grant_remotedb_repl_user.__name__
    sub_pipeline.add_act(
        act_name=_("新增repl帐户{}".format(exec_act_kwargs.exec_ip)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    cluster["repl_ip"] = cluster["new_slave_ip"]
    cluster["repl_port"] = cluster["new_slave_port"]
    cluster["target_ip"] = cluster["master_ip"]
    cluster["target_port"] = cluster["master_port"]
    cluster["change_master_type"] = MysqlChangeMasterType.BACKUPFILE.value
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_remotedb_change_master.__name__
    sub_pipeline.add_act(
        act_name=_("建立主从关系 {}:{}".format(exec_act_kwargs.exec_ip, cluster["repl_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    return sub_pipeline.build_sub_process(sub_name=_("用本地备份恢复数据{}".format(exec_act_kwargs.exec_ip)))


def mysql_rollback_data_sub_flow(
    root_id: str, ticket_data: dict, cluster: dict, cluster_model: Cluster, ins_list: list, is_rollback_binlog: bool
):
    """
    @param root_id: 流程 root_id
    @param ticket_data: 单据输入的tick_data
    @param cluster:  流程信息
    @param cluster_model: 集群元数据
    @param ins_list: 查询实例列表
    @param is_rollback_binlog:是否前滚日志
    @return:
    cluster: new_slave_ip,new_slave_port,master_ip,master_port,file_target_path,charset,change_master_force,backup_time
    """
    rollback_time = str2datetime(cluster["rollback_time"], "%Y-%m-%d %H:%M:%S")
    if is_rollback_binlog:
        cluster["recover_binlog"] = True
    else:
        cluster["recover_binlog"] = False
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    cluster["change_master"] = False
    backup_info = get_local_backup(ins_list, cluster_model, cluster["rollback_time"])
    logger.debug(backup_info)
    if backup_info is None:
        logger.error("cluster {} backup info not exists".format(cluster_model.id))
        raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(cluster_model.id)))
    cluster["backupinfo"] = backup_info
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_model.bk_cloud_id,
        cluster_type=cluster_model.cluster_type,
        cluster=cluster,
    )
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
    exec_act_kwargs.exec_ip = cluster["rollback_ip"]
    sub_pipeline.add_act(
        act_name=_("创建目录 {}".format(cluster["file_target_path"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 下载备份文件  backup_info["file_list"] 需要确认
    task_ids = ["{}/{}".format(backup_info["backup_dir"], i["file_name"]) for i in backup_info["file_list"]]
    if backup_info["backup_meta_file"] not in task_ids:
        task_ids.append(backup_info["backup_meta_file"])
    sub_pipeline.add_act(
        act_name=_("下载备份到{}".format(cluster["rollback_ip"])),
        act_component_code=MySQLTransFileComponent.code,
        kwargs=asdict(
            P2PFileKwargs(
                bk_cloud_id=cluster_model.bk_cloud_id,
                file_list=task_ids,
                file_target_path=cluster["file_target_path"],
                source_ip_list=[backup_info["instance_ip"]],
                exec_ip=cluster["rollback_ip"],
            )
        ),
    )

    cluster["change_master"] = False
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["rollback_ip"]
    exec_act_kwargs.job_timeout = MYSQL_DATA_RESTORE_TIME
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
    sub_pipeline.add_act(
        act_name=_("恢复新从节点数据 {}:{}".format(exec_act_kwargs.exec_ip, cluster["rollback_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    )

    if is_rollback_binlog:
        backup_time = str2datetime(backup_info["backup_time"], "%Y-%m-%d %H:%M:%S")
        cluster["backup_time"] = backup_info["backup_time"]
        binlog_result = get_backup_binlog(
            cluster_id=cluster_model.id,
            start_time=backup_time,
            end_time=rollback_time,
            binlog_info=backup_info["binlog_info"],
        )
        if "query_binlog_error" in binlog_result.keys():
            raise TendbGetBinlogFailedException(message=binlog_result["query_binlog_error"])

        cluster.update(binlog_result)

        download_kwargs = DownloadBackupFileKwargs(
            bk_cloud_id=cluster_model.bk_cloud_id,
            task_ids=binlog_result["binlog_task_ids"],
            dest_ip=cluster["rollback_ip"],
            dest_dir=cluster["file_target_path"],
            reason="rollback node rollback binlog",
            cluster=cluster,
        )
        sub_pipeline.add_act(
            act_name=_("下载定点恢复的binlog到{}").format(cluster["rollback_ip"]),
            act_component_code=MySQLDownloadBackupfileComponent.code,
            kwargs=asdict(download_kwargs),
        )
        exec_act_kwargs.exec_ip = cluster["rollback_ip"]
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_recover_binlog_payload.__name__
        exec_act_kwargs.cluster = copy.deepcopy(cluster)
        sub_pipeline.add_act(
            act_name=_("定点恢复之前滚binlog{}".format(exec_act_kwargs.exec_ip)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
    return sub_pipeline.build_sub_process(
        sub_name=_("用本地备份恢复数据{}:{}".format(exec_act_kwargs.exec_ip, cluster["rollback_port"]))
    )


def mysql_restore_master_slave_sub_flow(
    root_id: str, ticket_data: dict, cluster: dict, cluster_model: Cluster, ins_list: list
):
    """
    @param root_id: 流程 root_id
    @param ticket_data: 单据输入的tick_data
    @param cluster:  流程信息
    @param cluster_model: 集群元数据
    @param ins_list: 查询实例列表
    @return:
    cluster: new_slave_ip,new_slave_port,master_ip,master_port,file_target_path,charset,change_master_force,backup_time
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    cluster["change_master"] = False
    backup_info = get_local_backup(ins_list, cluster_model)
    if backup_info is None:
        logger.error("cluster {} backup info not exists".format(cluster_model.id))
        raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(cluster_model.id)))
    cluster["backupinfo"] = backup_info
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster_model.bk_cloud_id,
        cluster_type=cluster_model.cluster_type,
        cluster=cluster,
    )
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
    exec_act_kwargs.exec_ip = [cluster["new_slave_ip"], cluster["new_master_ip"]]
    sub_pipeline.add_act(
        act_name=_("创建目录 {}".format(cluster["file_target_path"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    sub_pipeline.add_act(
        act_name=_("下发db-actor到节点"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster_model.bk_cloud_id,
                exec_ip=[cluster["master_ip"], cluster["new_slave_ip"], cluster["new_master_ip"]],
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )

    task_ids = ["{}/{}".format(backup_info["backup_dir"], i["file_name"]) for i in backup_info["file_list"]]
    if backup_info["backup_meta_file"] not in task_ids:
        task_ids.append(backup_info["backup_meta_file"])
    sub_pipeline.add_act(
        act_name=_("本地备份文件下载"),
        act_component_code=MySQLTransFileComponent.code,
        kwargs=asdict(
            P2PFileKwargs(
                bk_cloud_id=cluster_model.bk_cloud_id,
                file_list=task_ids,
                file_target_path=cluster["file_target_path"],
                source_ip_list=[backup_info["instance_ip"]],
                exec_ip=[cluster["new_slave_ip"], cluster["new_master_ip"]],
            )
        ),
    )

    #  恢复
    restore_list = []
    cluster["restore_ip"] = cluster["new_master_ip"]
    cluster["restore_port"] = cluster["new_master_port"]
    cluster["source_ip"] = cluster["master_ip"]
    cluster["source_port"] = cluster["master_port"]
    cluster["change_master"] = False
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
    exec_act_kwargs.job_timeout = MYSQL_DATA_RESTORE_TIME
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_restore_remotedb_payload.__name__
    restore_list.append(
        {
            "act_name": _("恢复新主节点数据 {}:{}".format(exec_act_kwargs.exec_ip, cluster["restore_port"])),
            "act_component_code": ExecuteDBActuatorScriptComponent.code,
            "kwargs": asdict(exec_act_kwargs),
            "write_payload_var": "change_master_info",
        }
    )

    cluster["restore_ip"] = cluster["new_slave_ip"]
    cluster["restore_port"] = cluster["new_slave_port"]
    cluster["source_ip"] = cluster["master_ip"]
    cluster["source_port"] = cluster["master_port"]
    cluster["change_master"] = False
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_restore_remotedb_payload.__name__
    restore_list.append(
        {
            "act_name": _("恢复新从节点数据 {}:{}".format(exec_act_kwargs.exec_ip, cluster["restore_port"])),
            "act_component_code": ExecuteDBActuatorScriptComponent.code,
            "kwargs": asdict(exec_act_kwargs),
        }
    )
    sub_pipeline.add_parallel_acts(acts_list=restore_list)

    # 阶段5 change master: 新从库指向新主库
    cluster["target_ip"] = cluster["new_master_ip"]
    cluster["target_port"] = cluster["new_master_port"]
    cluster["repl_ip"] = cluster["new_slave_ip"]
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
    exec_act_kwargs.job_timeout = MYSQL_USUAL_JOB_TIME
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_grant_remotedb_repl_user.__name__
    sub_pipeline.add_act(
        act_name=_("新增repl帐户{}".format(exec_act_kwargs.exec_ip)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="show_master_status_info",
    )

    cluster["repl_ip"] = cluster["new_slave_ip"]
    cluster["repl_port"] = cluster["new_slave_port"]
    cluster["target_ip"] = cluster["new_master_ip"]
    cluster["target_port"] = cluster["new_master_port"]
    cluster["change_master_type"] = MysqlChangeMasterType.MASTERSTATUS.value
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_remotedb_change_master.__name__
    sub_pipeline.add_act(
        act_name=_("建立主从关系:新从库指向新主库 {} {}:".format(exec_act_kwargs.exec_ip, cluster["repl_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 阶段6 change master: 新主库指向旧主库
    cluster["target_ip"] = cluster["master_ip"]
    cluster["target_port"] = cluster["master_port"]
    cluster["repl_ip"] = cluster["new_master_ip"]
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["master_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_grant_remotedb_repl_user.__name__
    sub_pipeline.add_act(
        act_name=_("新增repl帐户{}".format(exec_act_kwargs.exec_ip)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    cluster["repl_ip"] = cluster["new_master_ip"]
    cluster["repl_port"] = cluster["new_master_port"]
    cluster["target_ip"] = cluster["master_ip"]
    cluster["target_port"] = cluster["master_port"]
    cluster["change_master_type"] = MysqlChangeMasterType.BACKUPFILE.value
    exec_act_kwargs.cluster = copy.deepcopy(cluster)
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_remotedb_change_master.__name__
    sub_pipeline.add_act(
        act_name=_("建立主从关系:新主库指向旧主库 {}:{}".format(exec_act_kwargs.exec_ip, cluster["repl_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    return sub_pipeline.build_sub_process(sub_name=_("RemoteDB主从节点成对迁移子流程{}".format(exec_act_kwargs.exec_ip)))
