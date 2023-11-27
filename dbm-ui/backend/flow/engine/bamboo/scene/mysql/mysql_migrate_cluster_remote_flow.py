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
from datetime import datetime
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_surrounding_apps_sub_flow,
    install_mysql_in_cluster_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.common.master_and_slave_switch import master_and_slave_switch
from backend.flow.engine.bamboo.scene.mysql.common.uninstall_instance import uninstall_instance_sub_flow
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBackupInfoFailedException
from backend.flow.engine.bamboo.scene.spider.spider_remote_node_migrate import remote_instance_migrate_sub_flow
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_ports, get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import ClearMachineKwargs, DBMetaOPKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLMigrateClusterRemoteFlow(object):
    """
    构建mysql主从成对迁移抽象类
    支持多云区域操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.ticket_data = data
        self.data = {}

        # 定义备份文件存放到目标机器目录位置
        self.backup_target_path = f"/data/dbbak/{self.root_id}"

    def migrate_cluster_flow(self):
        """
        成对迁移集群主从节点。
        元数据信息修改顺序：
        1 mysql_migrate_cluster_add_instance
        2 mysql_migrate_cluster_add_tuple
        3 mysql_migrate_cluster_switch_storage
        """
        # 构建流程
        tendb_migrate_pipeline_all = Builder(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))
        # 按照传入的infos信息，循环拼接子流程
        tendb_migrate_pipeline_list = []
        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            cluster_class = Cluster.objects.get(id=self.data["cluster_ids"][0])
            # 确定要迁移的主节点，从节点.
            master = cluster_class.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
            slave = cluster_class.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
            ).first()
            self.data["master_ip"] = master.machine.ip
            self.data["cluster_type"] = cluster_class.cluster_type
            self.data["old_slave_ip"] = slave.machine.ip
            self.data["slave_ip"] = slave.machine.ip
            self.data["mysql_port"] = master.port
            self.data["bk_biz_id"] = cluster_class.bk_biz_id
            self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
            self.data["db_module_id"] = cluster_class.db_module_id
            self.data["time_zone"] = cluster_class.time_zone
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["module"] = cluster_class.db_module_id
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["uid"] = self.ticket_data["uid"]
            self.data["package"] = Package.get_latest_package(
                version=cluster_class.major_version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL
            ).name
            self.data["ports"] = get_ports(info["cluster_ids"])
            self.data["force"] = info.get("force", False)
            self.data["charset"], self.data["db_version"] = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=self.data["db_module_id"],
                cluster_type=self.data["cluster_type"],
            )
            tendb_migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            # 整机安装数据库
            install_sub_pipeline_list = []
            install_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            install_sub_pipeline.add_sub_pipeline(
                sub_flow=install_mysql_in_cluster_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster_class,
                    new_mysql_list=[self.data["new_slave_ip"], self.data["new_master_ip"]],
                    install_ports=self.data["ports"],
                )
            )

            #  写入元数据
            cluster = {
                "cluster_ports": self.data["ports"],
                "new_master_ip": self.data["new_master_ip"],
                "new_slave_ip": self.data["new_slave_ip"],
                "bk_cloud_id": self.data["bk_cloud_id"],
            }
            install_sub_pipeline.add_act(
                act_name=_("安装完毕,写入初始化实例的db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.migrate_cluster_add_instance.__name__,
                        cluster=cluster,
                        is_update_trans_data=True,
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
                        download_host_list=[cluster["new_master_ip"], cluster["new_slave_ip"]],
                    )
                ),
            )

            exec_act_kwargs = ExecActuatorKwargs(
                cluster=cluster,
                bk_cloud_id=cluster_class.bk_cloud_id,
                cluster_type=cluster_class.cluster_type,
                get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
            )
            exec_act_kwargs.exec_ip = [cluster["new_master_ip"], cluster["new_slave_ip"]]
            install_sub_pipeline.add_act(
                act_name=_("安装临时备份程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )
            install_sub_pipeline_list.append(install_sub_pipeline.build_sub_process(sub_name=_("安装实例")))

            sync_data_sub_pipeline_list = []
            for cluster_id in self.data["cluster_ids"]:
                cluster_model = Cluster.objects.get(id=cluster_id)
                master = cluster_model.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
                # 查询备份
                rollback_time = datetime.now()
                rollback_handler = FixPointRollbackHandler(cluster_id=cluster_model.id)
                backup_info = rollback_handler.query_latest_backup_log(rollback_time)
                if backup_info is None:
                    logger.error("cluster {} backup info not exists".format(cluster_model.id))
                    raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(cluster_model.id)))
                cluster["backupinfo"] = backup_info
                cluster["new_master_ip"] = self.data["new_master_ip"]
                cluster["new_slave_ip"] = self.data["new_slave_ip"]
                cluster["new_master_port"] = master.port
                cluster["new_slave_port"] = master.port
                cluster["master_ip"] = self.data["master_ip"]
                cluster["slave_ip"] = self.data["slave_ip"]
                cluster["master_port"] = master.port
                cluster["slave_port"] = master.port
                cluster["file_target_path"] = f"/data/dbbak/{self.root_id}/{master.port}"
                cluster["cluster_id"] = cluster_model.id
                cluster["bk_cloud_id"] = cluster_model.bk_cloud_id
                cluster["change_master_force"] = False
                cluster["charset"] = self.data["charset"]

                sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                sync_data_sub_pipeline.add_sub_pipeline(
                    sub_flow=remote_instance_migrate_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=cluster
                    )
                )

                sync_data_sub_pipeline.add_act(
                    act_name=_("数据恢复完毕,写入新主节点和旧主节点的关系链元数据"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.migrate_cluster_add_tuple.__name__,
                            cluster=cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                sync_data_sub_pipeline_list.append(sync_data_sub_pipeline.build_sub_process(sub_name=_("恢复实例数据")))

            switch_sub_pipeline_list = []
            for cluster_id in self.data["cluster_ids"]:
                switch_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                cluster_model = Cluster.objects.get(id=cluster_id)

                other_slave_storage = cluster_model.storageinstance_set.filter(
                    instance_inner_role=InstanceInnerRole.SLAVE.value
                ).exclude(
                    machine__ip__in=[self.data["old_slave_ip"], self.data["new_slave_ip"], self.data["new_master_ip"]]
                )
                other_slaves = [y.machine.ip for y in other_slave_storage]
                cluster = {
                    "cluster_id": cluster_model.id,
                    "bk_cloud_id": cluster_model.bk_cloud_id,
                    "old_master_ip": self.data["master_ip"],
                    "old_master_port": self.data["mysql_port"],
                    "old_slave_ip": self.data["old_slave_ip"],
                    "old_slave_port": self.data["mysql_port"],
                    "new_master_ip": self.data["new_master_ip"],
                    "new_master_port": self.data["mysql_port"],
                    "new_slave_ip": self.data["new_slave_ip"],
                    "new_slave_port": self.data["mysql_port"],
                    "mysql_port": self.data["mysql_port"],
                    "other_slave_info": other_slaves,
                }
                switch_sub_pipeline.add_sub_pipeline(
                    sub_flow=master_and_slave_switch(
                        root_id=self.root_id,
                        ticket_data=copy.deepcopy(self.data),
                        cluster=cluster_model,
                        cluster_info=cluster,
                    )
                )
                switch_sub_pipeline.add_act(
                    act_name=_("集群切换完成,写入 {} 的元信息".format(cluster_model.id)),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_migrate_cluster_switch_storage.__name__,
                            cluster=cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                switch_sub_pipeline_list.append(
                    switch_sub_pipeline.build_sub_process(sub_name=_("集群 {} 切换".format(cluster_model.id)))
                )
            # 第四步 卸载实例
            uninstall_svr_sub_pipeline_list = []
            for ip in [self.data["slave_ip"], self.data["master_ip"]]:
                uninstall_svr_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                uninstall_svr_sub_pipeline.add_sub_pipeline(
                    sub_flow=uninstall_instance_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), ip=ip, ports=self.data["ports"]
                    )
                )
                cluster = {"uninstall_ip": ip, "ports": self.data["ports"], "bk_cloud_id": self.data["bk_cloud_id"]}
                uninstall_svr_sub_pipeline.add_act(
                    act_name=_("整机卸载成功后删除元数据"),
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
                            exec_ip=ip,
                            bk_cloud_id=self.data["bk_cloud_id"],
                        )
                    ),
                )
                uninstall_svr_sub_pipeline_list.append(
                    uninstall_svr_sub_pipeline.build_sub_process(sub_name=_("卸载remote节点{}".format(ip)))
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
                    slave_ip_list=[self.data["new_slave_ip"], self.data["new_master_ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(self.data),
                    is_init=True,
                    cluster_type=ClusterType.TenDBHA.value,
                )
            )
            # 人工确认切换迁移实例
            tendb_migrate_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})
            # 切换迁移实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_pipeline_list)
            tendb_migrate_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    master_ip_list=[self.data["new_master_ip"]],
                    slave_ip_list=[self.data["new_slave_ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(self.data),
                    is_init=True,
                    cluster_type=ClusterType.TenDBHA.value,
                )
            )
            # 卸载流程人工确认
            tendb_migrate_pipeline.add_act(act_name=_("人工确认卸载实例"), act_component_code=PauseComponent.code, kwargs={})
            # 卸载remote节点
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_svr_sub_pipeline_list)
            tendb_migrate_pipeline_list.append(
                tendb_migrate_pipeline.build_sub_process(sub_name=_("集群{}开始成对迁移").format(cluster_class.id))
            )
        # 运行流程
        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(tendb_migrate_pipeline_list)
        tendb_migrate_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext())
