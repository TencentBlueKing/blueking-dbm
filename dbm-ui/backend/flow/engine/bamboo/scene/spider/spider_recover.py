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
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import RollbackType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBinlogFailedException
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import (
    MySQLDownloadBackupfileComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadBackupFileKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.utils.time import compare_time, str2datetime


def spider_recover_sub_flow(root_id: str, ticket_data: dict, cluster: dict):
    """
    spider 恢复表结构
    从指定spider列表获取备份介质恢复至指定的spider
    1 获取介质>判断介质来源>恢复数据
    @param root_id: flow流程root_id
    @param ticket_data: 单据 data
    @param cluster_info: 关联的cluster对象
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=int(cluster["bk_cloud_id"]), cluster_type=ClusterType.TenDBCluster, cluster=cluster
    )
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
    exec_act_kwargs.exec_ip = cluster["rollback_ip"]
    sub_pipeline.add_act(
        act_name=_("创建目录 {}".format(cluster["file_target_path"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    #  spider 没有主从节点.指定备份的ip:port为主节点。
    cluster["master_ip"] = ""
    cluster["master_port"] = 0
    cluster["change_master"] = False
    backup_info = cluster["backupinfo"]
    task_ids = [i["task_id"] for i in backup_info["file_list_details"]]
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster["bk_cloud_id"],
        task_ids=task_ids,
        dest_ip=cluster["rollback_ip"],
        desc_dir=cluster["file_target_path"],
        reason="spider node rollback data",
    )
    sub_pipeline.add_act(
        act_name=_("下载定点恢复的全库备份介质到{}:{}").format(cluster["rollback_ip"], cluster["rollback_port"]),
        act_component_code=MySQLDownloadBackupfileComponent.code,
        kwargs=asdict(download_kwargs),
    )
    exec_act_kwargs.exec_ip = cluster["rollback_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之恢复数据{}:{}").format(exec_act_kwargs.exec_ip, cluster["rollback_port"]),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    if cluster["rollback_type"] == RollbackType.REMOTE_AND_TIME.value:
        spider_has_binlog = cluster.get("spider_has_binlog", False)
        if spider_has_binlog:
            if compare_time(backup_info["backup_time"], cluster["rollback_time"]):
                raise TendbGetBinlogFailedException(message=_("{} 备份时间点大于回滚时间点".format(cluster["master_ip"])))
            rollback_handler = FixPointRollbackHandler(cluster["cluster_id"])
            backup_binlog = rollback_handler.query_binlog_from_bklog(
                str2datetime(backup_info["backup_time"]),
                str2datetime(cluster["rollback_time"]),
                minute_range=30,
                host_ip=cluster["rollback_ip"],
                port=cluster["rollback_port"],
            )
            if backup_binlog is None:
                raise TendbGetBinlogFailedException(message=_("获取实例 {} binlog失败".format(cluster["rollback_ip"])))

            task_ids = [i["task_id"] for i in backup_binlog["file_list_details"]]
            binlog_files = [i["file_name"] for i in backup_binlog["file_list_details"]]
            cluster["binlog_files"] = ",".join(binlog_files)
            download_kwargs = DownloadBackupFileKwargs(
                bk_cloud_id=cluster["bk_cloud_id"],
                task_ids=task_ids,
                dest_ip=cluster["rollback_ip"],
                desc_dir=cluster["file_target_path"],
                reason="spider node rollback binlog",
            )
            sub_pipeline.add_act(
                act_name=_("下载定点恢复的binlog到{}:{}").format(cluster["rollback_ip"], cluster["rollback_port"]),
                act_component_code=MySQLDownloadBackupfileComponent.code,
                kwargs=asdict(download_kwargs),
            )

            exec_act_kwargs.exec_ip = cluster["rollback_ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_recover_binlog_payload.__name__
            sub_pipeline.add_act(
                act_name=_("定点恢复之前滚binlog{}:{}").format(exec_act_kwargs.exec_ip, cluster["rollback_port"]),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

    return sub_pipeline.build_sub_process(sub_name=_("spider恢复:{}".format(cluster["instance"])))


def remote_node_rollback(root_id: str, ticket_data: dict, cluster: dict):
    """
    remote node 主从节点数据恢复+binlog前滚 备份类型 rollback_type 分为2种:
    REMOTE_AND_TIME:指定时间点恢复。恢复备份文件+binlog前滚
    REMOTE_AND_BACKUPID:指定备份id恢复。只需恢复备份文件
    @param root_id: flow 流程 root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info: 关联的cluster对象
    """
    # cluster = copy.deepcopy(cluster_info)
    sub_pipeline_all = SubBuilder(root_id=root_id, data=ticket_data)
    sub_pipeline_all_list = []
    for node in [cluster["new_master"], cluster["new_slave"]]:
        cluster["rollback_ip"] = node["ip"]
        cluster["rollback_port"] = node["port"]
        backup_info = cluster["backupinfo"]

        sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=int(cluster["bk_cloud_id"]), cluster_type=ClusterType.TenDBCluster, cluster=cluster
        )
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
        exec_act_kwargs.exec_ip = cluster["rollback_ip"]
        sub_pipeline.add_act(
            act_name=_("创建目录 {}".format(cluster["file_target_path"])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        task_ids = [i["task_id"] for i in backup_info["file_list_details"]]
        # 是否回档从库？
        download_kwargs = DownloadBackupFileKwargs(
            bk_cloud_id=cluster["bk_cloud_id"],
            task_ids=task_ids,
            dest_ip=cluster["rollback_ip"],
            desc_dir=cluster["file_target_path"],
            reason="spider remote node rollback data",
        )
        sub_pipeline.add_act(
            act_name=_("下载定点恢复的全库备份介质到{}:{}".format(cluster["rollback_ip"], cluster["rollback_port"])),
            act_component_code=MySQLDownloadBackupfileComponent.code,
            kwargs=asdict(download_kwargs),
        )
        exec_act_kwargs.exec_ip = cluster["rollback_ip"]

        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
        sub_pipeline.add_act(
            act_name=_("定点恢复之恢复数据{}:{}".format(exec_act_kwargs.exec_ip, cluster["rollback_port"])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        #  指定时间点的定点回档则需要执行binlog前滚。滚动到指定的时间点。
        if cluster["rollback_type"] == RollbackType.REMOTE_AND_TIME.value:
            if compare_time(backup_info["backup_time"], cluster["rollback_time"]):
                raise TendbGetBinlogFailedException(message=_("{} 备份时间点大于回滚时间点".format(cluster["master_ip"])))

            rollback_handler = FixPointRollbackHandler(cluster["cluster_id"])
            backup_binlog = rollback_handler.query_binlog_from_bklog(
                start_time=str2datetime(backup_info["backup_time"]),
                end_time=str2datetime(cluster["rollback_time"]),
                minute_range=30,
                host_ip=cluster["master_ip"],
                port=cluster["master_port"],
            )
            if backup_binlog is None:
                raise TendbGetBinlogFailedException(message=_("获取实例 {} 的备份信息失败".format(cluster["master_ip"])))

            task_ids = [i["task_id"] for i in backup_binlog["file_list_details"]]
            binlog_files = [i["file_name"] for i in backup_binlog["file_list_details"]]
            cluster["binlog_files"] = ",".join(binlog_files)
            download_kwargs = DownloadBackupFileKwargs(
                bk_cloud_id=cluster["bk_cloud_id"],
                task_ids=task_ids,
                dest_ip=cluster["rollback_ip"],
                desc_dir=cluster["file_target_path"],
                reason="tenDB rollback binlog",
            )
            sub_pipeline.add_act(
                act_name=_("下载定点恢复的binlog到{}:{}".format(cluster["rollback_ip"], cluster["rollback_port"])),
                act_component_code=MySQLDownloadBackupfileComponent.code,
                kwargs=asdict(download_kwargs),
            )
            exec_act_kwargs.exec_ip = cluster["rollback_ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_recover_binlog_payload.__name__
            sub_pipeline.add_act(
                act_name=_("定点恢复之前滚binlog{}:{}".format(exec_act_kwargs.exec_ip, cluster["rollback_port"])),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )
        sub_pipeline_all_list.append(
            sub_pipeline.build_sub_process(sub_name=_("定点恢复 {}:{}".format(node["ip"], node["port"])))
        )
    sub_pipeline_all.add_parallel_sub_pipeline(sub_pipeline_all_list)
    return sub_pipeline_all.build_sub_process(
        sub_name=_(
            "Remote node {} 恢复: 主 {} 从 {} ".format(
                cluster["shard_id"], cluster["new_master"]["instance"], cluster["new_slave"]["instance"]
            )
        )
    )
