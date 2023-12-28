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
import logging
from dataclasses import asdict
from datetime import datetime

from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.configuration.constants import MYSQL_DATA_RESTORE_TIME, MYSQL_USUAL_JOB_TIME
from backend.db_meta.enums import ClusterType
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import MysqlChangeMasterType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBackupInfoFailedException
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import (
    MySQLDownloadBackupfileComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadBackupFileKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


def slave_recover_sub_flow(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    tendb remote slave 节点 恢复。(只做流程,元数据请在主流程控制)
    @param root_id:  flow流程的root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info:  关联的cluster对象
    """

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # 下发dbactor》通过master/slave 获取备份的文件》判断备份文件》恢复数据》change master
    cluster = {
        "cluster_id": cluster_info["cluster_id"],
        "master_ip": cluster_info["master_ip"],
        "master_port": cluster_info["master_port"],
        "new_slave_ip": cluster_info["new_slave_ip"],
        "new_slave_port": cluster_info["new_slave_port"],
        "bk_cloud_id": cluster_info["bk_cloud_id"],
        "file_target_path": cluster_info["file_target_path"],
        "change_master_force": cluster_info["change_master_force"],
        "charset": cluster_info["charset"],
        "cluster_type": cluster_info["cluster_type"],
    }
    # 查询备份
    rollback_time = datetime.now(timezone.utc)
    rollback_handler = FixPointRollbackHandler(cluster_id=cluster["cluster_id"])
    backup_info = rollback_handler.query_latest_backup_log(rollback_time)
    if backup_info is None:
        logger.error("cluster {} backup info not exists".format(cluster["cluster_id"]))
        raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(cluster["cluster_id"])))

    #  todo 兼容spider。后续需改接口
    if cluster["cluster_type"] == ClusterType.TenDBCluster:
        cluster["shard_id"] = cluster_info["shard_id"]
        backup_info = backup_info["remote_node"][cluster["shard_id"]]
    cluster["backupinfo"] = backup_info

    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=int(cluster["bk_cloud_id"]),
        cluster_type=cluster["cluster_type"],
        cluster=cluster,
    )
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    sub_pipeline.add_act(
        act_name=_("创建目录 {}".format(cluster["file_target_path"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    #  新从库下载备份介质 下载为异步下载，定时调起接口扫描下载结果
    task_ids = [i["task_id"] for i in backup_info["file_list_details"]]
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster["bk_cloud_id"],
        task_ids=task_ids,
        dest_ip=cluster["new_slave_ip"],
        dest_dir=cluster["file_target_path"],
        reason="slave recover",
    )
    sub_pipeline.add_act(
        act_name=_("下载全库备份介质到 {}".format(cluster["new_slave_ip"])),
        act_component_code=MySQLDownloadBackupfileComponent.code,
        kwargs=asdict(download_kwargs),
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
        act_name=_("建立主从关系:新主库指向旧主库 {}:{}".format(exec_act_kwargs.exec_ip, cluster["repl_port"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    return sub_pipeline.build_sub_process(sub_name=_("RemoteDB从节点重建子流程{}".format(exec_act_kwargs.exec_ip)))
