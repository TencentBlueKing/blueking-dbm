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

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER, IP_PORT_DIVIDER_FOR_DNS
from backend.db_meta.enums import InstanceInnerRole, InstancePhase, InstanceStatus
from backend.db_meta.exceptions import InstanceNotExistException
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.clone_grants_from_file.subflow import mysql_clone_grants_from_file_subflow
from backend.flow.engine.bamboo.scene.mysql.common.cluster_entrys import get_tendb_ha_entry
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import install_mysql_in_cluster_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_instance_config
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import mysql_restore_data_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.slave_recover_switch import slave_migrate_switch_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.uninstall_instance import uninstall_instance_sub_flow
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    ALLDEPARTS,
    DeployPeripheralToolsDepart,
    remove_departs,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import (
    standardize_mysql_cluster_by_ip_subflow,
    standardize_mysql_cluster_subflow,
)
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_check_binlog_dump import MySQLCheckBinlogDumpComponent
from backend.flow.plugins.components.collections.mysql.mysql_check_processlist import MySQLCheckProcesslistComponent
from backend.flow.plugins.components.collections.mysql.mysql_check_slave_delay import MySQLCheckSlaveDelayComponent
from backend.flow.plugins.components.collections.mysql.mysql_check_slave_delay_probe import (
    MySQLCheckSlaveDelayProbeComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_crond_control import MysqlCrondMonitorControlComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.mysql_rds_execute import MySQLExecuteRdsComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_ports, get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckSlaveStatusKwargs,
    ClearMachineKwargs,
    CreateDnsKwargs,
    CrondMonitorKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    ExecuteRdsKwargs,
    IpDnsRecordRecycleKwargs,
    RecycleDnsRecordKwargs,
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
        self.auto_switch_slave = self.ticket_data.get("auto_switch_slave", False)
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
        # 用于治愈自动重建的: 这里会自动切换到重建好的新节点、并自动下架机器。
        disable_manual_confirm = self.ticket_data.get("disable_manual_confirm", False)
        if disable_manual_confirm:
            self.auto_switch_slave = True

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
                        ip_list=[self.data["new_slave_ip"]],
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
            master_instances = []
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
                    "backup_source": self.ticket_data.get("backup_source"),
                    "change_master_force": True,
                }
                master_instances.append(master.ip_port)
                if not self.add_slave_only:
                    cluster["restore_privilege"] = True
                    cluster["privilege_ips"] = [self.data["old_slave_ip"]]
                    check_slave = cluster_class.storageinstance_set.get(
                        machine__ip=self.data["old_slave_ip"], port=master.port
                    )
                    cluster["is_stand_by"] = check_slave.is_stand_by

                if self.ticket_data.get("backup_source") == MySQLBackupSource.LOCAL:
                    filter_ips = [master.machine.ip]
                    stand_by_slaves = cluster_model.storageinstance_set.filter(
                        instance_inner_role=InstanceInnerRole.SLAVE.value,
                        is_stand_by=True,
                        status=InstanceStatus.RUNNING.value,
                    )
                    filter_ips.extend([slave.machine.ip for slave in stand_by_slaves])
                else:
                    filter_ips = None
                sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                sync_data_sub_pipeline.add_sub_pipeline(
                    sub_flow=mysql_restore_data_sub_flow(
                        root_id=self.root_id,
                        ticket_data=copy.deepcopy(self.data),
                        cluster=cluster,
                        cluster_model=cluster_model,
                        filter_ips=filter_ips,
                    )
                )

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
                has_unavailable_instance = StorageInstance.objects.filter(
                    machine__ip=self.data.get("old_slave_ip", None),
                    instance_inner_role=InstanceInnerRole.SLAVE.value,
                    status=InstanceStatus.UNAVAILABLE.value,
                    machine__bk_cloud_id=self.data["bk_cloud_id"],
                    bk_biz_id=self.data["bk_biz_id"],
                ).exists()
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
                            auto_switch_slave=self.auto_switch_slave,
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
                    switch_sub_pipeline.add_act(
                        act_name=_("切换后屏蔽旧实例备份 {}").format(self.data["old_slave_ip"]),
                        act_component_code=MysqlCrondMonitorControlComponent.code,
                        kwargs=asdict(
                            CrondMonitorKwargs(
                                bk_cloud_id=cluster_class.bk_cloud_id,
                                exec_ips=[self.data["old_slave_ip"]],
                                name="dbbackup",
                                port=master.port,
                            )
                        ),
                        error_ignorable=has_unavailable_instance,
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
                    error_ignorable=has_unavailable_instance,
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
                    error_ignorable=has_unavailable_instance,
                )
                uninstall_svr_sub_pipeline.add_sub_pipeline(
                    sub_flow=uninstall_instance_sub_flow(
                        root_id=self.root_id,
                        ticket_data=copy.deepcopy(self.data),
                        ip=self.data["old_slave_ip"],
                        ports=self.data["ports"],
                        error_ignorable=has_unavailable_instance,
                    )
                )
                uninstall_svr_sub_pipeline_list.append(
                    uninstall_svr_sub_pipeline.build_sub_process(
                        sub_name=_("卸载remote节点{}".format(self.data["old_slave_ip"]))
                    )
                )
            # === 主流程 ===
            # 安装实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=install_sub_pipeline_list)
            instances = ["{}:{}".format(self.data["new_slave_ip"], port) for port in self.data["ports"]]
            tendb_migrate_pipeline.add_act(
                act_name=_("屏蔽告警24小时"),
                act_component_code=AddAlarmShieldComponent.code,
                kwargs={
                    "duration_seconds": 24 * 3600,
                    "description": str(instances),
                    "dimensions": [
                        {
                            "name": "instance_host",
                            "values": [self.data["new_slave_ip"]],
                        }
                    ],
                },
            )
            # 数据同步
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
            if self.add_slave_only:
                # 如果是仅添加从库,则接下来 安装周边>解除屏蔽监控 即刻完成。
                # todo 后续这里可能需要添加域名用于作为只读从库组。
                tendb_migrate_pipeline.add_sub_pipeline(
                    sub_flow=standardize_mysql_cluster_subflow(
                        root_id=self.root_id,
                        data=copy.deepcopy(self.data),
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        bk_biz_id=cluster_class.bk_biz_id,
                        instances=instances,
                        with_actuator=False,
                        with_bk_plugin=False,
                        with_instance_standardize=False,
                        with_collect_sysinfo=False,
                    )
                )
                tendb_migrate_pipeline.add_act(
                    act_name=DisableAlarmShieldComponent.node_name,
                    act_component_code=DisableAlarmShieldComponent.code,
                    kwargs={},
                )
            else:
                # 如果是替换从库。后续的动作则为：安装周边>切换主从>刷新安装周边>解除监控>卸载实例
                tendb_migrate_pipeline.add_sub_pipeline(
                    sub_flow=standardize_mysql_cluster_subflow(
                        root_id=self.root_id,
                        data=copy.deepcopy(self.data),
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        bk_biz_id=cluster_class.bk_biz_id,
                        instances=instances,
                        departs=remove_departs(ALLDEPARTS, DeployPeripheralToolsDepart.MySQLDBBackup),
                        with_actuator=False,
                        with_bk_plugin=False,
                        with_instance_standardize=False,
                        with_cc_standardize=False,
                        with_collect_sysinfo=False,
                    )
                )
                # 人工切换
                if not self.auto_switch_slave:
                    tendb_migrate_pipeline.add_act(
                        act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={}
                    )
                # 切换迁移实例
                tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_pipeline_list)
                # 切换后再次刷新周边
                # 标志重建机器是否为is_stand_by
                standardize_instances = instances
                slaves = cluster_class.storageinstance_set.filter(machine__ip=self.data["old_slave_ip"])
                for slave in slaves:
                    if slave.is_stand_by:
                        standardize_instances = instances + master_instances
                        break
                tendb_migrate_pipeline.add_sub_pipeline(
                    sub_flow=standardize_mysql_cluster_subflow(
                        root_id=self.root_id,
                        data=copy.deepcopy(self.data),
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        bk_biz_id=cluster_class.bk_biz_id,
                        instances=standardize_instances,
                        with_actuator=False,
                        with_bk_plugin=False,
                        with_instance_standardize=False,
                        with_collect_sysinfo=True,
                        with_backup_client=False,
                    )
                )
                tendb_migrate_pipeline.add_act(
                    act_name=DisableAlarmShieldComponent.node_name,
                    act_component_code=DisableAlarmShieldComponent.code,
                    kwargs={},
                )
                # 卸载流程人工确认
                if not disable_manual_confirm:
                    tendb_migrate_pipeline.add_act(
                        act_name=_("人工确认卸载实例"), act_component_code=PauseComponent.code, kwargs={}
                    )
                # 卸载remote节点
                tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_svr_sub_pipeline_list)

            if self.add_slave_only:
                title = _("添加从库 {} {}").format(self.data["new_slave_ip"], cluster_class.immute_domain)
            else:
                title = _("{} > {} 从库重建 {}").format(
                    self.data["old_slave_ip"], self.data["new_slave_ip"], cluster_class.immute_domain
                )
            tendb_migrate_pipeline_list.append(tendb_migrate_pipeline.build_sub_process(title))
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
                act_name=_("检查重做节点是否存在从库{}").format(target_slave.ip_port),
                act_component_code=MySQLCheckBinlogDumpComponent.code,
                kwargs=asdict(
                    ExecuteRdsKwargs(
                        bk_cloud_id=cluster_model.bk_cloud_id,
                        instance_ip=target_slave.machine.ip,
                        instance_port=target_slave.port,
                    )
                ),
            )

            tendb_migrate_pipeline.add_act(
                act_name=_("下发db-actor到节点 {} {}".format(target_slave.machine.ip, master.machine.ip)),
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
                act_name=_("修改{}状态为:{}".format(target_slave.ip_port, InstanceStatus.RESTORING.value)),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.tendb_modify_storage_status.__name__,
                        cluster=cluster,
                        is_update_trans_data=False,
                    )
                ),
            )

            tendb_migrate_pipeline.add_act(
                act_name=_("检查数据库链接{}").format(target_slave.ip_port),
                act_component_code=MySQLCheckProcesslistComponent.code,
                kwargs=asdict(
                    ExecuteRdsKwargs(
                        bk_cloud_id=cluster_model.bk_cloud_id,
                        instance_ip=target_slave.machine.ip,
                        instance_port=target_slave.port,
                    )
                ),
            )

            tendb_migrate_pipeline.add_act(
                act_name=_("屏蔽告警24小时 {}".format(target_slave.ip_port)),
                act_component_code=AddAlarmShieldComponent.code,
                kwargs={
                    "duration_seconds": 24 * 3600,
                    "description": cluster_model.immute_domain,
                    "dimensions": [
                        {
                            "name": "instance_host",
                            "values": [target_slave.machine.ip],
                        },
                        {
                            "name": "instance_port",
                            "values": [target_slave.port],
                        },
                    ],
                },
            )

            tendb_migrate_pipeline.add_act(
                act_name=_("删除从库{}关联的域名").format(target_slave.ip_port),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    RecycleDnsRecordKwargs(
                        dns_op_exec_port=target_slave.port,
                        exec_ip=target_slave.machine.ip,
                        bk_cloud_id=cluster_model.bk_cloud_id,
                    )
                ),
            )

            tendb_migrate_pipeline.add_act(
                act_name=_("Master节点执行 reset slave {},防止故障切换后master的位点还没断开,slave恢复后导致覆盖。").format(master.ip_port),
                act_component_code=MySQLExecuteRdsComponent.code,
                kwargs=asdict(
                    ExecuteRdsKwargs(
                        bk_cloud_id=cluster_model.bk_cloud_id,
                        instance_ip=master.machine.ip,
                        instance_port=master.port,
                        sqls=["stop slave", "reset slave all"],
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

            cluster = {
                "stop_slave": True,
                "reset_slave": True,
                "restart": False,
                "force": True,
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
                "backup_source": self.ticket_data.get("backup_source"),
                "restore_privilege": True,
                "privilege_ips": [target_slave.machine.ip],
                "is_stand_by": target_slave.is_stand_by,
            }

            if self.ticket_data.get("backup_source") == MySQLBackupSource.LOCAL:
                filter_ips = [master.machine.ip]
            else:
                filter_ips = None
            tendb_migrate_pipeline.add_sub_pipeline(
                sub_flow=mysql_restore_data_sub_flow(
                    root_id=self.root_id,
                    ticket_data=copy.deepcopy(self.data),
                    cluster=cluster,
                    cluster_model=cluster_model,
                    filter_ips=filter_ips,
                )
            )
            new_slave = "{}{}{}".format(target_slave.machine.ip, IP_PORT_DIVIDER, target_slave.port)
            old_master = "{}{}{}".format(master.machine.ip, IP_PORT_DIVIDER, master.port)
            if self.auto_switch_slave:
                # 自动切换新从库
                tendb_migrate_pipeline.add_act(
                    act_name=_("探测主从延迟情况 {}").format(new_slave),
                    act_component_code=MySQLCheckSlaveDelayProbeComponent.code,
                    kwargs=asdict(
                        CheckSlaveStatusKwargs(
                            bk_cloud_id=cluster_model.bk_cloud_id,
                            instance_ip=target_slave.machine.ip,
                            instance_port=target_slave.port,
                            slave_delay_threshold=1000000,
                            check_file_delay=1,
                        )
                    ),
                )
            else:
                # 卸载流程人工确认
                tendb_migrate_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
                tendb_migrate_pipeline.add_act(
                    act_name=_("检查主/从延迟 {}").format(new_slave),
                    act_component_code=MySQLCheckSlaveDelayComponent.code,
                    kwargs=asdict(
                        CheckSlaveStatusKwargs(
                            bk_cloud_id=cluster_model.bk_cloud_id,
                            instance_ip=target_slave.machine.ip,
                            instance_port=target_slave.port,
                            slave_delay_threshold=1000000,
                            check_file_delay=1,
                        )
                    ),
                )
            #  克隆权限
            if master.is_stand_by:
                tendb_migrate_pipeline.add_sub_pipeline(
                    sub_flow=mysql_clone_grants_from_file_subflow(
                        root_id=self.root_id,
                        data=copy.deepcopy(self.data),
                        bk_cloud_id=cluster_model.bk_cloud_id,
                        bk_biz_id=cluster_model.bk_biz_id,
                        source_address=old_master,
                        dest_addresses=[new_slave],
                    )
                )

            domain_map = get_tendb_ha_entry(cluster_model.id)
            domain_add_list = []
            for domain in domain_map[target_slave.machine.ip]:
                domain_add_list.append(
                    {
                        "act_name": _("添加从库域名{} {}").format(target_slave.machine.ip, domain),
                        "act_component_code": MySQLDnsManageComponent.code,
                        "kwargs": asdict(
                            CreateDnsKwargs(
                                bk_cloud_id=cluster_model.bk_cloud_id,
                                add_domain_name=domain,
                                dns_op_exec_port=target_slave.port,
                                exec_ip=target_slave.machine.ip,
                            )
                        ),
                    }
                )
            if len(domain_add_list) > 0:
                tendb_migrate_pipeline.add_parallel_acts(acts_list=domain_add_list)

            domain_add_list = []
            if target_slave.is_stand_by:
                for domain in domain_map["master_has_slave_domain"]:
                    domain_add_list.append(
                        {
                            "act_name": _("删除主的Dr域名{} {}").format(master.machine.ip, domain),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                IpDnsRecordRecycleKwargs(
                                    bk_cloud_id=cluster_model.bk_cloud_id,
                                    instance_list=[
                                        "{}{}{}".format(master.machine.ip, IP_PORT_DIVIDER_FOR_DNS, master.port)
                                    ],
                                    domain_name=domain,
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
                    "cluster_id": cluster_model.id,
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

            # 原地重建, 基本可以认为只要重新推送配置
            tendb_migrate_pipeline.add_sub_pipeline(
                sub_flow=standardize_mysql_cluster_by_ip_subflow(
                    root_id=self.root_id,
                    data=copy.deepcopy(self.data),
                    bk_cloud_id=cluster_model.bk_cloud_id,
                    bk_biz_id=master.bk_biz_id,
                    ips=[master.machine.ip, target_slave.machine.ip],
                    with_collect_sysinfo=False,
                    with_instance_standardize=False,
                    with_bk_plugin=False,
                    with_actuator=False,
                )
            )
            tendb_migrate_pipeline.add_act(
                act_name=DisableAlarmShieldComponent.node_name,
                act_component_code=DisableAlarmShieldComponent.code,
                kwargs={},
            )

            tendb_migrate_pipeline_list.append(
                tendb_migrate_pipeline.build_sub_process(
                    _("{} 从库原地重建 {}").format(target_slave.ip_port, cluster_model.immute_domain)
                )
            )

        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(sub_flow_list=tendb_migrate_pipeline_list)

        tendb_migrate_pipeline_all.run_pipeline(
            init_trans_data_class=ClusterInfoContext(),
            is_drop_random_user=True,
        )
