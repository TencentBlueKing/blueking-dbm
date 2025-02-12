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

from backend.components import DRSApi
from backend.configuration.constants import DBType, MySQLMonitorPauseTime
from backend.constants import IP_PORT_DIVIDER, IP_PORT_DIVIDER_FOR_DNS
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstancePhase, InstanceStatus
from backend.db_meta.exceptions import InstanceNotExistException
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.cluster_entrys import get_standby_dns, get_tendb_ha_entry
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_surrounding_apps_sub_flow,
    install_mysql_in_cluster_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_instance_config
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import mysql_restore_data_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.recover_slave_instance import (
    priv_recover_sub_flow,
    slave_recover_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.common.slave_recover_switch import slave_migrate_switch_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.uninstall_instance import uninstall_instance_sub_flow
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_crond_control import MysqlCrondMonitorControlComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.mysql_rds_execute import MySQLExecuteRdsComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_ports, get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import (
    ClearMachineKwargs,
    CrondMonitorKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    ExecuteRdsKwargs,
    InstanceUserCloneKwargs,
    UpdateDnsRecordKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.ticket.builders.common.constants import MySQLBackupSource

logger = logging.getLogger("flow")


class MySQLRestoreSlaveRemoteFlow(object):
    """
    mysql 重建slave流程接入新备份系统
    """

    def __init__(self, root_id: str, tick_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param tick_data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.ticket_data = tick_data
        self.data = {}
        #  仅添加从库。不切换。不复制账号
        self.add_slave_only = self.ticket_data.get("add_slave_only", False)
        self.local_backup = False
        if self.ticket_data.get("backup_source") == MySQLBackupSource.LOCAL:
            self.local_backup = True

    def tendb_ha_restore_slave_flow(self):
        """
        机器级别重建slave节点的流程
        元数据流程：
        1 mysql_restore_slave_add_instance
        2 mysql_add_slave_info
        3 mysql_restore_slave_change_cluster_info
        4 mysql_restore_remove_old_slave
        """
        cluster_ids = []
        for i in self.ticket_data["infos"]:
            cluster_ids.extend(i["cluster_ids"])
        tendb_migrate_pipeline_all = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        tendb_migrate_pipeline_list = []
        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            cluster_class = Cluster.objects.get(id=self.data["cluster_ids"][0])
            self.data["bk_biz_id"] = cluster_class.bk_biz_id
            self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
            self.data["db_module_id"] = cluster_class.db_module_id
            self.data["time_zone"] = cluster_class.time_zone
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["module"] = cluster_class.db_module_id
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["cluster_type"] = cluster_class.cluster_type
            self.data["uid"] = self.ticket_data["uid"]
            self.data["package"] = Package.get_latest_package(
                version=cluster_class.major_version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL
            ).name
            # self.data["package"] = "5.7.20"
            self.data["ports"] = get_ports(info["cluster_ids"])
            self.data["force"] = self.ticket_data.get("force", False)
            self.data["charset"], self.data["db_version"] = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=self.data["db_module_id"],
                cluster_type=self.data["cluster_type"],
            )
            bk_host_ids = []
            if "bk_new_slave" in self.data.keys():
                bk_host_ids.append(self.data["bk_new_slave"]["bk_host_id"])
            tendb_migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            #  获取信息
            # 整机安装数据库
            master = cluster_class.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
            db_config = get_instance_config(cluster_class.bk_cloud_id, master.machine.ip, self.data["ports"])
            install_sub_pipeline_list = []
            install_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            install_sub_pipeline.add_sub_pipeline(
                sub_flow=install_mysql_in_cluster_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster_class,
                    new_mysql_list=[self.data["new_slave_ip"]],
                    install_ports=self.data["ports"],
                    bk_host_ids=bk_host_ids,
                    db_config=db_config,
                )
            )

            cluster = {
                "install_ip": self.data["new_slave_ip"],
                "cluster_ids": self.data["cluster_ids"],
                "package": self.data["package"],
            }
            install_sub_pipeline.add_act(
                act_name=_("写入初始化实例的db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.slave_recover_add_instance.__name__,
                        cluster=copy.deepcopy(cluster),
                        is_update_trans_data=False,
                    )
                ),
            )

            install_sub_pipeline.add_act(
                act_name=_("安装backup-client工具"),
                act_component_code=DownloadBackupClientComponent.code,
                kwargs=asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        bk_biz_id=int(cluster_class.bk_biz_id),
                        download_host_list=[self.data["new_slave_ip"]],
                    )
                ),
            )

            exec_act_kwargs = ExecActuatorKwargs(
                cluster=cluster,
                bk_cloud_id=cluster_class.bk_cloud_id,
                cluster_type=cluster_class.cluster_type,
                get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
            )
            exec_act_kwargs.exec_ip = [self.data["new_slave_ip"]]
            install_sub_pipeline.add_act(
                act_name=_("安装临时备份程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            install_sub_pipeline_list.append(install_sub_pipeline.build_sub_process(sub_name=_("安装从节点")))

            sync_data_sub_pipeline_list = []
            for cluster_id in info["cluster_ids"]:
                cluster_model = Cluster.objects.get(id=cluster_id)
                master = cluster_model.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
                cluster = {
                    "add_slave_only": self.add_slave_only,
                    "mysql_port": master.port,
                    "cluster_id": cluster_model.id,
                    "cluster_type": cluster_class.cluster_type,
                    "master_ip": master.machine.ip,
                    "master_port": master.port,
                    "new_slave_ip": self.data["new_slave_ip"],
                    "new_slave_port": master.port,
                    "bk_cloud_id": cluster_model.bk_cloud_id,
                    "file_target_path": f"/data/dbbak/{self.root_id}/{master.port}",
                    "charset": self.data["charset"],
                    "change_master_force": True,
                    "change_master": True,
                }
                sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                if self.local_backup:
                    # 获取本地备份并恢复
                    inst_list = ["{}{}{}".format(master.machine.ip, IP_PORT_DIVIDER, master.port)]
                    stand_by_slaves = cluster_model.storageinstance_set.filter(
                        instance_inner_role=InstanceInnerRole.SLAVE.value,
                        is_stand_by=True,
                        status=InstanceStatus.RUNNING.value,
                    ).exclude(machine__ip__in=[self.data["new_slave_ip"]])
                    if len(stand_by_slaves) > 0:
                        inst_list.append(
                            "{}{}{}".format(stand_by_slaves[0].machine.ip, IP_PORT_DIVIDER, stand_by_slaves[0].port)
                        )
                    sync_data_sub_pipeline.add_sub_pipeline(
                        sub_flow=mysql_restore_data_sub_flow(
                            root_id=self.root_id,
                            ticket_data=copy.deepcopy(self.data),
                            cluster=cluster,
                            cluster_model=cluster_model,
                            ins_list=inst_list,
                        )
                    )

                else:
                    sync_data_sub_pipeline.add_sub_pipeline(
                        sub_flow=slave_recover_sub_flow(
                            root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=cluster
                        )
                    )

                    priv_sub_flow = priv_recover_sub_flow(
                        root_id=self.root_id,
                        ticket_data=copy.deepcopy(self.data),
                        cluster_info=cluster,
                        ips=[self.data["new_slave_ip"]],
                    )
                    if priv_sub_flow:
                        sync_data_sub_pipeline.add_sub_pipeline(sub_flow=priv_sub_flow)

                sync_data_sub_pipeline.add_act(
                    act_name=_("同步完毕,写入主从关系,设置节点为running状态"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_add_slave_info.__name__,
                            cluster=cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )

                sync_data_sub_pipeline_list.append(sync_data_sub_pipeline.build_sub_process(sub_name=_("恢复实例数据")))

            switch_sub_pipeline_list = []
            uninstall_svr_sub_pipeline_list = []
            if not self.add_slave_only:
                for cluster_id in self.data["cluster_ids"]:
                    cluster_model = Cluster.objects.get(id=cluster_id)
                    switch_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                    switch_sub_pipeline.add_sub_pipeline(
                        sub_flow=slave_migrate_switch_sub_flow(
                            root_id=self.root_id,
                            ticket_data=copy.deepcopy(self.data),
                            cluster=cluster_model,
                            old_slave_ip=self.data["old_slave_ip"],
                            new_slave_ip=self.data["new_slave_ip"],
                        )
                    )
                    domain_map = get_tendb_ha_entry(cluster_model.id)
                    cluster = {
                        "slave_domain": domain_map[self.data["old_slave_ip"]],
                        "new_slave_ip": self.data["new_slave_ip"],
                        "old_slave_ip": self.data["old_slave_ip"],
                        "cluster_id": cluster_model.id,
                    }
                    switch_sub_pipeline.add_act(
                        act_name=_("slave切换完毕，修改集群 {} 数据".format(cluster_model.id)),
                        act_component_code=MySQLDBMetaComponent.code,
                        kwargs=asdict(
                            DBMetaOPKwargs(
                                db_meta_class_func=MySQLDBMeta.mysql_restore_slave_change_cluster_info.__name__,
                                cluster=cluster,
                                is_update_trans_data=True,
                            )
                        ),
                    )
                    switch_sub_pipeline_list.append(switch_sub_pipeline.build_sub_process(sub_name=_("切换到新从节点")))

                uninstall_svr_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                # cluster = {"uninstall_ip": self.data["old_slave_ip"], "cluster_ids": self.data["cluster_ids"]}
                cluster = {
                    "uninstall_ip": self.data["old_slave_ip"],
                    "ports": self.data["ports"],
                    "bk_cloud_id": cluster_class.bk_cloud_id,
                    "cluster_type": cluster_class.cluster_type,
                }
                uninstall_svr_sub_pipeline.add_act(
                    act_name=_("卸载实例前先删除元数据"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.uninstall_instance.__name__,
                            is_update_trans_data=True,
                            cluster=cluster,
                        )
                    ),
                )
                uninstall_svr_sub_pipeline.add_act(
                    act_name=_("下发db-actor到节点{}".format(self.data["old_slave_ip"])),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=cluster_class.bk_cloud_id,
                            exec_ip=[self.data["old_slave_ip"]],
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                )
                uninstall_svr_sub_pipeline.add_act(
                    act_name=_("清理机器配置"),
                    act_component_code=MySQLClearMachineComponent.code,
                    kwargs=asdict(
                        ClearMachineKwargs(
                            exec_ip=self.data["old_slave_ip"],
                            bk_cloud_id=cluster_class.bk_cloud_id,
                        )
                    ),
                )
                uninstall_svr_sub_pipeline.add_sub_pipeline(
                    sub_flow=uninstall_instance_sub_flow(
                        root_id=self.root_id,
                        ticket_data=copy.deepcopy(self.data),
                        ip=self.data["old_slave_ip"],
                        ports=self.data["ports"],
                    )
                )
                uninstall_svr_sub_pipeline_list.append(
                    uninstall_svr_sub_pipeline.build_sub_process(
                        sub_name=_("卸载remote节点{}".format(self.data["old_slave_ip"]))
                    )
                )

            # 安装实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=install_sub_pipeline_list)
            # 数据同步
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
            #  新机器安装周边组件
            tendb_migrate_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    master_ip_list=None,
                    slave_ip_list=[self.data["new_slave_ip"]],
                    root_id=self.root_id,
                    is_install_backup=False,
                    parent_global_data=copy.deepcopy(self.data),
                    cluster_type=ClusterType.TenDBHA.value,
                )
            )
            tendb_migrate_pipeline.add_act(
                act_name=_("屏蔽监控 {}").format(self.data["new_slave_ip"]),
                act_component_code=MysqlCrondMonitorControlComponent.code,
                kwargs=asdict(
                    CrondMonitorKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        exec_ips=[self.data["new_slave_ip"]],
                        port=0,
                        minutes=MySQLMonitorPauseTime.SLAVE_DELAY,
                    )
                ),
            )

            if not self.add_slave_only:
                # 人工确认切换迁移实例
                tendb_migrate_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})
                # 切换迁移实例
                tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_pipeline_list)
                # 切换后再次刷新周边
                tendb_migrate_pipeline.add_sub_pipeline(
                    sub_flow=build_surrounding_apps_sub_flow(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        master_ip_list=[master.machine.ip],
                        slave_ip_list=[self.data["new_slave_ip"]],
                        root_id=self.root_id,
                        parent_global_data=copy.deepcopy(self.data),
                        is_init=False,
                        cluster_type=ClusterType.TenDBHA.value,
                    )
                )
                tendb_migrate_pipeline.add_act(
                    act_name=_("切换后解除屏蔽监控 {}").format(self.data["new_slave_ip"]),
                    act_component_code=MysqlCrondMonitorControlComponent.code,
                    kwargs=asdict(
                        CrondMonitorKwargs(
                            bk_cloud_id=cluster_class.bk_cloud_id,
                            exec_ips=[self.data["new_slave_ip"]],
                            port=0,
                            enable=True,
                        )
                    ),
                )
                # 卸载流程人工确认
                tendb_migrate_pipeline.add_act(
                    act_name=_("人工确认卸载实例"), act_component_code=PauseComponent.code, kwargs={}
                )
                # # 卸载remote节点
                tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_svr_sub_pipeline_list)
            tendb_migrate_pipeline_list.append(
                tendb_migrate_pipeline.build_sub_process(_("slave重建迁移{}").format(self.data["new_slave_ip"]))
            )
        # 运行流程
        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(tendb_migrate_pipeline_list)
        tendb_migrate_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)

    def restore_local_slave_flow(self):
        """
        原地重建slave
        机器slave数据损坏或者其他原因丢弃实例数据，重新恢复数据。
        无元数据改动
        """
        cluster_ids = [i["cluster_id"] for i in self.ticket_data["infos"]]
        tendb_migrate_pipeline_all = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        tendb_migrate_pipeline_list = []
        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            cluster_model = Cluster.objects.get(id=self.data["cluster_id"])
            target_slave = cluster_model.storageinstance_set.get(
                machine__bk_cloud_id=cluster_model.bk_cloud_id,
                machine__ip=self.data["slave_ip"],
                port=self.data["slave_port"],
            )

            res = DRSApi.rpc(
                {
                    "addresses": [target_slave.ip_port],
                    "cmds": ["select version()"],
                    "force": False,
                    "bk_cloud_id": target_slave.machine.bk_cloud_id,
                }
            )
            if res[0]["error_msg"]:
                raise InstanceNotExistException(
                    _("请检查实例 {} 是否存活,是否正常可访问，slave原地重建是实例级别的，且必须保证实例存活方可提单进行").format(target_slave.ip_port)
                )

            master = cluster_model.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
            self.data["new_slave_ip"] = target_slave.machine.ip
            self.data["bk_biz_id"] = cluster_model.bk_biz_id
            self.data["bk_cloud_id"] = cluster_model.bk_cloud_id
            self.data["db_module_id"] = cluster_model.db_module_id
            self.data["time_zone"] = cluster_model.time_zone
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["module"] = cluster_model.db_module_id
            self.data["force"] = self.ticket_data.get("force", False)
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["cluster_type"] = cluster_model.cluster_type
            self.data["uid"] = self.ticket_data["uid"]
            self.data["charset"], self.data["db_version"] = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=self.data["db_module_id"],
                cluster_type=self.data["cluster_type"],
            )
            tendb_migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))

            tendb_migrate_pipeline.add_act(
                act_name=_("下发db-actor到节点{}".format(target_slave.machine.ip)),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster_model.bk_cloud_id,
                        exec_ip=[target_slave.machine.ip, master.machine.ip],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            cluster = {
                "phase": InstancePhase.TRANS_STAGE.value,
                "storage_status": InstanceStatus.RESTORING.value,
                "storage_id": target_slave.id,
            }
            tendb_migrate_pipeline.add_act(
                act_name=_("写入初始化实例的db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.tendb_modify_storage_status.__name__,
                        cluster=cluster,
                        is_update_trans_data=False,
                    )
                ),
            )

            cluster = {
                "stop_slave": True,
                "reset_slave": True,
                "restart": False,
                "force": self.data["force"],
                "drop_database": True,
                "new_slave_ip": target_slave.machine.ip,
                "new_slave_port": target_slave.port,
            }
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=cluster_model.bk_cloud_id,
                cluster_type=cluster_model.cluster_type,
                cluster=cluster,
                exec_ip=target_slave.machine.ip,
            )
            # 屏蔽
            tendb_migrate_pipeline.add_act(
                act_name=_("数据恢复屏蔽监控 {}").format(target_slave.ip_port),
                act_component_code=MysqlCrondMonitorControlComponent.code,
                kwargs=asdict(
                    CrondMonitorKwargs(
                        bk_cloud_id=cluster_model.bk_cloud_id,
                        exec_ips=[target_slave.machine.ip],
                        port=target_slave.port,
                        minutes=MySQLMonitorPauseTime.RESTORE_DATA,
                    )
                ),
            )

            tendb_migrate_pipeline.add_act(
                act_name=_("从库reset slave {}").format(target_slave.ip_port),
                act_component_code=MySQLExecuteRdsComponent.code,
                kwargs=asdict(
                    ExecuteRdsKwargs(
                        bk_cloud_id=cluster_model.bk_cloud_id,
                        instance_ip=target_slave.machine.ip,
                        instance_port=target_slave.port,
                        sqls=["stop slave", "reset slave all"],
                    )
                ),
            )

            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clean_mysql_payload.__name__
            tendb_migrate_pipeline.add_act(
                act_name=_("slave重建之清理从库{}").format(target_slave.ip_port),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_change_server_id.__name__
            tendb_migrate_pipeline.add_act(
                act_name=_("重置server_id {}".format(exec_act_kwargs.exec_ip)),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            cluster = {
                "cluster_id": cluster_model.id,
                "master_ip": master.machine.ip,
                "master_port": master.port,
                "new_slave_ip": target_slave.machine.ip,
                "new_slave_port": target_slave.port,
                "bk_cloud_id": cluster_model.bk_cloud_id,
                "file_target_path": f"/data/dbbak/{self.root_id}/{master.port}",
                "charset": self.data["charset"],
                "change_master_force": True,
                "cluster_type": cluster_model.cluster_type,
                "change_master": True,
            }

            if self.local_backup:
                inst_list = ["{}{}{}".format(master.machine.ip, IP_PORT_DIVIDER, master.port)]
                tendb_migrate_pipeline.add_sub_pipeline(
                    sub_flow=mysql_restore_data_sub_flow(
                        root_id=self.root_id,
                        ticket_data=copy.deepcopy(self.data),
                        cluster=cluster,
                        cluster_model=cluster_model,
                        ins_list=inst_list,
                    )
                )
            else:
                tendb_migrate_pipeline.add_sub_pipeline(
                    sub_flow=slave_recover_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=cluster
                    )
                )
                priv_sub_flow = priv_recover_sub_flow(
                    root_id=self.root_id,
                    ticket_data=copy.deepcopy(self.data),
                    cluster_info=cluster,
                    ips=[target_slave.machine.ip],
                )
                if priv_sub_flow:
                    tendb_migrate_pipeline.add_sub_pipeline(sub_flow=priv_sub_flow)

            # 屏蔽
            tendb_migrate_pipeline.add_act(
                act_name=_("数据同步屏蔽监控 {}").format(target_slave.ip_port),
                act_component_code=MysqlCrondMonitorControlComponent.code,
                kwargs=asdict(
                    CrondMonitorKwargs(
                        bk_cloud_id=cluster_model.bk_cloud_id,
                        exec_ips=[target_slave.machine.ip],
                        port=target_slave.port,
                        minutes=MySQLMonitorPauseTime.SLAVE_DELAY,
                    )
                ),
            )
            # 卸载流程人工确认
            tendb_migrate_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            #  克隆权限
            new_slave = "{}{}{}".format(target_slave.machine.ip, IP_PORT_DIVIDER, master.port)
            old_master = "{}{}{}".format(master.machine.ip, IP_PORT_DIVIDER, master.port)
            clone_data = [
                {
                    "source": old_master,
                    "target": new_slave,
                    "bk_cloud_id": cluster_model.bk_cloud_id,
                }
            ]
            tendb_migrate_pipeline.add_act(
                act_name=_("克隆权限"),
                act_component_code=CloneUserComponent.code,
                kwargs=asdict(InstanceUserCloneKwargs(clone_data=clone_data)),
            )

            # 这里区分是standby还是普通salve添加域名
            if target_slave.is_stand_by:
                domain_map = get_standby_dns(cluster_model.id)
                domain_add_list = []
                for old_instance, domain in domain_map.items():
                    domain_add_list.append(
                        {
                            "act_name": _("添加Standby从库域名{}:{}").format(target_slave.machine.ip, domain),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                UpdateDnsRecordKwargs(
                                    bk_cloud_id=cluster_model.bk_cloud_id,
                                    old_instance=old_instance,
                                    new_instance="{}{}{}".format(
                                        target_slave.machine.ip, IP_PORT_DIVIDER_FOR_DNS, master.port
                                    ),
                                    update_domain_name=domain,
                                )
                            ),
                        }
                    )
                if len(domain_add_list) > 0:
                    tendb_migrate_pipeline.add_parallel_acts(acts_list=domain_add_list)
                # 如果域名来源于从库，可能需要修正元数据entry
                cluster = {
                    "cluster_id": cluster_model.id,
                    "new_slave_ip": target_slave.machine.ip,
                    "old_slave_ip": target_slave.machine.ip,
                    "slave_domain": [domain for domain in domain_map.values()],
                }
                tendb_migrate_pipeline.add_act(
                    act_name=_("slave切换完毕，修改standby{}数据".format(target_slave.ip_port)),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_restore_slave_change_cluster_info.__name__,
                            cluster=cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
            else:
                # 非standby节点则刷新域名
                domain_map = get_tendb_ha_entry(cluster_model.id)
                domain_add_list = []
                for domain in domain_map[target_slave.machine.ip]:
                    domain_add_list.append(
                        {
                            "act_name": _("添加从库域名{}:{}").format(target_slave.machine.ip, domain),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                UpdateDnsRecordKwargs(
                                    bk_cloud_id=cluster_model.bk_cloud_id,
                                    old_instance="{}#{}".format(target_slave.machine.ip, master.port),
                                    new_instance="{}#{}".format(target_slave.machine.ip, master.port),
                                    update_domain_name=domain,
                                )
                            ),
                        }
                    )
                if len(domain_add_list) > 0:
                    tendb_migrate_pipeline.add_parallel_acts(acts_list=domain_add_list)
                cluster = {
                    "phase": InstancePhase.ONLINE.value,
                    "storage_status": InstanceStatus.RUNNING.value,
                    "storage_id": target_slave.id,
                }
                tendb_migrate_pipeline.add_act(
                    act_name=_("同步完毕,修改{}元数据".format(target_slave.ip_port)),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.tendb_modify_storage_status.__name__,
                            cluster=cluster,
                            is_update_trans_data=False,
                        )
                    ),
                )

            tendb_migrate_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=cluster_model.bk_cloud_id,
                    master_ip_list=[master.machine.ip],
                    slave_ip_list=[target_slave.machine.ip],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(self.data),
                    cluster_type=ClusterType.TenDBHA.value,
                )
            )
            tendb_migrate_pipeline.add_act(
                act_name=_("切换后解除屏蔽监控 {}").format(self.data["new_slave_ip"]),
                act_component_code=MysqlCrondMonitorControlComponent.code,
                kwargs=asdict(
                    CrondMonitorKwargs(
                        bk_cloud_id=cluster_model.bk_cloud_id,
                        exec_ips=[target_slave.machine.ip],
                        port=target_slave.port,
                        enable=True,
                    )
                ),
            )

            tendb_migrate_pipeline_list.append(
                tendb_migrate_pipeline.build_sub_process(_("{}slave原地重建").format(target_slave.ip_port))
            )

        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(sub_flow_list=tendb_migrate_pipeline_list)
        tendb_migrate_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)
