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
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_surrounding_apps_sub_flow,
    install_mysql_in_cluster_sub_flow,
)
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
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import ClearMachineKwargs, DBMetaOPKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.flow.utils.spider.tendb_cluster_info import get_cluster_info

logger = logging.getLogger("flow")


class TenDBRemoteRebalanceFlow(object):
    """
    TenDB 后端节点主从成对迁移
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param ticket_data : 单据传递参数
        """
        self.root_id = root_id
        self.ticket_data = ticket_data
        self.data = {}

    def tendb_migrate(self):
        """
        tendb 迁移
        """
        # 根据已有的实例计算出端口。nodes 中的每一个ip对应一个流程。
        tendb_migrate_pipeline_all = Builder(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))
        # 阶段1 获取集群所有信息。计算端口,构建数据。
        tendb_migrate_pipeline_all_list = []
        for info in self.ticket_data["infos"]:
            cluster_info = get_cluster_info(info["cluster_id"])

            self.data = {}
            self.data = copy.deepcopy(info)
            self.data["bk_cloud_id"] = cluster_info["bk_cloud_id"]
            self.data["root_id"] = self.root_id
            self.data["start_port"] = 20000
            self.data["uid"] = self.ticket_data["uid"]
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["bk_biz_id"] = self.ticket_data["bk_biz_id"]
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["module"] = info["db_module_id"]
            # 卸载流程时强制卸载
            self.data["force"] = True

            # 先查询备份，如果备份不存在则退出，不安装实例
            # restore_time = datetime.strptime("2023-07-31 17:40:00", "%Y-%m-%d %H:%M:%S")
            backup_handler = FixPointRollbackHandler(self.data["cluster_id"])
            restore_time = datetime.now()
            backup_info = backup_handler.query_latest_backup_log(restore_time)
            if backup_info is None:
                logger.error("cluster {} backup info not exists".format(self.data["cluster_id"]))
                raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(self.data["cluster_id"])))
            logger.debug(backup_info)
            tendb_migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            charset, db_version = get_version_and_charset(
                bk_biz_id=cluster_info["bk_biz_id"],
                db_module_id=cluster_info["db_module_id"],
                cluster_type=cluster_info["cluster_type"],
            )
            cluster_info["charset"] = charset
            cluster_info["db_version"] = db_version
            cluster_class = Cluster.objects.get(id=self.data["cluster_id"])

            shards = len(cluster_info["shards"])
            if self.data["remote_shard_num"] * len(self.data["remote_group"]) != shards:
                return
            cluster_info["ports"] = []
            for port in range(self.data["start_port"], self.data["start_port"] + self.data["remote_shard_num"]):
                cluster_info["ports"].append(port)

            shard_ids = copy.deepcopy(cluster_info["shard_ids"])
            for node in self.data["remote_group"]:
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
                    shard_id = shard_ids.pop(0)
                    cluster_info["shards"][shard_id]["new_master"] = master
                    cluster_info["shards"][shard_id]["new_slave"] = slave

            # 阶段2 安装实例并写入数据
            install_sub_pipeline_list = []
            for node in self.data["remote_group"]:
                install_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                install_sub_pipeline.add_sub_pipeline(
                    sub_flow=install_mysql_in_cluster_sub_flow(
                        uid=self.data["uid"],
                        root_id=self.root_id,
                        cluster=cluster_class,
                        new_mysql_list=[node["master"]["ip"], node["slave"]["ip"]],
                        install_ports=cluster_info["ports"],
                    )
                )
                cluster = {
                    "new_master_ip": node["master"]["ip"],
                    "new_slave_ip": node["slave"]["ip"],
                    "cluster_id": cluster_info["cluster_id"],
                    "bk_cloud_id": cluster_info["bk_cloud_id"],
                    "bk_biz_id": cluster_info["bk_biz_id"],
                    "ports": cluster_info["ports"],
                    "version": cluster_info["cluster"]["major_version"],
                }
                install_sub_pipeline.add_act(
                    act_name=_("写入初始化实例的db_meta元信息"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.remotedb_migrate_add_install_nodes.__name__,
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
                            download_host_list=[cluster["new_master_ip"], cluster["new_slave_ip"]],
                        )
                    ),
                )
                #  安装临时备份程序
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
                install_sub_pipeline_list.append(install_sub_pipeline.build_sub_process(sub_name=_("安装remote主从节点")))

            # 阶段3 逐个实例同步数据到新主从库
            sync_data_sub_pipeline_list = []
            for shard_id, node in cluster_info["shards"].items():
                ins_cluster = copy.deepcopy(cluster_info["cluster"])
                ins_cluster["charset"] = cluster_info["charset"]
                ins_cluster["new_master_ip"] = node["new_master"]["ip"]
                ins_cluster["new_slave_ip"] = node["new_slave"]["ip"]
                ins_cluster["new_master_port"] = node["new_master"]["port"]
                ins_cluster["new_slave_port"] = node["new_slave"]["port"]
                ins_cluster["master_ip"] = node["master"]["ip"]
                ins_cluster["slave_ip"] = node["slave"]["ip"]
                ins_cluster["master_port"] = node["master"]["port"]
                ins_cluster["slave_port"] = node["slave"]["port"]
                ins_cluster["file_target_path"] = f"/data/dbbak/{self.root_id}/{ins_cluster['master_port']}"
                ins_cluster["shard_id"] = shard_id
                ins_cluster["change_master_force"] = False
                ins_cluster["backupinfo"] = backup_info["remote_node"].get(shard_id, {})
                # 判断 remote_node 下每个分片的备份信息是否正常
                if (
                    len(ins_cluster["backupinfo"]) == 0
                    or len(ins_cluster["backupinfo"].get("file_list_details", {})) == 0
                ):
                    logger.error(
                        "cluster {} shard {} backup info not exists".format(self.data["cluster_id"], shard_id)
                    )
                    raise TendbGetBackupInfoFailedException(
                        message=_("获取集群分片 {} shard {}  的备份信息失败".format(self.data["cluster_id"], shard_id))
                    )
                sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                sync_data_sub_pipeline.add_sub_pipeline(
                    sub_flow=remote_instance_migrate_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=ins_cluster
                    )
                )
                sync_data_sub_pipeline.add_act(
                    act_name=_("同步数据完毕,写入数据节点的主从关系相关元数据"),
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
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster_class,
                    migrate_tuples=shard_list,
                    created_by=self.data["created_by"],
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
            for node in self.data["remote_group"]:
                surrounding_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                surrounding_sub_pipeline.add_sub_pipeline(
                    sub_flow=build_surrounding_apps_sub_flow(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        master_ip_list=[node["master"]["ip"]],
                        slave_ip_list=[node["slave"]["ip"]],
                        root_id=self.root_id,
                        parent_global_data=copy.deepcopy(self.data),
                        is_init=True,
                        cluster_type=ClusterType.TenDBCluster.value,
                    )
                )
                surrounding_sub_pipeline_list.append(
                    surrounding_sub_pipeline.build_sub_process(sub_name=_("新机器安装周边组件"))
                )

            # 阶段6: 主机级别卸载实例,卸载指定ip下的所有实例
            uninstall_svr_sub_pipeline_list = []
            machines = cluster_info["masters"] + cluster_info["slaves"]
            for ip in machines:
                uninstall_svr_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                ins_cluster = {"uninstall_ip": ip, "cluster_id": cluster_info["cluster_id"]}
                uninstall_svr_sub_pipeline.add_sub_pipeline(
                    sub_flow=remote_node_uninstall_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), ip=ip
                    )
                )
                uninstall_svr_sub_pipeline.add_act(
                    act_name=_("整机卸载成功后删除元数据"),
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
                uninstall_svr_sub_pipeline_list.append(
                    uninstall_svr_sub_pipeline.build_sub_process(sub_name=_("卸载remote节点{}".format(ip)))
                )
            # 安装实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=install_sub_pipeline_list)
            # 数据同步
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
            # 人工确认切换迁移实例
            tendb_migrate_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})
            # 切换迁移实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_pipeline_list)
            #  新机器安装周边组件
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=surrounding_sub_pipeline_list)
            # 卸载流程人工确认
            tendb_migrate_pipeline.add_act(act_name=_("人工确认卸载实例"), act_component_code=PauseComponent.code, kwargs={})
            # # 卸载remote节点
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_svr_sub_pipeline_list)
            tendb_migrate_pipeline_all_list.append(
                tendb_migrate_pipeline.build_sub_process(_("集群迁移{}").format(self.data["cluster_id"]))
            )
        # 运行流程
        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(tendb_migrate_pipeline_all_list)
        tendb_migrate_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext())
