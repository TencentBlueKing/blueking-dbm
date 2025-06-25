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

from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType, MySQLMonitorPauseTime
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import install_mysql_in_cluster_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_instance_config
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import (
    mysql_restore_master_slave_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    ALLDEPARTS,
    DeployPeripheralToolsDepart,
    remove_departs,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.engine.bamboo.scene.mysql.mysql_ha_upgrade import adapt_mycnf_for_upgrade
from backend.flow.engine.bamboo.scene.mysql.mysql_upgrade import upgrade_version_check
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import remote_migrate_switch_sub_flow
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBackupInfoFailedException
from backend.flow.engine.bamboo.scene.spider.spider_remote_node_migrate import (
    remote_instance_migrate_sub_flow,
    remote_node_uninstall_sub_flow,
)
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_crond_control import MysqlCrondMonitorControlComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
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
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.flow.utils.spider.tendb_cluster_info import get_cluster_info
from backend.ticket.builders.common.constants import MySQLBackupSource

logger = logging.getLogger("flow")


class UpgradeRemoteFlow(object):
    """
    TenDBCluster 后端节点主从成对迁移
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param ticket_data : 单据传递参数
        """
        self.root_id = root_id
        self.uid = data["uid"]
        self.bk_biz_id = data["bk_biz_id"]
        self.created_by = data["created_by"]
        self.ticket_data = data
        self.data = {}
        self.backup_target_path = f"/data/dbbak/{self.root_id}"

    def __get_backup_info(self, cluster_id: int):
        """
        get backup info from remote

        :param cluster_id: int, cluster id
        :return: dict, backup info
        :raises TendbGetBackupInfoFailedException: if backup info not exists
        """

        backup_info = {}
        if self.ticket_data["backup_source"] == MySQLBackupSource.REMOTE.value:
            # 先查询备份，如果备份不存在则退出
            # restore_time = datetime.strptime("2023-07-31 17:40:00", "%Y-%m-%d %H:%M:%S")
            backup_handler = FixPointRollbackHandler(cluster_id, check_full_backup=True)
            restore_time = datetime.now(timezone.utc)
            backup_info = backup_handler.query_latest_backup_log(restore_time)
            logger.debug(backup_info)
            if backup_info is None:
                logger.error("cluster {} backup info not exists".format(cluster_id))
                raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(cluster_id)))
        return backup_info

    def migrate_upgrade(self):
        """
        tendb 迁移
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        # 根据已有的实例计算出端口。nodes 中的每一个ip对应一个流程。
        cluster_ids = [i["cluster_id"] for i in self.ticket_data["infos"]]
        tendb_migrate_pipeline_all = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        # 阶段1 获取集群所有信息。计算端口,构建数据。
        tendb_migrate_pipeline_all_list = []
        for info in self.ticket_data["infos"]:
            cluster_id = info["cluster_id"]
            cluster_class = Cluster.objects.get(id=cluster_id)
            # build data {}
            self.data = {}
            self.data = copy.deepcopy(info)
            self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
            self.data["root_id"] = self.root_id
            self.data["start_port"] = 20000
            self.data["uid"] = self.uid
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["bk_biz_id"] = self.bk_biz_id
            self.data["created_by"] = self.created_by
            self.data["force"] = True

            pkg_id = info["pkg_id"]
            new_db_module_id = info["new_db_module_id"]
            pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
            cluster_info = get_cluster_info(cluster_id)
            charset, db_version = get_version_and_charset(
                bk_biz_id=cluster_info["bk_biz_id"],
                db_module_id=cluster_info["db_module_id"],
                cluster_type=cluster_info["cluster_type"],
            )
            cluster_info["charset"] = charset
            cluster_info["db_version"] = db_version
            self.data["db_version"] = db_version

            charset, new_db_version = get_version_and_charset(
                bk_biz_id=cluster_info["bk_biz_id"],
                db_module_id=new_db_module_id,
                cluster_type=cluster_info["cluster_type"],
            )
            upgrade_version_check(db_version, new_db_version)
            shards = len(cluster_info["shards"])
            if self.data["remote_shard_num"] * len(self.data["remote_group"]) != shards:
                raise TendbGetBackupInfoFailedException(
                    message=_(
                        "{}集群分片计算错误 remote_shard_num:{} x remote_group:{} != {}".format(
                            self.data["cluster_id"],
                            self.data["remote_shard_num"],
                            len(self.data["remote_group"]),
                            shards,
                        )
                    )
                )
            cluster_info["ports"] = []
            for port in range(self.data["start_port"], self.data["start_port"] + self.data["remote_shard_num"]):
                cluster_info["ports"].append(port)
            shard_ids = copy.deepcopy(cluster_info["shard_ids"])

            instances = []
            for idx, node in enumerate(copy.deepcopy(self.data["remote_group"])):
                db_config = {}
                for port in cluster_info["ports"]:
                    master = {
                        "ip": node["master"]["ip"],
                        "port": port,
                        "bk_cloud_id": self.data["bk_cloud_id"],
                        "instance": "{}{}{}".format(node["master"]["ip"], IP_PORT_DIVIDER, port),
                    }
                    slave = {
                        "ip": node["slave"]["ip"],
                        "port": port,
                        "bk_cloud_id": self.data["bk_cloud_id"],
                        "instance": "{}{}{}".format(node["slave"]["ip"], IP_PORT_DIVIDER, port),
                    }

                    instances.extend(
                        ["{}:{}".format(master["ip"], master["port"]), "{}:{}".format(slave["ip"], slave["port"])]
                    )

                    shard_id = shard_ids.pop(0)
                    cluster_info["shards"][shard_id]["new_master"] = master
                    cluster_info["shards"][shard_id]["new_slave"] = slave
                    # 获取分片的master节点信息
                    shard_config = get_instance_config(
                        cluster_class.bk_cloud_id,
                        cluster_info["shards"][shard_id]["master"]["ip"],
                        [cluster_info["shards"][shard_id]["master"]["port"]],
                    )
                    db_config[port] = shard_config.get(str(cluster_info["shards"][shard_id]["master"]["port"]), {})
                # 源实例对应分片配置文件一一放入新机器安装信息
                self.data["remote_group"][idx]["db_config"] = db_config

            tendb_migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            # 阶段2 安装实例并写入数据
            install_sub_pipeline_list = []
            for node in self.data["remote_group"]:
                db_config = node.get("db_config", {})
                db_config = adapt_mycnf_for_upgrade(pkg.name, db_version, db_config)
                master_host_id = node["master"]["bk_host_id"]
                slave_host_id = node["slave"]["bk_host_id"]
                install_node_pipeline_list = build_install_remote_mspair_sub_pipeline(
                    uid=self.uid,
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(self.data),
                    cluster=cluster_class,
                    new_master_ip=node["master"]["ip"],
                    new_slave_ip=node["slave"]["ip"],
                    ports=cluster_info["ports"],
                    bk_host_ids=[master_host_id, slave_host_id],
                    db_config=db_config,
                    pkg_id=pkg_id,
                    db_module_id=new_db_module_id,
                )
                install_sub_pipeline_list.append(install_node_pipeline_list)

            # 阶段3 逐个实例同步数据到新主从库
            backup_info = self.__get_backup_info(info["cluster_id"])
            sync_data_sub_pipeline_list = self.build_sync_data_sub_pipeline(
                cluster_class=cluster_class,
                cluster_info=cluster_info,
                backup_info=backup_info,
            )
            # 阶段4 切换
            switch_sub_pipeline_list = []
            shard_list = []
            for shard_id, node in cluster_info["shards"].items():
                shard_cluster = {
                    "old_master": node["master"]["instance"],
                    "old_slave": node["slave"]["instance"],
                    "new_master": node["new_master"]["instance"],
                    "new_slave": node["new_slave"]["instance"],
                }
                shard_list.append(shard_cluster)
            switch_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            switch_sub_pipeline.add_sub_pipeline(
                sub_flow=remote_migrate_switch_sub_flow(
                    uid=self.uid,
                    root_id=self.root_id,
                    cluster=cluster_class,
                    migrate_tuples=shard_list,
                    created_by=self.created_by,
                )
            )
            switch_sub_pipeline.add_act(
                act_name=_("整集群切换完毕后修改元数据指向"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.tendb_remotedb_rebalance_switch.__name__,
                        cluster=cluster_info,
                        is_update_trans_data=True,
                    )
                ),
            )
            switch_sub_pipeline_list.append(switch_sub_pipeline.build_sub_process(sub_name=_("切换remote node 节点")))

            # 阶段5: 新机器安装周边组件
            surrounding_sub_pipeline_list = []
            re_surrounding_sub_pipeline_list = []
            for node in self.data["remote_group"]:
                surrounding_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                surrounding_sub_pipeline.add_sub_pipeline(
                    sub_flow=standardize_mysql_cluster_subflow(
                        root_id=self.root_id,
                        data=copy.deepcopy(self.data),
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        bk_biz_id=cluster_class.bk_biz_id,
                        departs=remove_departs(ALLDEPARTS, DeployPeripheralToolsDepart.MySQLDBBackup),
                        instances=instances,
                        with_actuator=False,
                        with_bk_plugin=False,
                        with_collect_sysinfo=False,
                        with_cc_standardize=False,
                        with_instance_standardize=False,
                    )
                )
                surrounding_sub_pipeline.add_act(
                    act_name=_("屏蔽监控 {} {}").format(node["master"]["ip"], node["slave"]["ip"]),
                    act_component_code=MysqlCrondMonitorControlComponent.code,
                    kwargs=asdict(
                        CrondMonitorKwargs(
                            bk_cloud_id=cluster_class.bk_cloud_id,
                            exec_ips=[node["master"]["ip"], node["slave"]["ip"]],
                            port=0,
                            minutes=MySQLMonitorPauseTime.SLAVE_DELAY,
                        )
                    ),
                )
                surrounding_sub_pipeline_list.append(
                    surrounding_sub_pipeline.build_sub_process(sub_name=_("新机器安装周边组件"))
                )

                re_surrounding_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                re_surrounding_sub_pipeline.add_sub_pipeline(
                    sub_flow=standardize_mysql_cluster_subflow(
                        root_id=self.root_id,
                        data=copy.deepcopy(self.data),
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        bk_biz_id=cluster_class.bk_biz_id,
                        instances=instances,
                        with_actuator=False,
                        with_bk_plugin=False,
                        with_backup_client=False,
                        with_collect_sysinfo=False,
                        with_instance_standardize=False,
                        with_cc_standardize=False,
                    )
                )
                re_surrounding_sub_pipeline.add_act(
                    act_name=_("解除屏蔽监控 {} {}").format(node["master"]["ip"], node["slave"]["ip"]),
                    act_component_code=MysqlCrondMonitorControlComponent.code,
                    kwargs=asdict(
                        CrondMonitorKwargs(
                            bk_cloud_id=cluster_class.bk_cloud_id,
                            exec_ips=[node["master"]["ip"], node["slave"]["ip"]],
                            port=0,
                            enable=True,
                        )
                    ),
                )
                re_surrounding_sub_pipeline_list.append(
                    re_surrounding_sub_pipeline.build_sub_process(sub_name=_("切换后重新安装周边组件"))
                )

            # 阶段6: 主机级别卸载实例,卸载指定ip下的所有实例
            uninstall_svr_sub_pipeline_list = []
            machines = cluster_info["masters"] + cluster_info["slaves"]
            for ip in machines:
                uninstall_svr_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                uninstall_svr_sub_pipeline.add_act(
                    act_name=_("下发db-actor到节点{}".format(ip)),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=cluster_class.bk_cloud_id,
                            exec_ip=[ip],
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                )
                ins_cluster = {"uninstall_ip": ip, "cluster_id": cluster_info["cluster_id"]}
                uninstall_svr_sub_pipeline.add_act(
                    act_name=_("整机卸载前删除元数据"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.remotedb_migrate_remove_storage.__name__,
                            cluster=ins_cluster,
                            is_update_trans_data=True,
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
                uninstall_svr_sub_pipeline.add_sub_pipeline(
                    sub_flow=remote_node_uninstall_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), ip=ip
                    )
                )
                uninstall_svr_sub_pipeline_list.append(
                    uninstall_svr_sub_pipeline.build_sub_process(sub_name=_("卸载remote节点{}".format(ip)))
                )
            # 安装实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=install_sub_pipeline_list)
            # 数据同步
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
            # 切换前安装周边
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=surrounding_sub_pipeline_list)
            # 人工确认切换迁移实例
            tendb_migrate_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})
            # 切换迁移实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_pipeline_list)
            # 更新集群模块信息
            tendb_migrate_pipeline.add_act(
                act_name=_("更新集群db模块信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_cluster_module.__name__,
                        cluster={
                            "cluster_ids": [cluster_id],
                            "new_module_id": new_db_module_id,
                            "major_version": new_db_version,
                        },
                    )
                ),
            )
            #  新机器安装周边组件
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=re_surrounding_sub_pipeline_list)
            # 卸载流程人工确认
            tendb_migrate_pipeline.add_act(act_name=_("人工确认卸载实例"), act_component_code=PauseComponent.code, kwargs={})
            # # 卸载remote节点
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_svr_sub_pipeline_list)
            tendb_migrate_pipeline_all_list.append(
                tendb_migrate_pipeline.build_sub_process(_("集群迁移{}").format(self.data["cluster_id"]))
            )
        # 运行流程
        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(tendb_migrate_pipeline_all_list)
        tendb_migrate_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)

    def build_sync_data_sub_pipeline(self, cluster_info: dict, backup_info: dict, cluster_class: Cluster) -> list:
        """构建数据同步子流程
        Args:
            cluster_info: 集群信息
            backup_info: 备份信息
            cluster_class: 集群类实例
        Returns:
            list: 数据同步子流程列表
        """
        sync_data_sub_pipeline_list = []
        for shard_id, node in cluster_info["shards"].items():
            # 构建实例集群信息
            ins_cluster = self._build_instance_cluster_info(cluster_info, node, shard_id)
            # 构建同步数据子流程
            sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            if self.ticket_data["backup_source"] == MySQLBackupSource.REMOTE.value:
                # 远程备份源场景
                self._handle_remote_backup_sync(sync_data_sub_pipeline, backup_info, shard_id, ins_cluster)
            else:
                # 本地备份源场景
                self._handle_local_backup_sync(sync_data_sub_pipeline, node, ins_cluster, cluster_class)

            # 添加同步完成后的元数据更新动作
            sync_data_sub_pipeline.add_act(
                act_name=_("同步完毕,写入数据节点的主从关系"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.remotedb_migrate_add_storage_tuple.__name__,
                        cluster=ins_cluster,
                        is_update_trans_data=True,
                    )
                ),
            )
            sync_data_sub_pipeline_list.append(sync_data_sub_pipeline.build_sub_process(sub_name=_("恢复实例数据")))
        return sync_data_sub_pipeline_list

    def _build_instance_cluster_info(self, cluster_info: dict, node: dict, shard_id: str) -> dict:
        """构建实例集群信息
        Args:
            cluster_info: 集群信息
            node: 节点信息
            shard_id: 分片ID
        Returns:
            dict: 实例集群信息
        """
        ins_cluster = copy.deepcopy(cluster_info["cluster"])
        ins_cluster.update(
            {
                "charset": cluster_info["charset"],
                "new_master_ip": node["new_master"]["ip"],
                "new_slave_ip": node["new_slave"]["ip"],
                "new_master_port": node["new_master"]["port"],
                "new_slave_port": node["new_slave"]["port"],
                "master_ip": node["master"]["ip"],
                "slave_ip": node["slave"]["ip"],
                "master_port": node["master"]["port"],
                "slave_port": node["slave"]["port"],
                "file_target_path": f"{self.backup_target_path}/{node['new_master']['port']}",
                "shard_id": shard_id,
                "change_master_force": False,
            }
        )
        return ins_cluster

    def _handle_remote_backup_sync(self, pipeline: SubBuilder, backup_info: dict, shard_id: str, ins_cluster: dict):
        """处理远程备份源同步场景

        Args:
            pipeline: 流程构建器
            backup_info: 备份信息
            shard_id: 分片ID
            ins_cluster: 实例集群信息
        """
        shard_backupinfo = backup_info["remote_node"].get(shard_id, {})
        ins_cluster["backupinfo"] = shard_backupinfo
        logger.debug(shard_backupinfo)

        if not shard_backupinfo or not shard_backupinfo.get("file_list_details"):
            error_msg = _("获取集群分片 {} shard {} 的备份信息失败").format(self.data["cluster_id"], shard_id)
            logger.error("cluster %s shard %s backup info not exists", self.data["cluster_id"], shard_id)
            raise TendbGetBackupInfoFailedException(message=_(error_msg))

        pipeline.add_sub_pipeline(
            sub_flow=remote_instance_migrate_sub_flow(
                root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=ins_cluster
            )
        )

    def _handle_local_backup_sync(self, pipeline: SubBuilder, node: dict, ins_cluster: dict, cluster_class: Cluster):
        """处理本地备份源同步场景

        Args:
            pipeline: 流程构建器
            node: 节点信息
            ins_cluster: 实例集群信息
            cluster_class: 集群类实例
        """
        ins_cluster["change_master"] = False
        inst_list = [
            f"{node['master']['ip']}{IP_PORT_DIVIDER}{node['master']['port']}",
            f"{node['slave']['ip']}{IP_PORT_DIVIDER}{node['slave']['port']}",
        ]

        pipeline.add_sub_pipeline(
            sub_flow=mysql_restore_master_slave_sub_flow(
                root_id=self.root_id,
                ticket_data=copy.deepcopy(self.data),
                cluster=ins_cluster,
                cluster_model=cluster_class,
                ins_list=inst_list,
            )
        )


def build_install_remote_mspair_sub_pipeline(
    uid,
    root_id,
    parent_global_data,
    cluster,
    new_master_ip,
    new_slave_ip,
    ports,
    bk_host_ids,
    db_config,
    pkg_id,
    db_module_id,
):
    install_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(parent_global_data))

    install_sub_pipeline.add_sub_pipeline(
        sub_flow=install_mysql_in_cluster_sub_flow(
            uid=uid,
            root_id=root_id,
            cluster=cluster,
            new_mysql_list=[new_master_ip, new_slave_ip],
            install_ports=ports,
            bk_host_ids=bk_host_ids,
            pkg_id=pkg_id,
            db_config=db_config,
            db_module_id=str(db_module_id),
        )
    )

    cluster_info = {
        "new_master_ip": new_master_ip,
        "new_slave_ip": new_slave_ip,
        "bk_cloud_id": cluster.bk_cloud_id,
        "ports": ports,
        "bk_biz_id": cluster.bk_biz_id,
        "cluster_id": cluster.id,
        "version": cluster.major_version,
    }

    install_sub_pipeline.add_act(
        act_name=_("写入初始化实例的db_meta元信息"),
        act_component_code=SpiderDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=SpiderDBMeta.remotedb_migrate_add_install_nodes.__name__,
                cluster=copy.deepcopy(cluster_info),
                is_update_trans_data=False,
            )
        ),
    )

    install_sub_pipeline.add_act(
        act_name=_("安装backup-client工具"),
        act_component_code=DownloadBackupClientComponent.code,
        kwargs=asdict(
            DownloadBackupClientKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                bk_biz_id=int(cluster.bk_biz_id),
                download_host_list=[new_master_ip, new_slave_ip],
            )
        ),
    )

    exec_act_kwargs = ExecActuatorKwargs(
        cluster=cluster_info,
        bk_cloud_id=cluster.bk_cloud_id,
        cluster_type=cluster.cluster_type,
        get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
        exec_ip=[new_master_ip, new_slave_ip],
    )
    install_sub_pipeline.add_act(
        act_name=_("安装临时备份程序"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    return install_sub_pipeline.build_sub_process(sub_name=_("安装MySQL主从实例"))
