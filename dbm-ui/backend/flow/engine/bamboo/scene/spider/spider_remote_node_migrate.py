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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import MysqlChangeMasterType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import (
    MySQLDownloadBackupfileComponent,
)
from backend.flow.plugins.components.collections.mysql.slave_trans_flies import SlaveTransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DownloadBackupFileKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    P2PFileKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.spider.tendb_cluster_info import get_remotedb_info


def remote_node_migrate_sub_flow(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    主从成对迁移子流程。(只做流程,元数据请在主流程控制)
    @param root_id:   flow 流程的root_id
    @param ticket_data:  单据传输过来的data数据
    @param cluster_info:  关联集群的信息
    """

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    #  已经安装好的2个ip，需要导入同步数据
    # 下发dbactor》通过master/slave 获取备份的文件》判断备份文件》恢复数据》change master
    cluster = {
        "master_ip": cluster_info["master_ip"],
        "slave_ip": cluster_info["slave_ip"],
        "master_port": cluster_info["master_port"],
        "new_master_ip": cluster_info["new_master_ip"],
        "new_slave_ip": cluster_info["new_slave_ip"],
        "new_master_port": cluster_info["new_master_port"],
        "bk_cloud_id": cluster_info["bk_cloud_id"],
        "backup_target_path": cluster_info["backup_target_path"],
    }
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=int(cluster["bk_cloud_id"]),
        cluster_type=ClusterType.TenDBCluster,
    )
    #  阶段1 传输工具
    exec_ip = [cluster["master_ip"], cluster["slave_ip"], cluster["new_master_ip"], cluster["new_slave_ip"]]
    sub_pipeline.add_act(
        act_name=_("下发db-actor: {}".format(exec_ip)),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster["bk_cloud_id"],
                exec_ip=exec_ip,
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )
    # 阶段2
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
    exec_act_kwargs.exec_ip = cluster["master_ip"]
    sub_pipeline.add_act(
        act_name=_("获取master节点备份介质{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="master_backup_file",
    )
    exec_act_kwargs.exec_ip = cluster["slave_ip"]
    sub_pipeline.add_act(
        act_name=_("获取slave节点备份介质{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="slave_backup_file",
    )
    # 阶段3 判断备份介质，并传输备份介质
    sub_pipeline.add_act(
        act_name=_("判断备份文件来源,并传输备份文件新机器"),
        act_component_code=SlaveTransFileComponent.code,
        kwargs=asdict(
            P2PFileKwargs(
                bk_cloud_id=cluster["bk_cloud_id"],
                file_list=[],
                file_target_path=cluster["backup_target_path"],
                source_ip_list=[],
                exec_ip=[cluster["new_slave_ip"], cluster["new_master_ip"]],
            )
        ),
    )
    # 阶段4 恢复数据  payload 需要注意新实例端口可能与旧实例不一样
    restore_list = []
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_restore_slave_payload.__name__
    restore_list.append(
        {
            "act_name": _("恢复新主节点数据{}:{}").format(exec_act_kwargs.exec_ip, cluster["new_master_port"]),
            "act_component_code": ExecuteDBActuatorScriptComponent.code,
            "kwargs": asdict(exec_act_kwargs),
            "write_payload_var": "change_master_info",
        }
    )

    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_restore_slave_payload.__name__
    restore_list.append(
        {
            "act_name": _("恢复新从节点数据{}:{}").format(exec_act_kwargs.exec_ip, cluster["new_master_port"]),
            "act_component_code": ExecuteDBActuatorScriptComponent.code,
            "kwargs": asdict(exec_act_kwargs),
        }
    )
    sub_pipeline.add_parallel_acts(acts_list=restore_list)

    # 阶段5 change master: 新从库指向新主库  注意端口
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_grant_mysql_repl_user_payload.__name__
    sub_pipeline.add_act(
        act_name=_("新增repl帐户{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
        write_payload_var="master_ip_sync_info",
    )

    exec_act_kwargs.exec_ip = cluster["new_slave_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_change_master_payload.__name__
    sub_pipeline.add_act(
        act_name=_("建立主从关系:新从库指向新主库 {}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    # 阶段6 change master: 新主库指向旧主库 todo 注意端口
    exec_act_kwargs.exec_ip = cluster["master_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_grant_repl_for_migrate_cluster.__name__
    sub_pipeline.add_act(
        act_name=_("新增repl帐户{}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_change_master_payload_for_migrate_cluster.__name__
    sub_pipeline.add_act(
        act_name=_("建立主从关系:新主库指向旧主库 {}").format(exec_act_kwargs.exec_ip),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    return sub_pipeline.build_sub_process(sub_name=_("RemoteDB主从节点成对迁移子流程{}".format(exec_ip)))


def remote_instance_migrate_sub_flow(root_id: str, ticket_data: dict, cluster_info: dict):
    """
    tendb remote 节点 扩容缩容流程。实例级别迁移。(只做流程,元数据请在主流程控制)
    @param root_id:  flow流程的root_id
    @param ticket_data: 关联单据 ticket对象
    @param cluster_info:  关联的cluster对象
    """

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    #  已经安装好的2个ip，需要导入同步数据
    # 下发dbactor》通过master/slave 获取备份的文件》判断备份文件》恢复数据》change master
    cluster = {
        "cluster_id": cluster_info["cluster_id"],
        "master_ip": cluster_info["master_ip"],
        "slave_ip": cluster_info["slave_ip"],
        "master_port": cluster_info["master_port"],
        "new_master_ip": cluster_info["new_master_ip"],
        "new_slave_ip": cluster_info["new_slave_ip"],
        "new_slave_port": cluster_info["new_slave_port"],
        "new_master_port": cluster_info["new_master_port"],
        "bk_cloud_id": cluster_info["bk_cloud_id"],
        "file_target_path": cluster_info["file_target_path"],
        "change_master_force": cluster_info["change_master_force"],
        "backupinfo": cluster_info["backupinfo"],
        "charset": cluster_info["charset"],
    }
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=int(cluster["bk_cloud_id"]),
        cluster_type=ClusterType.TenDBCluster,
    )
    backup_info = cluster["backupinfo"]
    #  主从并发下载备份介质 下载为异步下载，定时调起接口扫描下载结果
    task_ids = [i["task_id"] for i in backup_info["file_list_details"]]
    download_sub_pipeline_list = []
    download_kwargs = DownloadBackupFileKwargs(
        bk_cloud_id=cluster["bk_cloud_id"],
        task_ids=task_ids,
        dest_ip=cluster["new_master_ip"],
        desc_dir=cluster["file_target_path"],
        reason="spider remote node sync data",
    )
    download_sub_pipeline_list.append(
        {
            "act_name": _("下载全库备份介质到 {}".format(cluster["new_master_ip"])),
            "act_component_code": MySQLDownloadBackupfileComponent.code,
            "kwargs": asdict(download_kwargs),
        }
    )
    download_kwargs.dest_ip = cluster["new_slave_ip"]
    download_sub_pipeline_list.append(
        {
            "act_name": _("下载全库备份介质到 {}".format(cluster["new_slave_ip"])),
            "act_component_code": MySQLDownloadBackupfileComponent.code,
            "kwargs": asdict(download_kwargs),
        }
    )
    sub_pipeline.add_parallel_acts(download_sub_pipeline_list)

    # 阶段4 恢复数据remote主从节点的数据
    restore_list = []
    cluster["restore_ip"] = cluster["new_master_ip"]
    cluster["restore_port"] = cluster["new_master_port"]
    cluster["source_ip"] = cluster["master_ip"]
    cluster["source_port"] = cluster["master_port"]
    cluster["change_master"] = False
    exec_act_kwargs.exec_ip = cluster["new_master_ip"]
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


def remote_node_uninstall_sub_flow(root_id: str, ticket_data: dict, ip: str):
    """
    卸载remotedb 指定ip节点下的所有实例
    @param root_id: flow流程的root_id
    @param ticket_data: 单据 data 对象
    @param ip: 指定卸载的ip
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    cluster = {"uninstall_ip": ip, "bk_cloud_id": ticket_data["bk_cloud_id"]}
    instances = get_remotedb_info(cluster["uninstall_ip"], cluster["bk_cloud_id"])
    sub_pipeline_list = []
    for instance in instances:
        cluster["backend_port"] = instance["port"]
        sub_pipeline_list.append(
            {
                "act_name": _("卸载MySQL实例:{}:{}".format(cluster["uninstall_ip"], cluster["backend_port"])),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=cluster["uninstall_ip"],
                        bk_cloud_id=cluster["bk_cloud_id"],
                        cluster=cluster,
                        get_mysql_payload_func=MysqlActPayload.get_uninstall_mysql_payload.__name__,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(sub_pipeline_list)
    return sub_pipeline.build_sub_process(sub_name=_("Remote node {} 卸载整机实例".format(cluster["uninstall_ip"])))
