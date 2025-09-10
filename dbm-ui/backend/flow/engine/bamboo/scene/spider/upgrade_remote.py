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
from datetime import timedelta
from typing import Dict, Optional

from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType, MySQLMonitorPauseTime
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceInnerRole, InstanceRole, InstanceStatus, MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.db_package.models import Package
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import install_mysql_in_cluster_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_instance_config
from backend.flow.engine.bamboo.scene.mysql.common.master_and_slave_switch import master_and_slave_switch_v2
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import (
    mysql_restore_master_slave_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.common.uninstall_instance import uninstall_instance_sub_flow
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
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
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
from backend.flow.utils.mysql.mysql_version_parse import get_sub_version_by_pkg_name
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

    def run(self):
        """
        执行tendbcluster存储层本地升级流程
        """
        if self.ticket_data.get("upgrade_local", False):
            self.local_upgrade()
        else:
            self.migrate_upgrade()

    def local_upgrade(self):
        """
        TenDBCluster存储层本地升级流程:
        1. 先本地升级slave节点
        2. 主从切换
        3. 再升级新的slave节点(原master)
        4. 执行标准化

        数据格式：
        {
            "upgrade_local": True,
            "infos": [
                {
                    "cluster_id": 1,
                    "pkg_id": 123,
                }
            ]
        }
        """
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        tendbcluster_upgrade_pipeline = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )

        sub_pipelines = []
        for info in self.ticket_data["infos"]:
            cluster_id = info["cluster_id"]
            pkg_id = info["pkg_id"]

            # 创建集群本地升级子流程
            cluster_upgrade_flow = TenDBClusterStorageLocalUpgradeFlow(
                root_id=self.root_id, cluster_id=cluster_id, pkg_id=pkg_id, ticket_data=copy.deepcopy(self.ticket_data)
            )

            sub_pipeline = cluster_upgrade_flow.build_upgrade_pipeline()
            sub_pipelines.append(sub_pipeline)

        tendbcluster_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        tendbcluster_upgrade_pipeline.run_pipeline(is_drop_random_user=True)

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
                    sub_flow=uninstall_instance_sub_flow(
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
            filter_ips = None
            if self.ticket_data["backup_source"] == MySQLBackupSource.LOCAL.value:
                filter_ips = [node["master"]["ip"], node["slave"]["ip"]]
            sync_data_sub_pipeline.add_sub_pipeline(
                sub_flow=mysql_restore_master_slave_sub_flow(
                    root_id=self.root_id,
                    ticket_data=copy.deepcopy(self.data),
                    cluster=ins_cluster,
                    cluster_model=cluster_class,
                    filter_ips=filter_ips,
                )
            )

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


class TenDBClusterStorageLocalUpgradeFlow(object):
    """
    TenDBCluster存储层本地升级流程
    1. 先本地升级slave节点
    2. 主从切换
    3. 再升级新的slave节点(原master)
    4. 执行标准化
    """

    def __init__(self, root_id: str, cluster_id: int, pkg_id: int, ticket_data: Dict):
        """
        @param root_id: 任务流程定义的root_id
        @param cluster_id: 集群ID
        @param pkg_id: 升级包ID
        @param ticket_data: 单据传递参数
        """
        self.root_id = root_id
        self.cluster_id = cluster_id
        self.pkg_id = pkg_id
        self.ticket_data = ticket_data
        self.cluster = Cluster.objects.get(id=cluster_id)
        self.new_mysql_pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)

        logger.info(_("开始处理集群 {} 的本地升级，目标版本: {}").format(cluster_id, self.new_mysql_pkg.name))

    def pre_check(self):
        """
        升级前置检查
        1. 检查集群元数据完整性
        2. 检查master和slave实例是否都存在且健康
        3. 检查主从关系是否正确
        4. 检查版本兼容性
        """
        logger.info(_("开始执行集群 {} 的升级前置检查").format(self.cluster_id))

        # 检查集群基本信息
        if not self.cluster:
            raise DBMetaException(message=_("集群 {} 不存在").format(self.cluster_id))

        # 获取集群的remote存储实例
        remote_storage_instances = self._get_remote_storage_instances()
        if not remote_storage_instances:
            raise DBMetaException(message=_("集群 {} 没有找到remote存储实例").format(self.cluster_id))

        # 按主从分组并检查
        master_slave_pairs = self._group_master_slave_pairs(remote_storage_instances)
        if not master_slave_pairs:
            raise DBMetaException(message=_("集群 {} 没有找到有效的主从实例对").format(self.cluster_id))

        logger.info(_("集群 {} 共发现 {} 个主从对").format(self.cluster_id, len(master_slave_pairs)))

        # 检查每个主从对
        for i, pair in enumerate(master_slave_pairs):
            self._check_master_slave_pair(pair, i + 1)

        # 检查版本兼容性
        self._check_version_compatibility()

        logger.info(_("集群 {} 升级前置检查通过").format(self.cluster_id))

    def _check_master_slave_pair(self, pair, pair_index):
        """检查单个主从对的健康状态"""
        master_info = pair.get("master")
        slave_info = pair.get("slave")

        # 检查master实例
        if not master_info:
            raise DBMetaException(message=_("集群 {} 第 {} 个主从对缺少master实例").format(self.cluster_id, pair_index))

        master_instance = master_info["instance"]
        if master_instance.status != InstanceStatus.RUNNING:
            raise DBMetaException(
                message=_("集群 {} master实例 {}:{} 状态异常: {}").format(
                    self.cluster_id, master_info["ip"], master_info["port"], master_instance.status
                )
            )

        if master_instance.instance_inner_role != InstanceInnerRole.MASTER:
            raise DBMetaException(
                message=_("集群 {} 实例 {}:{} 角色配置错误，期望: {}, 实际: {}").format(
                    self.cluster_id,
                    master_info["ip"],
                    master_info["port"],
                    InstanceInnerRole.MASTER,
                    master_instance.instance_inner_role,
                )
            )

        # 检查slave实例
        if not slave_info:
            raise DBMetaException(message=_("集群 {} 第 {} 个主从对缺少slave实例").format(self.cluster_id, pair_index))

        slave_instance = slave_info["instance"]
        if slave_instance.status != InstanceStatus.RUNNING:
            raise DBMetaException(
                message=_("集群 {} slave实例 {}:{} 状态异常: {}").format(
                    self.cluster_id, slave_info["ip"], slave_info["port"], slave_instance.status
                )
            )

        if slave_instance.instance_inner_role != InstanceInnerRole.SLAVE:
            raise DBMetaException(
                message=_("集群 {} 实例 {}:{} 角色配置错误，期望: {}, 实际: {}").format(
                    self.cluster_id,
                    slave_info["ip"],
                    slave_info["port"],
                    InstanceInnerRole.SLAVE,
                    slave_instance.instance_inner_role,
                )
            )

        # 检查主从关系是否正确配置
        self._check_master_slave_relationship(master_instance, slave_instance, pair_index)

        logger.info(
            _("集群 {} 第 {} 个主从对 {}:{} <-> {}:{} 检查通过").format(
                self.cluster_id,
                pair_index,
                master_info["ip"],
                master_info["port"],
                slave_info["ip"],
                slave_info["port"],
            )
        )

    def _check_master_slave_relationship(self, master_instance, slave_instance, pair_index):
        """检查主从关系是否正确配置"""
        try:
            # 检查是否存在正确的StorageInstanceTuple关系
            StorageInstanceTuple.objects.get(ejector=master_instance, receiver=slave_instance)
            logger.debug(_("集群 {} 第 {} 个主从对的主从关系配置正确").format(self.cluster_id, pair_index))
        except StorageInstanceTuple.DoesNotExist:
            raise DBMetaException(
                message=_("集群 {} 第 {} 个主从对 {}:{} <-> {}:{} 主从关系配置错误").format(
                    self.cluster_id,
                    pair_index,
                    master_instance.machine.ip,
                    master_instance.port,
                    slave_instance.machine.ip,
                    slave_instance.port,
                )
            )

    def _check_version_compatibility(self):
        """检查版本兼容性"""
        try:
            # 获取当前集群的版本信息
            current_charset, current_mysql_ver = get_version_and_charset(
                self.cluster.bk_biz_id,
                db_module_id=self.cluster.db_module_id,
                cluster_type=self.cluster.cluster_type,
            )

            # 获取目标版本信息 - 如果有新模块ID的话
            new_db_module_id = self.ticket_data.get("new_db_module_id")
            if new_db_module_id:
                new_charset, new_mysql_ver = get_version_and_charset(
                    self.cluster.bk_biz_id,
                    db_module_id=new_db_module_id,
                    cluster_type=self.cluster.cluster_type,
                )

                # 检查字符集一致性
                if new_charset != current_charset:
                    raise DBMetaException(
                        message=_("集群 {} 升级前后字符集不一致，原字符集: {}，新模块字符集: {}").format(
                            self.cluster_id, current_charset, new_charset
                        )
                    )

                # 检查版本升级的合法性
                upgrade_version_check(current_mysql_ver, new_mysql_ver)
                logger.info(_("集群 {} 版本兼容性检查通过: {} -> {}").format(self.cluster_id, current_mysql_ver, new_mysql_ver))
            else:
                # 如果没有指定新模块，检查当前包版本与当前集群版本的兼容性
                pkg_version = get_sub_version_by_pkg_name(self.new_mysql_pkg.name)
                upgrade_version_check(current_mysql_ver, pkg_version)
                logger.info(_("集群 {} 版本兼容性检查通过: {} -> {}").format(self.cluster_id, current_mysql_ver, pkg_version))

        except Exception as e:
            raise DBMetaException(message=_("集群 {} 版本兼容性检查失败: {}").format(self.cluster_id, str(e)))

    def build_upgrade_pipeline(self):
        """构建升级流水线"""
        # 执行升级前置检查
        self.pre_check()

        sub_pipeline = SubBuilder(
            root_id=self.root_id, data=copy.deepcopy(self.ticket_data), need_random_pass_cluster_ids=[self.cluster_id]
        )

        # 获取集群的remote存储实例
        remote_storage_instances = self._get_remote_storage_instances()

        # 按主从分组
        master_slave_pairs = self._group_master_slave_pairs(remote_storage_instances)

        logger.info(_("集群 {} 共有 {} 个主从对需要升级").format(self.cluster_id, len(master_slave_pairs)))

        # 阶段1: 对所有实例执行MySQL升级前置检查
        self._add_mysql_precheck_for_all_instances(sub_pipeline, master_slave_pairs)

        # 阶段2: 添加告警屏蔽
        self._add_alarm_shield_act(sub_pipeline)

        # 阶段3: 屏蔽监控
        self._add_monitor_shield_act(sub_pipeline, remote_storage_instances)

        # 阶段4: 升级所有slave节点
        slave_upgrade_pipelines = []
        for pair in master_slave_pairs:
            if pair["slave"]:
                slave_pipeline = self._build_upgrade_mysql_subflow(
                    pair["slave"]["ip"],
                    [pair["slave"]["port"]],
                    _("升级slave节点 {}:{}").format(pair["slave"]["ip"], pair["slave"]["port"]),
                    skip_precheck=True,  # 已经在阶段1统一执行过前置检查
                )
                slave_upgrade_pipelines.append(slave_pipeline)

        if slave_upgrade_pipelines:
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=slave_upgrade_pipelines)

        # 阶段5: 主从切换
        switch_pipelines = []
        for pair in master_slave_pairs:
            if pair["master"] and pair["slave"]:
                switch_pipeline = self._build_master_slave_switch_subflow(pair)
                switch_pipelines.append(switch_pipeline)

        if switch_pipelines:
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_pipelines)

        # 阶段6: 升级原master节点（现在是slave）
        original_master_upgrade_pipelines = []
        for pair in master_slave_pairs:
            if pair["master"]:
                original_master_pipeline = self._build_upgrade_mysql_subflow(
                    pair["master"]["ip"],
                    [pair["master"]["port"]],
                    _("升级原master节点 {}:{}").format(pair["master"]["ip"], pair["master"]["port"]),
                    skip_precheck=True,  # 已经在阶段1统一执行过前置检查
                )
                original_master_upgrade_pipelines.append(original_master_pipeline)

        if original_master_upgrade_pipelines:
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=original_master_upgrade_pipelines)

        # 阶段7: 执行标准化
        self._add_standardize_act(sub_pipeline, remote_storage_instances)

        # 阶段8: 解除监控屏蔽
        self._add_monitor_unshield_act(sub_pipeline, remote_storage_instances)

        # 阶段9: 解除告警屏蔽
        self._add_alarm_unshield_act(sub_pipeline)

        return sub_pipeline.build_sub_process(sub_name=_("TenDBCluster集群 {} 存储层本地升级").format(self.cluster_id))

    def _get_remote_storage_instances(self):
        """获取集群的remote存储实例"""
        return self.cluster.storageinstance_set.filter(
            machine_type=MachineType.REMOTE, instance_role__in=[InstanceRole.REMOTE_MASTER, InstanceRole.REMOTE_SLAVE]
        ).select_related("machine")

    def _group_master_slave_pairs(self, instances):
        """将实例按主从配对分组"""
        pairs = []
        masters = {}
        slaves = {}

        for instance in instances:
            key = f"{instance.machine.ip}:{instance.port}"
            info = {"ip": instance.machine.ip, "port": instance.port, "instance": instance}

            if instance.instance_inner_role == InstanceInnerRole.MASTER:
                masters[key] = info
            elif instance.instance_inner_role == InstanceInnerRole.SLAVE:
                slaves[key] = info

        # 通过实例的主从关系来配对
        for master_key, master_info in masters.items():
            # 查找对应的slave
            slave_info = None
            master_instance = master_info["instance"]

            # 通过StorageInstanceTuple查找对应的slave
            slave_tuples = master_instance.as_ejector.all()
            if slave_tuples:
                slave_instance = slave_tuples[0].receiver
                slave_key = f"{slave_instance.machine.ip}:{slave_instance.port}"
                if slave_key in slaves:
                    slave_info = slaves[slave_key]

            pairs.append({"master": master_info, "slave": slave_info})

        return pairs

    def _add_alarm_shield_act(self, sub_pipeline):
        """添加告警屏蔽活动"""
        # 获取集群的所有存储实例IP
        storage_ips = list(
            self.cluster.storageinstance_set.filter(machine_type=MachineType.REMOTE)
            .values_list("machine__ip", flat=True)
            .distinct()
        )

        sub_pipeline.add_act(
            act_name=_("屏蔽集群 {} 告警4小时").format(self.cluster.name),
            act_component_code=AddAlarmShieldComponent.code,
            kwargs={
                "begin_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": (datetime.datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
                "description": _("集群 {} TenDBCluster存储层本地升级操作").format(self.cluster.immute_domain),
                "dimensions": [
                    {
                        "name": "instance_host",
                        "values": storage_ips,
                    }
                ],
            },
        )

    def _add_alarm_unshield_act(self, sub_pipeline):
        """添加解除告警屏蔽活动"""
        sub_pipeline.add_act(act_name=_("解除告警屏蔽"), act_component_code=DisableAlarmShieldComponent.code, kwargs={})

    def _add_monitor_shield_act(self, sub_pipeline, instances):
        """添加监控屏蔽活动"""
        ips = list(set([instance.machine.ip for instance in instances]))

        sub_pipeline.add_act(
            act_name=_("屏蔽监控"),
            act_component_code=MysqlCrondMonitorControlComponent.code,
            kwargs=asdict(
                CrondMonitorKwargs(
                    bk_cloud_id=self.cluster.bk_cloud_id,
                    exec_ips=ips,
                    port=0,
                    minutes=MySQLMonitorPauseTime.SLAVE_DELAY,
                )
            ),
        )

    def _add_monitor_unshield_act(self, sub_pipeline, instances):
        """添加解除监控屏蔽活动"""
        ips = list(set([instance.machine.ip for instance in instances]))

        sub_pipeline.add_act(
            act_name=_("解除监控屏蔽"),
            act_component_code=MysqlCrondMonitorControlComponent.code,
            kwargs=asdict(
                CrondMonitorKwargs(
                    bk_cloud_id=self.cluster.bk_cloud_id,
                    exec_ips=ips,
                    port=0,
                    enable=True,
                )
            ),
        )

    def _build_upgrade_mysql_subflow(self, ip: str, ports: list, sub_name: str, skip_precheck: bool = False):
        """构建MySQL升级子流程"""
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))

        # 如果没有跳过前置检查，则需要下发升级包
        if not skip_precheck:
            # 下发升级包
            sub_pipeline.add_act(
                act_name=_("下发升级的安装包到 {}").format(ip),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=self.cluster.bk_cloud_id,
                        exec_ip=ip,
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_upgrade_package(
                            pkg_id=self.pkg_id, db_version=""
                        ),
                    )
                ),
            )

            # 执行升级前置检查
            cluster_config = {"run": False, "ports": ports, "pkg_id": self.pkg_id}
            exec_act_kwargs = ExecActuatorKwargs(cluster=cluster_config, bk_cloud_id=self.cluster.bk_cloud_id)
            exec_act_kwargs.exec_ip = ip
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_upgrade_payload.__name__

            sub_pipeline.add_act(
                act_name=_("执行本地升级前置检查 {}").format(ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

        # 执行本地升级
        cluster_config = {"run": True, "ports": ports, "pkg_id": self.pkg_id}
        exec_act_kwargs = ExecActuatorKwargs(cluster=cluster_config, bk_cloud_id=self.cluster.bk_cloud_id)
        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_upgrade_payload.__name__

        sub_pipeline.add_act(
            act_name=_("执行本地升级 {}").format(ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        # 更新mysql instance version信息
        sub_pipeline.add_act(
            act_name=_("更新mysql instance version meta信息 {}").format(ip),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_mysql_instance_version.__name__,
                    cluster={"ip": ip, "version": get_sub_version_by_pkg_name(self.new_mysql_pkg.name)},
                )
            ),
        )

        return sub_pipeline.build_sub_process(sub_name=sub_name)

    def _build_master_slave_switch_subflow(self, pair):
        """构建主从切换子流程"""
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))

        master_info = pair["master"]
        slave_info = pair["slave"]

        cluster_switch_info = {
            "cluster_id": self.cluster.id,
            "bk_cloud_id": self.cluster.bk_cloud_id,
            "old_master_ip": master_info["ip"],
            "old_master_port": master_info["port"],
            "old_slave_ip": slave_info["ip"],
            "old_slave_port": slave_info["port"],
            "new_master_ip": slave_info["ip"],
            "new_master_port": slave_info["port"],
            "new_slave_ip": master_info["ip"],
            "new_slave_port": master_info["port"],
            "mysql_port": master_info["port"],
            "master_port": master_info["port"],
            "other_slave_info": [],
        }

        sub_pipeline.add_sub_pipeline(
            sub_flow=master_and_slave_switch_v2(
                root_id=self.root_id,
                ticket_data=copy.deepcopy(self.ticket_data),
                cluster=self.cluster,
                cluster_info=copy.deepcopy(cluster_switch_info),
            )
        )

        # 更新元数据
        sub_pipeline.add_act(
            act_name=_("更新主从切换元数据 {}:{}").format(master_info["ip"], master_info["port"]),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SpiderDBMeta.tendb_remotedb_rebalance_switch.__name__,
                    cluster=cluster_switch_info,
                    is_update_trans_data=True,
                )
            ),
        )

        return sub_pipeline.build_sub_process(
            sub_name=_("主从切换 {}:{} <-> {}:{}").format(
                master_info["ip"], master_info["port"], slave_info["ip"], slave_info["port"]
            )
        )

    def _add_mysql_precheck_for_all_instances(self, sub_pipeline, master_slave_pairs):
        """对所有实例执行MySQL升级前置检查"""
        precheck_pipelines = []

        # 收集所有需要检查的实例
        all_instances = []
        for pair in master_slave_pairs:
            if pair["master"]:
                all_instances.append((pair["master"]["ip"], [pair["master"]["port"]]))
            if pair["slave"]:
                all_instances.append((pair["slave"]["ip"], [pair["slave"]["port"]]))

        logger.info(_("集群 {} 开始对 {} 个实例执行MySQL升级前置检查").format(self.cluster_id, len(all_instances)))

        # 为每个实例创建前置检查子流程
        for ip, ports in all_instances:
            precheck_pipeline = self._build_mysql_precheck_subflow(ip, ports)
            precheck_pipelines.append(precheck_pipeline)

        if precheck_pipelines:
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=precheck_pipelines)

    def _build_mysql_precheck_subflow(self, ip: str, ports: list):
        """构建MySQL升级前置检查子流程"""
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))

        # 下发升级包（前置检查需要）
        sub_pipeline.add_act(
            act_name=_("下发升级包到 {} 用于前置检查").format(ip),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=self.cluster.bk_cloud_id,
                    exec_ip=ip,
                    file_list=GetFileList(db_type=DBType.MySQL).mysql_upgrade_package(
                        pkg_id=self.pkg_id, db_version=""
                    ),
                )
            ),
        )

        # 执行MySQL升级前置检查
        cluster_config = {"run": False, "ports": ports, "pkg_id": self.pkg_id}
        exec_act_kwargs = ExecActuatorKwargs(cluster=cluster_config, bk_cloud_id=self.cluster.bk_cloud_id)
        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_mysql_upgrade_payload.__name__

        sub_pipeline.add_act(
            act_name=_("MySQL升级前置检查 {}:{}").format(ip, ",".join(map(str, ports))),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        return sub_pipeline.build_sub_process(sub_name=_("MySQL升级前置检查 {}:{}").format(ip, ",".join(map(str, ports))))

    def _add_standardize_act(self, sub_pipeline, instances):
        """添加标准化活动"""
        sub_pipeline.add_sub_pipeline(
            sub_flow=standardize_mysql_cluster_subflow(
                root_id=self.root_id,
                data=copy.deepcopy(self.ticket_data),
                bk_cloud_id=self.cluster.bk_cloud_id,
                bk_biz_id=self.cluster.bk_biz_id,
                instances=[f"{instance.machine.ip}:{instance.port}" for instance in instances],
                with_actuator=False,
                with_bk_plugin=False,
                with_collect_sysinfo=False,
                with_cc_standardize=False,
                with_instance_standardize=False,
            )
        )
