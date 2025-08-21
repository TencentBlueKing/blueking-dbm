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
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Optional

from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryType, InstanceInnerRole, InstancePhase, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import DBA_SYSTEM_USER, LONG_JOB_TIMEOUT, MediumEnum, TendbSingleRestoreEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import install_mysql_in_cluster_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.get_local_backup import get_local_single_backup
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_instance_config
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import restore_single_remote_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.single_recover_switch import single_migrate_switch_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.uninstall_instance import uninstall_instance_sub_flow
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    ALLDEPARTS,
    DeployPeripheralToolsDepart,
    remove_departs,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBackupInfoFailedException
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_crond_control import MysqlCrondMonitorControlComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_ports, get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import (
    ClearMachineKwargs,
    CrondMonitorKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLMigrateSingleFlow(object):
    """
    构建mysql logDb 迁移抽象类
    支持多云区域操作
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param ticket_data : 单据传递参数
        """
        self.root_id = root_id
        self.ticket_data = ticket_data
        self.data = {}

        # 定义备份文件存放到目标机器目录位置
        self.backup_target_path = f"/data/dbbak/{self.root_id}"

    def migrate_single_flow(self, use_for_upgrade=False):
        """
        定义 tendbSingle 迁移flow
        1 mysql_migrate_cluster_add_instance
        2 mysql_migrate_cluster_add_tuple
        3 mysql_migrate_cluster_switch_storage
        """
        # 构建流程
        cluster_ids = []
        for i in self.ticket_data["infos"]:
            cluster_ids.extend(i["cluster_ids"])

        tendb_migrate_pipeline_all = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )

        # 按照传入的infos信息，循环拼接子流程
        tendb_migrate_pipeline_list = []
        # 一个循环一对机器
        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            cluster_class = Cluster.objects.get(id=self.data["cluster_ids"][0])
            # 确定要迁移的主节点，从节点.
            master_model = cluster_class.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN.value)
            install_pkg_version = cluster_class.major_version
            # 如果是升级用途的话,需要改变module id
            db_module_id = cluster_class.db_module_id
            self.data["package"] = Package.get_latest_package(
                version=install_pkg_version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL
            ).name

            pkg_id = 0
            if use_for_upgrade:
                db_module_id = info["new_db_module_id"]
                pkg_id = info["pkg_id"]
                self.data["package"] = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
            charset, db_version = get_version_and_charset(
                bk_biz_id=cluster_class.bk_biz_id,
                db_module_id=db_module_id,
                cluster_type=cluster_class.cluster_type,
            )
            self.data["new_orphan_ip"] = self.data["bk_new_orphan"]["ip"]
            self.data["new_orphan_port"] = master_model.port
            self.data["orphan_ip"] = master_model.machine.ip
            self.data["cluster_type"] = cluster_class.cluster_type
            self.data["orphan_port"] = master_model.port
            self.data["bk_biz_id"] = cluster_class.bk_biz_id
            self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
            self.data["db_module_id"] = db_module_id
            self.data["time_zone"] = cluster_class.time_zone
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["module"] = db_module_id
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["uid"] = self.ticket_data["uid"]
            self.data["ports"] = get_ports(info["cluster_ids"])
            self.data["charset"] = charset
            self.data["db_version"] = db_version

            tendb_migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            # 整机安装数据库
            db_config = get_instance_config(cluster_class.bk_cloud_id, master_model.machine.ip, self.data["ports"])
            install_sub_pipeline_list = []
            install_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            install_sub_pipeline.add_sub_pipeline(
                sub_flow=install_mysql_in_cluster_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster_class,
                    new_mysql_list=[self.data["new_orphan_ip"]],
                    install_ports=self.data["ports"],
                    bk_host_ids=[self.data["bk_new_orphan"]["bk_host_id"]],
                    pkg_id=pkg_id,
                    db_module_id=db_module_id,
                    db_config=db_config,
                )
            )

            cluster = {
                "cluster_ports": self.data["ports"],
                "new_orphan_ip": self.data["new_orphan_ip"],
                "bk_cloud_id": cluster_class.bk_cloud_id,
                "spec_config": self.data["resource_spec"]["orphan"],
                "spec_id": self.data["resource_spec"]["orphan"]["id"],
            }
            install_sub_pipeline.add_act(
                act_name=_("安装完毕,写入初始化实例的db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.migrate_single_add_instance.__name__,
                        cluster=copy.deepcopy(cluster),
                        is_update_trans_data=True,
                    )
                ),
            )
            # 安装临时备份工具，用于新机恢复数据
            install_sub_pipeline.add_act(
                act_name=_("安装backup-client工具"),
                act_component_code=DownloadBackupClientComponent.code,
                kwargs=asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        bk_biz_id=cluster_class.bk_biz_id,
                        download_host_list=[self.data["new_orphan_ip"]],
                    )
                ),
            )

            exec_act_kwargs = ExecActuatorKwargs(
                cluster=cluster,
                bk_cloud_id=cluster_class.bk_cloud_id,
                cluster_type=cluster_class.cluster_type,
                get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
            )
            exec_act_kwargs.exec_ip = [self.data["new_orphan_ip"]]
            install_sub_pipeline.add_act(
                act_name=_("安装临时备份程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )
            install_sub_pipeline_list.append(install_sub_pipeline.build_sub_process(sub_name=_("安装实例")))

            sync_data_sub_pipeline_list = []
            for cluster_id in self.data["cluster_ids"]:
                cluster_model = Cluster.objects.get(id=cluster_id)
                master_model = cluster_model.storageinstance_set.get(
                    instance_inner_role=InstanceInnerRole.ORPHAN.value
                )
                cluster["new_orphan_ip"] = self.data["new_orphan_ip"]
                cluster["new_orphan_port"] = master_model.port
                cluster["orphan_ip"] = master_model.machine.ip
                cluster["orphan_port"] = master_model.port
                cluster["mysql_port"] = master_model.port
                cluster["file_target_path"] = f"/data/dbbak/{self.root_id}/{master_model.port}"
                cluster["cluster_id"] = cluster_model.id
                cluster["bk_cloud_id"] = cluster_model.bk_cloud_id
                cluster["charset"] = self.data["charset"]
                cluster["binlog_sync"] = self.data.get("binlog_sync", False)
                cluster["recover_grants"] = True
                backup_id = uuid.uuid1()
                # 查询备份。根据选择的恢复类型。分别从本地发起实时备份，和从远程查询备份。
                sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                if self.data["orphan_restore_type"] in [
                    TendbSingleRestoreEnum.LocalBackupAndData,
                    TendbSingleRestoreEnum.LocalBackupAndSchema,
                ]:
                    if self.data["orphan_restore_type"] == TendbSingleRestoreEnum.LocalBackupAndSchema:
                        cluster["is_full_backup"] = 0
                        backup_gsd = ["schema"]
                    else:
                        cluster["is_full_backup"] = 1
                        backup_gsd = ["all"]
                    backup_sub_pipe = SubBuilder(
                        root_id=self.root_id,
                        data={
                            "uid": self.data["uid"],
                            "created_by": self.data["created_by"],
                            "bk_biz_id": cluster_model.bk_biz_id,
                            "ticket_type": self.data["ticket_type"],
                            "ip": master_model.machine.ip,
                            "port": master_model.port,
                            "backup_type": self.data["backup_type"],
                            "backup_id": backup_id,
                            "backup_gsd": backup_gsd,
                            "role": master_model.instance_role,
                        },
                    )
                    #  备份
                    backup_sub_pipe.add_act(
                        act_name=_("下发db-actor到节点"),
                        act_component_code=TransFileComponent.code,
                        kwargs=asdict(
                            DownloadMediaKwargs(
                                bk_cloud_id=cluster_model.bk_cloud_id,
                                exec_ip=[master_model.machine.ip],
                                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                            )
                        ),
                    )
                    backup_sub_pipe.add_act(
                        act_name=_("执行库表备份"),
                        act_component_code=ExecuteDBActuatorScriptComponent.code,
                        kwargs=asdict(
                            ExecActuatorKwargs(
                                job_timeout=LONG_JOB_TIMEOUT,
                                bk_cloud_id=cluster_model.bk_cloud_id,
                                run_as_system_user=DBA_SYSTEM_USER,
                                exec_ip=master_model.machine.ip,
                                get_mysql_payload_func=MysqlActPayload.mysql_backup_demand_payload.__name__,
                            )
                        ),
                    )
                    sync_data_sub_pipeline.add_sub_pipeline(
                        backup_sub_pipe.build_sub_process(
                            sub_name=_("{} tendbSingle发起备份").format(cluster_model.immute_domain)
                        )
                    )

                    backup_info = get_local_single_backup([master_model.ip_port], cluster_model, backup_id=backup_id)
                    if backup_info is None:
                        logger.error("cluster {} backup info not exists".format(cluster_model.id))
                        raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(cluster_model.id)))
                    cluster["backupinfo"] = backup_info
                    cluster["recover_grants"] = False
                else:
                    # 从远程查询备份
                    rollback_time = datetime.now(timezone.utc)
                    rollback_handler = FixPointRollbackHandler(cluster_id=cluster_model.id)
                    backup_info = rollback_handler.query_latest_backup_log(rollback_time)
                    if backup_info is None:
                        logger.error("cluster {} backup info not exists".format(cluster_model.id))
                        raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(cluster_id)))
                    cluster["backupinfo"] = backup_info
                sync_data_sub_pipeline.add_sub_pipeline(
                    sub_flow=restore_single_remote_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster=copy.deepcopy(cluster)
                    )
                )

                cluster = {
                    "phase": InstancePhase.ONLINE.value,
                    "storage_status": InstanceStatus.RUNNING.value,
                    "storage_id": master_model.id,
                }
                sync_data_sub_pipeline.add_act(
                    act_name=_("数据恢复完毕,修改实例状态"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.tendb_modify_storage_status.__name__,
                            cluster=copy.deepcopy(cluster),
                            is_update_trans_data=True,
                        )
                    ),
                )
                sync_data_sub_pipeline_list.append(
                    sync_data_sub_pipeline.build_sub_process(sub_name=_("{} 集群恢复数据".format(cluster_model.name)))
                )

            switch_sub_pipeline_list = []
            for cluster_id in self.data["cluster_ids"]:
                switch_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                cluster_model = Cluster.objects.get(id=cluster_id)
                master_model = cluster_model.storageinstance_set.get(
                    instance_inner_role=InstanceInnerRole.ORPHAN.value
                )
                #  切换。改域名链接.是否需要去kill掉主库链接。
                single_domains = master_model.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value)
                domains = [d.entry for d in single_domains]
                cluster = {
                    "cluster_id": cluster_model.id,
                    "bk_cloud_id": cluster_model.bk_cloud_id,
                    "orphan_ip": master_model.machine.ip,
                    "orphan_port": master_model.port,
                    "new_orphan_ip": self.data["new_orphan_ip"],
                    "new_orphan_port": master_model.port,
                    "domains": domains,
                }
                switch_sub_pipeline.add_sub_pipeline(
                    sub_flow=single_migrate_switch_sub_flow(
                        root_id=self.root_id,
                        ticket_data=copy.deepcopy(self.data),
                        cluster=cluster_model,
                        old_orphan_ip=master_model.machine.ip,
                        new_orphan_ip=self.data["new_orphan_ip"],
                        domains=domains,
                    )
                )

                switch_sub_pipeline.add_act(
                    act_name=_("集群切换完成,写入 {} 的元信息".format(cluster_model.name)),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_single_change_cluster_info.__name__,
                            cluster=cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                switch_sub_pipeline.add_act(
                    act_name=_("切换后屏蔽旧实例备份 {}").format(master_model.machine.ip),
                    act_component_code=MysqlCrondMonitorControlComponent.code,
                    kwargs=asdict(
                        CrondMonitorKwargs(
                            bk_cloud_id=cluster_class.bk_cloud_id,
                            exec_ips=[master_model.machine.ip],
                            name="dbbackup",
                            port=master_model.port,
                        )
                    ),
                )

                switch_sub_pipeline_list.append(
                    switch_sub_pipeline.build_sub_process(sub_name=_("集群 {} 切换".format(cluster_model.name)))
                )

            # 第四步 卸载周边 卸载实例
            uninstall_surrounding_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            uninstall_svr_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))

            # 考虑到部分实例为拆分的情况
            cluster = {
                "uninstall_ip": master_model.machine.ip,
                "remote_port": self.data["ports"],
                "backend_port": self.data["ports"],
                "bk_cloud_id": cluster_class.bk_cloud_id,
            }

            uninstall_surrounding_sub_pipeline.add_act(
                act_name=_("下发db-actor到节点{}".format(master_model.machine.ip)),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        exec_ip=[master_model.machine.ip],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            uninstall_surrounding_sub_pipeline.add_act(
                act_name=_("清理实例级别周边配置"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=master_model.machine.ip,
                        cluster_type=cluster_class.cluster_type,
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        cluster=cluster,
                        get_mysql_payload_func=MysqlActPayload.get_clear_surrounding_config_payload.__name__,
                    )
                ),
            )
            uninstall_surrounding_sub_pipeline_list = [
                uninstall_surrounding_sub_pipeline.build_sub_process(
                    sub_name=_("卸载remote节点周边{}".format(master_model.machine.ip))
                )
            ]

            # 卸载实例
            cluster = {
                "uninstall_ip": master_model.machine.ip,
                "ports": self.data["ports"],
                "bk_cloud_id": cluster_class.bk_cloud_id,
                "cluster_type": cluster_class.cluster_type,
            }
            uninstall_svr_sub_pipeline.add_act(
                act_name=_("实例卸载前删除元数据"),
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
                act_name=_("清理机器配置"),
                act_component_code=MySQLClearMachineComponent.code,
                kwargs=asdict(
                    ClearMachineKwargs(
                        exec_ip=master_model.machine.ip,
                        bk_cloud_id=cluster_class.bk_cloud_id,
                    )
                ),
            )
            uninstall_svr_sub_pipeline.add_sub_pipeline(
                sub_flow=uninstall_instance_sub_flow(
                    root_id=self.root_id,
                    ticket_data=copy.deepcopy(self.data),
                    ip=master_model.machine.ip,
                    ports=self.data["ports"],
                )
            )
            uninstall_svr_sub_pipeline_list = [
                uninstall_svr_sub_pipeline.build_sub_process(
                    sub_name=_("卸载remote节点{}".format(master_model.machine.ip))
                )
            ]

            # 安装实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=install_sub_pipeline_list)

            # 数据同步
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
            # 新机器安装周边组件
            instances = [
                "{}{}{}".format(self.data["new_orphan_ip"], IP_PORT_DIVIDER, port) for port in self.data["ports"]
            ]
            # 不能部署备份
            # 不然这些未启用机器的备份可能会污染正式集群
            tendb_migrate_pipeline.add_sub_pipeline(
                sub_flow=standardize_mysql_cluster_subflow(
                    root_id=self.root_id,
                    data=copy.deepcopy(self.data),
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    bk_biz_id=cluster_class.bk_biz_id,
                    departs=remove_departs(ALLDEPARTS, DeployPeripheralToolsDepart.MySQLDBBackup),
                    instances=instances,
                    with_actuator=False,
                    with_bk_plugin=False,
                )
            )

            # 切换迁移实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_pipeline_list)

            tendb_migrate_pipeline.add_sub_pipeline(
                sub_flow=standardize_mysql_cluster_subflow(
                    root_id=self.root_id,
                    data=copy.deepcopy(self.data),
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    bk_biz_id=cluster_class.bk_biz_id,
                    instances=instances,
                    departs=[
                        DeployPeripheralToolsDepart.MySQLMonitor,
                        DeployPeripheralToolsDepart.MySQLDBBackup,
                        DeployPeripheralToolsDepart.MySQLRotateBinlog,
                        DeployPeripheralToolsDepart.MySQLTableChecksum,
                    ],
                    with_actuator=False,
                    with_bk_plugin=False,
                    with_instance_standardize=False,
                    with_collect_sysinfo=False,
                    with_cc_standardize=False,
                )
            )

            tendb_migrate_pipeline.add_act(
                act_name=_("解除屏蔽监控 {}").format(self.data["new_orphan_ip"]),
                act_component_code=MysqlCrondMonitorControlComponent.code,
                kwargs=asdict(
                    CrondMonitorKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        exec_ips=[self.data["new_orphan_ip"]],
                        port=0,
                        enable=True,
                    )
                ),
            )

            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_surrounding_sub_pipeline_list)

            # 卸载流程人工确认
            tendb_migrate_pipeline.add_act(act_name=_("人工确认卸载实例"), act_component_code=PauseComponent.code, kwargs={})
            # 卸载remote节点
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_svr_sub_pipeline_list)
            tendb_migrate_pipeline_list.append(
                tendb_migrate_pipeline.build_sub_process(
                    sub_name=_("{} > {} 单节点迁移".format(self.data["orphan_ip"], self.data["new_orphan_ip"]))
                )
            )
        # 运行流程
        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(tendb_migrate_pipeline_list)
        tendb_migrate_pipeline_all.run_pipeline(
            init_trans_data_class=ClusterInfoContext(),
            is_drop_random_user=True,
        )
