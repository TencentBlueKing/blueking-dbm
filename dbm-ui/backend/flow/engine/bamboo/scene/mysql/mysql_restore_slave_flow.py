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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_services.mysql.permission.constants import CloneType
from backend.flow.consts import AUTH_ADDRESS_DIVIDER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import build_surrounding_apps_sub_flow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.slave_trans_flies import SlaveTransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import (
    get_cluster_info,
    get_cluster_ports,
    get_version_and_charset,
)
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    P2PFileKwargs,
    RecycleDnsRecordKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLRestoreSlaveFlow(object):
    """
    mysql 重建slave流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

        # 定义备份文件存放到目标机器目录位置
        self.backup_target_path = f"/data/dbbak/{self.root_id}"

    def deploy_restore_slave_flow(self):
        """
        重建slave节点的流程
        元数据流程：
        1 mysql_restore_slave_add_instance
        2 mysql_add_slave_info
        3 mysql_restore_slave_change_cluster_info
        4 mysql_restore_remove_old_slave
        """
        mysql_restore_slave_pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.data))
        sub_pipeline_list = []
        for one_machine in self.data["infos"]:
            ticket_data = copy.deepcopy(self.data)
            cluster_ports = get_cluster_ports(one_machine["cluster_ids"])
            one_machine.update(cluster_ports)

            charset, db_version = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=one_machine["db_module_id"],
                cluster_type=one_machine["cluster_type"],
            )
            ticket_data["clusters"] = one_machine["clusters"]
            ticket_data["mysql_ports"] = one_machine["cluster_ports"]
            ticket_data["charset"] = charset
            ticket_data["db_version"] = db_version
            ticket_data["force"] = one_machine.get("force", False)

            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
            sub_pipeline.add_sub_pipeline(
                sub_flow=self.install_instance_sub_flow(ticket_data=ticket_data, one_machine=one_machine)
            )

            slave_restore_sub_list = []
            clusters_info = []
            sub_pipeline_list = []
            for one_id in one_machine["cluster_ids"]:
                one_cluster = get_cluster_info(one_id)
                if one_cluster is None:
                    logger.info(_("%s slave 节点不存在"), one_id)
                    continue

                one_cluster["backend_port"] = one_cluster["master_port"]
                one_cluster["new_master_ip"] = one_cluster["master_ip"]
                one_cluster["new_slave_ip"] = one_machine["new_slave_ip"]
                # 指定传入的slave实例
                one_cluster["old_slave_ip"] = one_machine["old_slave_ip"]
                one_cluster["charset"] = charset
                one_cluster["change_master"] = True
                one_cluster["file_target_path"] = self.backup_target_path
                clusters_info.append(one_cluster)

                restore_slave_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
                # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
                exec_act_kwargs = ExecActuatorKwargs(
                    bk_cloud_id=one_cluster["bk_cloud_id"],
                    cluster_type=one_cluster["cluster_type"],
                    cluster=one_cluster,
                )

                restore_slave_sub_pipeline.add_act(
                    act_name=_("下发db-actor到集群主从节点"),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            exec_ip=[
                                one_cluster["master_ip"],
                                one_cluster["old_slave_ip"],
                                one_cluster["new_slave_ip"],
                            ],
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                )

                exec_act_kwargs.exec_ip = one_cluster["new_master_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_grant_mysql_repl_user_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("slave重建之新增repl帐户{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="master_ip_sync_info",
                )

                # 通过master、slave 获取备份的文件
                # acts_list = []  并行获取备份介质暂时存在问题，先改为串行
                exec_act_kwargs.exec_ip = one_cluster["master_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("slave重建之获取MASTER节点备份介质{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="master_backup_file",
                )

                exec_act_kwargs.exec_ip = one_cluster["old_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("slave重建之获取SLAVE节点备份介质{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="slave_backup_file",
                )

                restore_slave_sub_pipeline.add_act(
                    act_name=_("判断备份文件来源,并传输备份文件到新slave节点{}").format(one_cluster["new_slave_ip"]),
                    act_component_code=SlaveTransFileComponent.code,
                    kwargs=asdict(
                        P2PFileKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            file_list=[],
                            file_target_path=self.backup_target_path,
                            source_ip_list=[],
                            exec_ip=one_cluster["new_slave_ip"],
                        )
                    ),
                )

                exec_act_kwargs.exec_ip = one_cluster["new_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_restore_slave_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("恢复新从节点数据{}:{}").format(exec_act_kwargs.exec_ip, one_cluster["backend_port"]),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )

                restore_slave_sub_pipeline.add_act(
                    act_name=_("slave恢复完毕，修改元数据"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_add_slave_info.__name__,
                            cluster=one_cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                slave_restore_sub_list.append(restore_slave_sub_pipeline.build_sub_process(sub_name=_("恢复实例数据")))

            switch_slave_sub_list = []
            for one_cluster in clusters_info:
                switch_slave_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
                master_port = one_cluster["master_port"]
                clone_user = {
                    "clone_type": CloneType.INSTANCE.value,
                    "clone_data": [
                        {
                            "source": f'{one_cluster["master_ip"]}{AUTH_ADDRESS_DIVIDER}{master_port}',
                            "target": f'{one_cluster["new_slave_ip"]}{AUTH_ADDRESS_DIVIDER}{master_port}',
                            "bk_cloud_id": one_cluster["bk_cloud_id"],
                        }
                    ],
                }
                switch_slave_sub_pipeline.add_act(
                    act_name=_("克隆主节点账号权限到新从节点"),
                    act_component_code=CloneUserComponent.code,
                    kwargs=clone_user,
                )

                switch_slave_sub_pipeline.add_act(
                    act_name=_("先添加新从库域名{}").format(one_cluster["new_slave_ip"]),
                    act_component_code=MySQLDnsManageComponent.code,
                    kwargs=asdict(
                        CreateDnsKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            dns_op_exec_port=master_port,
                            exec_ip=one_cluster["new_slave_ip"],
                            add_domain_name=one_cluster["slave_domain"],
                        )
                    ),
                )

                switch_slave_sub_pipeline.add_act(
                    act_name=_("再删除旧从库域名{}").format(one_cluster["old_slave_ip"]),
                    act_component_code=MySQLDnsManageComponent.code,
                    kwargs=asdict(
                        RecycleDnsRecordKwargs(
                            dns_op_exec_port=master_port,
                            exec_ip=one_cluster["old_slave_ip"],
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                        )
                    ),
                )

                # 恢复单个实例完毕,修改元数据、修改 db_meta_storageinstance_bind_entry  db_meta_clusterentry
                switch_slave_sub_pipeline.add_act(
                    act_name=_("slave切换完毕，修改集群 {} 数据".format(one_cluster["cluster_id"])),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_restore_slave_change_cluster_info.__name__,
                            cluster=one_cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                switch_slave_sub_list.append(switch_slave_sub_pipeline.build_sub_process(_("实例切换")))

                # 第三部...
            uninstall_slave_sub_list = []
            for one_cluster in clusters_info:
                uninstall_slave_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
                exec_act_kwargs = ExecActuatorKwargs(
                    bk_cloud_id=one_cluster["bk_cloud_id"],
                    cluster_type=one_cluster["cluster_type"],
                    cluster=one_cluster,
                )
                exec_act_kwargs.exec_ip = one_cluster["old_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_surrounding_config_payload.__name__
                uninstall_slave_sub_pipeline.add_act(
                    act_name=_("清理实例级别周边配置"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )

                exec_act_kwargs.exec_ip = one_cluster["old_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_mysql_payload.__name__
                uninstall_slave_sub_pipeline.add_act(
                    act_name=_("卸载mysql实例{}:{}").format(exec_act_kwargs.exec_ip, one_cluster["backend_port"]),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )

                uninstall_slave_sub_pipeline.add_act(
                    act_name=_("old slave卸载完毕，修改元数据"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_restore_remove_old_slave.__name__,
                            cluster=one_cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                uninstall_slave_sub_list.append(uninstall_slave_sub_pipeline.build_sub_process(_("卸载实例")))
            # 流程: 恢复数据>切换>安装周边>卸载
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=slave_restore_sub_list)
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_slave_sub_list)
            # 第三步 安装周边
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=one_machine["bk_cloud_id"],
                    slave_ip_list=[one_machine["new_slave_ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(ticket_data),
                    is_init=True,
                    cluster_type=one_machine["cluster_type"],
                )
            )
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_slave_sub_list)

            sub_pipeline.add_sub_pipeline(
                sub_flow=self.uninstall_instance_sub_flow(ticket_data=ticket_data, one_machine=one_machine)
            )

            sub_pipeline_list.append(sub_pipeline.build_sub_process(sub_name=_("Restore Slave 重建从库")))
        mysql_restore_slave_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_restore_slave_pipeline.run_pipeline(init_trans_data_class=ClusterInfoContext())

    def deploy_restore_local_slave_flow(self):
        """
        原地重建slave
        机器slave数据损坏或者其他原因丢弃实例数据，重新恢复数据。
        无元数据改动
        """
        mysql_restore_local_slave_pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.data))
        sub_pipeline_list = []
        for slave in self.data["infos"]:
            ticket_data = copy.deepcopy(self.data)
            one_cluster = get_cluster_info(slave["cluster_id"])
            # if not (
            #         slave["slave_ip"] in one_cluster["slave_ip"] and slave["slave_port"] == one_cluster["master_port"]
            # ):
            #     continue
            # 检查master local backup> 清理原实例> 恢复
            # 通过master、slave 获取备份的文件
            charset, db_version = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=one_cluster["db_module_id"],
                cluster_type=one_cluster["cluster_type"],
            )
            one_cluster["backend_port"] = one_cluster["master_port"]
            one_cluster["new_slave_ip"] = slave["slave_ip"]
            one_cluster["new_slave_port"] = slave["slave_port"]
            one_cluster["charset"] = charset
            one_cluster["change_master"] = True
            one_cluster["drop_database"] = True
            one_cluster["force"] = False
            one_cluster["restart"] = False
            one_cluster["stop_slave"] = True
            one_cluster["reset_slave"] = True
            one_cluster["file_target_path"] = self.backup_target_path

            restore_local_slave_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=one_cluster["bk_cloud_id"],
                cluster_type=one_cluster["cluster_type"],
                cluster=one_cluster,
            )

            restore_local_slave_sub_pipeline.add_act(
                act_name=_("下发db-actor到集群主从节点"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=one_cluster["bk_cloud_id"],
                        exec_ip=[one_cluster["master_ip"], one_cluster["new_slave_ip"]],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            exec_act_kwargs.exec_ip = one_cluster["master_ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
            restore_local_slave_sub_pipeline.add_act(
                act_name=_("slave重建之获取MASTER节点备份介质{}").format(exec_act_kwargs.exec_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
                write_payload_var="master_backup_file",
            )

            exec_act_kwargs.exec_ip = one_cluster["new_slave_ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clean_mysql_payload.__name__
            restore_local_slave_sub_pipeline.add_act(
                act_name=_("slave重建之清理从库{}").format(exec_act_kwargs.exec_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            restore_local_slave_sub_pipeline.add_act(
                act_name=_("判断备份文件来源,并传输备份文件到新slave节点{}").format(one_cluster["new_slave_ip"]),
                act_component_code=SlaveTransFileComponent.code,
                kwargs=asdict(
                    P2PFileKwargs(
                        bk_cloud_id=one_cluster["bk_cloud_id"],
                        file_list=[],
                        file_target_path=self.backup_target_path,
                        source_ip_list=[],
                        exec_ip=one_cluster["new_slave_ip"],
                    )
                ),
            )

            exec_act_kwargs.exec_ip = one_cluster["new_slave_ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_restore_slave_payload.__name__
            restore_local_slave_sub_pipeline.add_act(
                act_name=_("slave 原地恢复数据{}").format(exec_act_kwargs.exec_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )
            sub_pipeline_list.append(
                restore_local_slave_sub_pipeline.build_sub_process(sub_name=_("Restore local Slave 本地重建"))
            )
        mysql_restore_local_slave_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_restore_local_slave_pipeline.run_pipeline(init_trans_data_class=ClusterInfoContext())

    def deploy_add_slave_flow(self):
        """
        添加从库：仅添加从库、不拷贝权限、不加入域名
        """
        mysql_restore_slave_pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.data))
        sub_pipeline_list = []

        for one_machine in self.data["infos"]:
            ticket_data = copy.deepcopy(self.data)
            cluster_ports = get_cluster_ports(one_machine["cluster_ids"])
            one_machine.update(cluster_ports)
            charset, db_version = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=one_machine["db_module_id"],
                cluster_type=one_machine["cluster_type"],
            )
            ticket_data["clusters"] = one_machine["clusters"]
            ticket_data["mysql_ports"] = one_machine["cluster_ports"]
            ticket_data["charset"] = charset
            ticket_data["db_version"] = db_version
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
            sub_pipeline.add_sub_pipeline(
                sub_flow=self.install_instance_sub_flow(ticket_data=ticket_data, one_machine=one_machine)
            )

            slave_restore_sub_list = []
            for one_id in one_machine["cluster_ids"]:
                one_cluster = get_cluster_info(one_id)
                # if one_cluster is None:
                #     logger.info(_("%s slave 节点不存在"), one_id)
                #     continue
                one_cluster["backend_port"] = one_cluster["master_port"]
                one_cluster["new_master_ip"] = one_cluster["master_ip"]
                one_cluster["new_slave_ip"] = one_machine["new_slave_ip"]
                one_cluster["charset"] = charset
                one_cluster["change_master"] = True
                one_cluster["file_target_path"] = self.backup_target_path

                ticket_data["force"] = one_machine.get("force", False)
                restore_slave_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))

                # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
                exec_act_kwargs = ExecActuatorKwargs(
                    bk_cloud_id=one_cluster["bk_cloud_id"],
                    cluster_type=one_cluster["cluster_type"],
                    cluster=one_cluster,
                )

                restore_slave_sub_pipeline.add_act(
                    act_name=_("下发db-actor到集群主从节点"),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            exec_ip=[
                                one_cluster["master_ip"],
                                one_cluster["old_slave_ip"],
                                one_cluster["new_slave_ip"],
                            ],
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                )

                exec_act_kwargs.exec_ip = one_cluster["new_master_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_grant_mysql_repl_user_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("添加slave之新增repl帐户{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var=ClusterInfoContext.get_sync_info_var_name(),
                )

                # 通过master、slave 获取备份的文件
                # acts_list = []  并行获取备份介质暂时存在问题，先改为串行
                exec_act_kwargs.exec_ip = one_cluster["master_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("添加slave之获取MASTER节点备份介质{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="master_backup_file",
                )

                exec_act_kwargs.exec_ip = one_cluster["old_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_find_local_backup_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("添加slave之获取SLAVE节点备份介质{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                    write_payload_var="slave_backup_file",
                )

                restore_slave_sub_pipeline.add_act(
                    act_name=_("判断备份文件来源,并传输备份文件到新slave节点{}").format(one_cluster["new_slave_ip"]),
                    act_component_code=SlaveTransFileComponent.code,
                    kwargs=asdict(
                        P2PFileKwargs(
                            bk_cloud_id=one_cluster["bk_cloud_id"],
                            file_list=[],
                            file_target_path=self.backup_target_path,
                            source_ip_list=[],
                            exec_ip=one_cluster["new_slave_ip"],
                        )
                    ),
                )

                exec_act_kwargs.exec_ip = one_cluster["new_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_restore_slave_payload.__name__
                restore_slave_sub_pipeline.add_act(
                    act_name=_("添加slave之恢复数据{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )

                restore_slave_sub_pipeline.add_act(
                    act_name=_("slave恢复完毕，修改元数据"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_add_slave_info.__name__,
                            cluster=one_cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                slave_restore_sub_list.append(
                    restore_slave_sub_pipeline.build_sub_process(sub_name=_("添加Slave之恢复slave"))
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=slave_restore_sub_list)
            sub_pipeline_list.append(sub_pipeline.build_sub_process(sub_name=_("添加从库flow")))

        mysql_restore_slave_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_restore_slave_pipeline.run_pipeline(init_trans_data_class=ClusterInfoContext())

    def install_instance_sub_flow(self, ticket_data: dict, one_machine: dict):
        #  通过集群级别去获取id
        install_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))

        # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
        exec_act_kwargs = ExecActuatorKwargs(
            exec_ip=one_machine["new_slave_ip"],
            cluster_type=one_machine["cluster_type"],
            bk_cloud_id=one_machine["bk_cloud_id"],
        )

        install_sub_pipeline.add_act(
            act_name=_("下发MySQL介质{}").format(one_machine["new_slave_ip"]),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=one_machine["bk_cloud_id"],
                    exec_ip=one_machine["new_slave_ip"],
                    file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                        db_version=ticket_data["db_version"]
                    ),
                )
            ),
        )

        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_sys_init_payload.__name__
        install_sub_pipeline.add_act(
            act_name=_("初始化机器{}").format(one_machine["new_slave_ip"]),
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
            act_name=_("安装MySQL实例{}").format(one_machine["new_slave_ip"]),
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
                    cluster=one_machine,
                    is_update_trans_data=True,
                )
            ),
        )

        # 新slave安装周边组件
        install_sub_pipeline.add_sub_pipeline(
            sub_flow=build_surrounding_apps_sub_flow(
                bk_cloud_id=one_machine["bk_cloud_id"],
                slave_ip_list=[one_machine["new_slave_ip"]],
                cluster_type=one_machine["cluster_type"],
                is_init=True,
                root_id=self.root_id,
                parent_global_data=copy.deepcopy(ticket_data),
            )
        )

        return install_sub_pipeline.build_sub_process(sub_name=_("安装实例flow"))

    def uninstall_instance_sub_flow(self, ticket_data: dict, one_machine: dict):

        uninstall_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))

        uninstall_sub_pipeline.add_act(
            act_name=_("清理机器配置{}").format(one_machine["old_slave_ip"]),
            act_component_code=MySQLClearMachineComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=one_machine["old_slave_ip"],
                    bk_cloud_id=one_machine["bk_cloud_id"],
                    get_mysql_payload_func=MysqlActPayload.get_clear_machine_crontab.__name__,
                )
            ),
        )
        return uninstall_sub_pipeline.build_sub_process(sub_name=_("清理机器flow"))
