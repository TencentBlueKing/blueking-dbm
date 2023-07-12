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
import datetime
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import (
    MySQLDownloadBackupfileComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadBackupFileKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.utils import time


def spider_recover_sub_flow(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    spider 恢复表结构
    从指定spider列表获取备份介质恢复至指定的spider
    1 获取介质>判断介质来源>恢复数据
    @param root_id: flow流程root_id
    @param ticket_data: 单据 data
    @param cluster_info: 关联的cluster对象
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    cluster = copy.deepcopy(cluster_info)
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=int(cluster["bk_cloud_id"]),
        cluster_type=ClusterType.TenDBCluster,
    )

    cluster["rollback_ip"] = cluster["ip"]
    cluster["rollback_port"] = cluster["port"]
    cluster["master_ip"] = cluster["total_backupinfo"]["host"]
    cluster["master_port"] = cluster["total_backupinfo"]["port"]

    backupinfo = cluster["total_backupinfo"]
    task_ids = [i["task_id"] for i in backupinfo["file_list_details"]]
    # 是否回档从库？
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster["bk_cloud_id"],
        task_ids=task_ids,
        dest_ip=cluster["rollback_ip"],
        login_user="mysql",
        desc_dir=cluster["file_target_path"],
        reason="spider node rollback data",
    )
    sub_pipeline.add_act(
        act_name=_("下载定点恢复的全库备份介质到{}".format(cluster["rollback_ip"])),
        act_component_code=MySQLDownloadBackupfileComponent.code,
        kwargs=asdict(download_kwargs),
    )
    # todo 注意payload信息  确定indexfile
    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之恢复数据{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="change_master_info",
    )

    # 恢复binlog 构造出时间 backup_consistent_time  rollback_time binlog_begin_time binlog_end_time binlog源为master_ip
    #  下载binlog的时间段: 开始为备份一致性时间点前半小时,结束为回滚目标时间点后半小时。以确保能下载到对应binlog
    rollback_time = time.strptime(cluster["rollback_time"], "%Y-%m-%d %H:%M:%S")
    backup_time = time.strptime(backupinfo["backup_consistent_time"], "%Y-%m-%d %H:%M:%S")
    cluster["binlog_begin_time"] = (backup_time - datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    cluster["binlog_end_time"] = (rollback_time + datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

    # todo 通过接口插到binlog的备份列表
    task_ids = []
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster["bk_cloud_id"],
        task_ids=task_ids,
        dest_ip=cluster["rollback_ip"],
        login_user="mysql",
        desc_dir=cluster["file_target_path"],
        reason="spider node rollback binlog",
    )
    sub_pipeline.add_act(
        act_name=_("下载定点恢复的binlog到{}").format(cluster["rollback_ip"]),
        act_component_code=MySQLDownloadBackupfileComponent.code,
        kwargs=asdict(download_kwargs),
    )

    exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_recover_binlog_payload.__name__
    sub_pipeline.add_act(
        act_name=_("定点恢复之前滚binlog{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    return sub_pipeline


def remote_node_rollback(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    remote node 主从节点数据恢复+binlog前滚
    @param root_id: flow 流程 root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info: 关联的cluster对象
    """
    cluster = copy.deepcopy(cluster_info)
    sub_pipeline_all = SubBuilder(root_id=root_id, data=ticket_data)
    sub_pipeline_all_list = []
    for node in [cluster["new_master"], cluster["new_slave"]]:
        cluster["rollback_ip"] = node["ip"]
        cluster["rollback_port"] = node["port"]
        sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=int(cluster["bk_cloud_id"]),
            cluster_type=ClusterType.TenDBCluster,
        )
        backup_info = cluster["total_backupinfo"]
        task_ids = [i["task_id"] for i in backup_info["file_list_details"]]
        # 是否回档从库？
        download_kwargs = DownloadBackupFileKwargs(
            bk_cloud_id=cluster["bk_cloud_id"],
            task_ids=task_ids,
            dest_ip=cluster["rollback_ip"],
            login_user="mysql",
            desc_dir=cluster["file_target_path"],
            reason="spider remote node rollback data",
        )
        sub_pipeline.add_act(
            act_name=_("下载定点恢复的全库备份介质到{}".format(cluster["rollback_ip"])),
            act_component_code=MySQLDownloadBackupfileComponent.code,
            kwargs=asdict(download_kwargs),
        )
        # todo 注意payload信息  确定indexfile
        exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
        sub_pipeline.add_act(
            act_name=_("定点恢复之恢复数据{}".format(exec_act_kwargs.exec_ip)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
            write_payload_var="change_master_info",
        )

        #  todo 恢复binlog 构造出时间 backup_consistent_time  rollback_time binlog_begin_time binlog_end_time binlog源为master_ip
        #  下载binlog的时间段: 开始为备份一致性时间点前半小时,结束为回滚目标时间点后半小时。以确保能下载到对应binlog
        rollback_time = time.strptime(cluster["rollback_time"], "%Y-%m-%d %H:%M:%S")
        backup_time = time.strptime(backup_info["backup_consistent_time"], "%Y-%m-%d %H:%M:%S")
        cluster["binlog_begin_time"] = (backup_time - datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        cluster["binlog_end_time"] = (rollback_time + datetime.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

        # todo 通过接口插到binlog的备份列表
        task_ids = []
        download_kwargs = DownloadBackupFileKwargs(
            bk_cloud_id=cluster["bk_cloud_id"],
            task_ids=task_ids,
            dest_ip=cluster["rollback_ip"],
            login_user="mysql",
            desc_dir=cluster["file_target_path"],
            reason="spider node rollback binlog",
        )
        sub_pipeline.add_act(
            act_name=_("下载定点恢复的binlog到{}".format(cluster["rollback_ip"])),
            act_component_code=MySQLDownloadBackupfileComponent.code,
            kwargs=asdict(download_kwargs),
        )
        exec_act_kwargs.exec_ip = cluster_info["rollback_ip"]
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_recover_binlog_payload.__name__
        sub_pipeline.add_act(
            act_name=_("定点恢复之前滚binlog{}".format(exec_act_kwargs.exec_ip)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        sub_pipeline_all_list.append(
            sub_pipeline.build_sub_process(sub_name=_("定点恢复 {}:{}".format(node["ip"], node["port"])))
        )
    sub_pipeline_all.add_parallel_acts(sub_pipeline_all_list)
    return sub_pipeline_all
