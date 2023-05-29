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
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import RollbackType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import (
    MySQLDownloadBackupfileComponent,
)
from backend.flow.plugins.components.collections.mysql.rollback_local_trans_flies import (
    RollBackLocalTransFileComponent,
)
from backend.flow.plugins.components.collections.mysql.rollback_trans_flies import RollBackTransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import (
    get_cluster_info,
    get_cluster_ports,
    get_version_and_charset,
)
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DBMetaOPKwargs,
    DownloadBackupFileKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    RollBackTransFileKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.utils import time

logger = logging.getLogger("flow")


class MySQLRollbackDataFlow(object):
    """
    mysql 重建slave流程
    元数据修改：
    1 mysql_restore_slave_add_instance
    2 mysql_rollback_remove_instance
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def rollback_data_flow(self):
        """
        定义重建slave节点的流程
        """
        mysql_restore_slave_pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.data))
        sub_pipeline_list = []
        for info in self.data["infos"]:
            # 根据ip级别安装mysql实例
            ticket_data = copy.deepcopy(self.data)
            cluster_ports = get_cluster_ports([info["cluster_id"]])
            info.update(cluster_ports)
            one_cluster = get_cluster_info(info["cluster_id"])
            charset, db_version = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=info["db_module_id"],
                cluster_type=info["cluster_type"],
            )
            info["new_slave_ip"] = info["rollback_ip"]
            ticket_data["clusters"] = info["clusters"]
            ticket_data["mysql_ports"] = info["cluster_ports"]
            ticket_data["charset"] = charset
            ticket_data["db_version"] = db_version

            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
            sub_pipeline.add_sub_pipeline(
                sub_flow=self.install_instance_sub_flow(ticket_data=ticket_data, cluster_info=info)
            )

            one_cluster["rollback_ip"] = info["rollback_ip"]
            one_cluster["databases"] = info["databases"]
            one_cluster["tables"] = info["tables"]
            one_cluster["databases_ignore"] = info["databases_ignore"]
            one_cluster["tables_ignore"] = info["tables_ignore"]
            one_cluster["backend_port"] = one_cluster["master_port"]
            one_cluster["charset"] = charset
            one_cluster["change_master"] = False
            one_cluster["diretory"] = f"/data/dbbak/{self.root_id}"

            one_cluster["file_target_path"] = one_cluster["diretory"]
            one_cluster["skip_local_exists"] = True
            one_cluster["name_regex"] = f"^.+{one_cluster['master_port']}\\.\\d+(\\..*)*$"
            one_cluster["rollback_time"] = info["rollback_time"]
            # ？？？
            one_cluster["new_master_ip"] = one_cluster["master_ip"]
            one_cluster["new_slave_ip"] = info["new_slave_ip"]

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=one_cluster["bk_cloud_id"],
                cluster_type=one_cluster["cluster_type"],
                cluster=one_cluster,
            )
            # === 本地备份文件+时间点恢复 ===
            if info["rollback_type"] == RollbackType.LOCAL_AND_TIME:
                # rollback_time = time.strptime(info["rollback_time"], "%Y-%m-%d %H:%M:%S")
                one_cluster["rollback_time"] = info["rollback_time"]
                sub_pipeline.add_act(
                    act_name=_("下发db_actuator介质"),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            exec_ip=[one_cluster["master_ip"], one_cluster["old_slave_ip"]],
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                )

                exec_act_kwargs.exec_ip = one_cluster["master_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("定点恢复之获取MASTER节点备份介质{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="master_backup_file",
                )

                exec_act_kwargs.exec_ip = one_cluster["old_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("定点恢复之获取SLAVE节点备份介质{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="slave_backup_file",
                )

                sub_pipeline.add_act(
                    act_name=_("判断备份文件来源,并传输备份文件到新定点恢复节点{}").format(info["rollback_ip"]),
                    act_component_code=RollBackTransFileComponent.code,
                    kwargs=asdict(
                        RollBackTransFileKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            file_list=[],
                            file_target_path=one_cluster["file_target_path"],
                            source_ip_list=[],
                            exec_ip=info["rollback_ip"],
                            cluster=one_cluster,
                        )
                    ),
                )

                exec_act_kwargs.exec_ip = info["rollback_ip"]
                exec_act_kwargs.get_mysql_payload_func = (
                    MysqlActPayload.get_rollback_local_data_restore_payload.__name__
                )
                sub_pipeline.add_act(
                    act_name=_("定点恢复之恢复数据{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="change_master_info",
                )
            #     todo 需添加binlog恢复流程

            # === 以下为远程备份+时间/备份ID ===
            backupinfo = info["backupinfo"]
            if info["rollback_type"] == RollbackType.REMOTE_AND_TIME.value:
                rollback_time = time.strptime(info["rollback_time"], "%Y-%m-%d %H:%M:%S")
                rollback_handler = FixPointRollbackHandler(one_cluster["cluster_id"])
                # 查询接口
                backupinfo = rollback_handler.query_latest_backup_log(rollback_time)
                one_cluster["master_ip"] = backupinfo["mysql_host"]
                one_cluster["backup_time"] = backupinfo["backup_begin_time"]
                one_cluster["total_backupinfo"] = copy.deepcopy(backupinfo)
                rollback_handler.query_backup_log_from_bklog()

            if (
                info["rollback_type"] == RollbackType.REMOTE_AND_TIME.value
                or info["rollback_type"] == RollbackType.REMOTE_AND_BACKUPID.value
            ):
                task_files = [{"file_name": i} for i in backupinfo["file_list"]]
                one_cluster["task_files"] = task_files
                #  区分
                one_cluster["master_ip"] = backupinfo["mysql_host"]
                one_cluster["backup_time"] = backupinfo["backup_begin_time"]

                # 用于下载
                # 用于日志恢复、日志恢复前后增加半个小时来获取恢复binlog
                backup_time = time.strptime(backupinfo["backup_begin_time"], "%Y-%m-%d %H:%M:%S")
                one_cluster["begin_time"] = (backup_time - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                one_cluster["end_time"] = (backup_time + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                one_cluster["total_backupinfo"] = copy.deepcopy(backupinfo)

                exec_act_kwargs.cluster = one_cluster
                task_ids = [i["task_id"] for i in backupinfo["file_list_details"]]
                download_kwargs = DownloadBackupFileKwargs(
                    bk_cloud_id=one_cluster["bk_cloud_id"],
                    task_ids=task_ids,
                    dest_ip=info["rollback_ip"],
                    login_user="mysql",
                    desc_dir=one_cluster["file_target_path"],
                    reason="mysql rollback data",
                )
                sub_pipeline.add_act(
                    act_name=_("下载定点恢复的全库备份介质到{}").format(info["rollback_ip"]),
                    act_component_code=MySQLDownloadBackupfileComponent.code,
                    kwargs=asdict(download_kwargs),
                )

                exec_act_kwargs.exec_ip = info["rollback_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("定点恢复之恢复数据{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="change_master_info",
                )
                #  远程备份+时间需要binlog前滚
                if info["rollback_type"] == RollbackType.REMOTE_AND_TIME.value:
                    rollback_time = time.strptime(info["rollback_time"], "%Y-%m-%d %H:%M:%S")
                    one_cluster["binlog_begin_time"] = (backup_time - datetime.timedelta(minutes=30)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    one_cluster["binlog_end_time"] = (rollback_time + datetime.timedelta(minutes=30)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    exec_act_kwargs.exec_ip = info["rollback_ip"]

                    # todo 需添加binlog恢复流程
                    # exec_act_kwargs.get_mysql_payload_func = (
                    #     MysqlActPayload.get_rollback_data_download_binlog_payload.__name__
                    # )
                    # sub_pipeline.add_act(
                    #     act_name=_("下载定点恢复的binlog文件到{}").format(exec_act_kwargs.exec_ip),
                    #     act_component_code=ExecuteDBActuatorScriptComponent.code,
                    #     kwargs=asdict(exec_act_kwargs),
                    #     write_payload_var="binlog_files",
                    # )
                    # exec_act_kwargs.exec_ip = info["rollback_ip"]
                    # exec_act_kwargs.get_mysql_payload_func = (
                    #     MysqlActPayload.get_rollback_data_recover_binlog_payload.__name__
                    # )
                    # sub_pipeline.add_act(
                    #     act_name=_("定点恢复之前滚binlog{}").format(exec_act_kwargs.exec_ip),
                    #     act_component_code=ExecuteDBActuatorScriptComponent.code,
                    #     kwargs=asdict(exec_act_kwargs),
                    # )

            #  === 本地备份+备份ID ==
            elif info["rollback_type"] == RollbackType.LOCAL_AND_BACKUPID:
                backupinfo = info["backupinfo"]
                backupinfo["backup_begin_time"] = backupinfo["backup_time"]
                backupinfo["mysql_host"] = backupinfo["inst_host"]
                backupinfo["mysql_port"] = backupinfo["inst_port"]
                # one_cluster["master_ip"] = backupinfo["inst_host"]
                one_cluster["total_backupinfo"] = copy.deepcopy(backupinfo)

                exec_act_kwargs.exec_ip = info["rollback_ip"]
                exec_act_kwargs.cluster = one_cluster

                sub_pipeline.add_act(
                    act_name=_("传输文件{}").format(info["rollback_ip"]),
                    act_component_code=RollBackLocalTransFileComponent.code,
                    kwargs=asdict(
                        RollBackTransFileKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            file_list=[],
                            file_target_path=one_cluster["file_target_path"],
                            source_ip_list=[],
                            exec_ip=info["rollback_ip"],
                            cluster=one_cluster,
                        )
                    ),
                )

                exec_act_kwargs.exec_ip = info["rollback_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_rollback_data_restore_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("定点恢复之恢复数据{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="change_master_info",
                )

            # 设置暂停。接下来卸载数据库的流程
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            sub_pipeline.add_sub_pipeline(
                sub_flow=self.uninstall_instance_sub_flow(ticket_data=ticket_data, cluster_info=one_cluster)
            )
            sub_pipeline_list.append(sub_pipeline.build_sub_process(sub_name=_("定点恢复")))

        mysql_restore_slave_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_restore_slave_pipeline.run_pipeline(init_trans_data_class=ClusterInfoContext())

    # 实例安装子流程
    def install_instance_sub_flow(self, ticket_data: dict, cluster_info: dict):

        install_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))

        # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
        exec_act_kwargs = ExecActuatorKwargs(
            exec_ip=cluster_info["rollback_ip"],
            cluster_type=cluster_info["cluster_type"],
            bk_cloud_id=int(cluster_info["bk_cloud_id"]),
        )

        install_sub_pipeline.add_act(
            act_name=_("下发MySQL介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=int(cluster_info["bk_cloud_id"]),
                    exec_ip=cluster_info["rollback_ip"],
                    file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                        db_version=ticket_data["db_version"]
                    ),
                )
            ),
        )

        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_sys_init_payload.__name__
        install_sub_pipeline.add_act(
            act_name=_("初始化机器"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
        install_sub_pipeline.add_act(
            act_name=_("部署mysql-crond"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_mysql_payload.__name__
        install_sub_pipeline.add_act(
            act_name=_("安装MySQL实例"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        # 安装完毕实例，写入元数据
        install_sub_pipeline.add_act(
            act_name=_("写入初始化实例的db_meta元信息"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.mysql_restore_slave_add_instance.__name__,
                    cluster=cluster_info,
                    is_update_trans_data=True,
                )
            ),
        )

        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_restore_backup_payload.__name__
        install_sub_pipeline.add_act(
            act_name=_("安装备份程序"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        return install_sub_pipeline.build_sub_process(sub_name=_("安装实例flow"))

    # 实例卸载子流程
    def uninstall_instance_sub_flow(self, ticket_data: dict, cluster_info: dict):
        sub_ticket_data = copy.deepcopy(ticket_data)
        sub_ticket_data["force"] = True
        uninstall_sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_ticket_data)

        # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
        exec_act_kwargs = ExecActuatorKwargs(
            exec_ip=cluster_info["rollback_ip"],
            bk_cloud_id=int(cluster_info["bk_cloud_id"]),
            cluster=cluster_info,
        )

        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_mysql_payload.__name__
        uninstall_sub_pipeline.add_act(
            act_name=_("卸载rollback实例{}").format(exec_act_kwargs.exec_ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        # 删除rollback_ip对应的集群实例
        uninstall_sub_pipeline.add_act(
            act_name=_("卸载rollback实例完毕，修改元数据"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.mysql_rollback_remove_instance.__name__,
                    cluster=cluster_info,
                    is_update_trans_data=True,
                )
            ),
        )

        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_machine_crontab.__name__
        uninstall_sub_pipeline.add_act(
            act_name=_("清理机器配置{}").format(exec_act_kwargs.exec_ip),
            act_component_code=MySQLClearMachineComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        return uninstall_sub_pipeline.build_sub_process(sub_name=_("清理机器flow"))
