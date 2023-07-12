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
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.spider_remote_node_migrate import (
    remote_node_migrate_sub_flow,
    remote_node_uninstall_sub_flow,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ClearMachineKwargs, DBMetaOPKwargs
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.flow.utils.spider.tendb_cluster_info import get_remotedb_info

logger = logging.getLogger("flow")


class TenDBMigrateFlow(object):
    """
    TenDB 后端节点主从成对迁移
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        # todo 初始化数据

    def tendb_migrate(self):
        """
        tendb 迁移
        """
        # 根据已有的实例计算出端口。nodes 中的每一个ip对应一个流程。
        # 根据集群获取版本。
        tendb_migrate_pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.data))
        svr_sub_pipeline_list = []
        for node in self.data["nodes"]:
            svr_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            node_cluster = {
                "cluster_id": node["cluster_id"],
                "bk_cloud_id": self.data["bk_cloud_id"],
                "bk_biz_id": self.data["bk_biz_id"],
                "master_ip": node["master"]["ip"],
                "slave_ip": node["slave"]["ip"],
                "new_master_ip": node["new_master"]["ip"],
                "new_slave_ip": node["new_slave"]["ip"],
            }
            instances = get_remotedb_info(node["master"]["ip"], node["master"]["bk_cloud_id"])
            ports = [one["port"] for one in instances]
            node_cluster["ports"] = ports
            # todo 是使用实例的版本，还是集群的版本
            node_cluster["version"] = instances[0]["version"]
            install_sub_pipeline_list = []
            install_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            #  阶段1 安装主从库
            # todo 并发调起安装子流程
            install_sub_pipeline.add_act(
                act_name=_("写入初始化实例的db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.remotedb_migrate_add_install_nodes.__name__,
                        cluster=node_cluster,
                        is_update_trans_data=True,
                    )
                ),
            )
            install_sub_pipeline_list.append(install_sub_pipeline.build_sub_process(sub_name=_("恢复实例数据 ")))

            # 阶段2 同步数据到新主从库
            sync_data_sub_pipeline_list = []
            for cluster_info in instances:
                ins_cluster = copy.deepcopy(cluster_info)
                ins_cluster["new_master_ip"] = node["new_master"]["ip"]
                ins_cluster["new_slave_ip"] = node["new_slave"]["ip"]
                ins_cluster["new_master_port"] = ins_cluster["port"]
                ins_cluster["new_slave_port"] = ins_cluster["port"]
                ins_cluster["master_ip"] = node["master"]["ip"]
                ins_cluster["slave_ip"] = node["slave"]["ip"]
                ins_cluster["master_port"] = ins_cluster["port"]
                ins_cluster["slave_port"] = ins_cluster["port"]
                ins_cluster["backup_target_path"] = "/data/dbbak/{}/{}".format(self.root_id, ins_cluster["port"])
                ins_cluster["cluster_id"] = node["cluster_id"]
                ins_cluster["bk_cloud_id"] = self.data["bk_cloud_id"]

                sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                sync_data_sub_pipeline.add_sub_pipeline(
                    sub_flow=remote_node_migrate_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=ins_cluster
                    )
                )
                sync_data_sub_pipeline.add_act(
                    act_name=_("同步数据完毕,写入数据节点的主从关系相关元数据"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.remotedb_migrate_add_storage_tuple.__name__,
                            cluster=node_cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                sync_data_sub_pipeline_list.append(sync_data_sub_pipeline.build_sub_process(sub_name=_("恢复实例数据 ")))

            # 阶段3 todo 整机切换实例
            switch_sub_pipeline_list = []
            switch_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            switch_sub_pipeline.add_sub_pipeline(sub_flow=_("切换子流程"))
            switch_sub_pipeline.add_act(
                act_name=_("整机切换完毕后修改元数据指向"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.remotedb_migrate_switch.__name__,
                        cluster=node_cluster,
                        is_update_trans_data=True,
                    )
                ),
            )
            switch_sub_pipeline_list.append(switch_sub_pipeline.build_sub_process(sub_name=_("切换remote node 节点")))

            # 阶段4 主机级别卸载实例,卸载指定ip下的所有实例
            uninstall_db_sub_pipeline_list = []
            for ip in [node["master_ip"], node["slave_ip"]]:
                node_cluster["uninstall_ip"] = ip
                uninstall_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                uninstall_sub_pipeline.add_sub_pipeline(
                    sub_flow=remote_node_uninstall_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), ip=ip
                    )
                )
                # 卸载完毕后修改删除实例信息(整机) 删除元数据
                uninstall_sub_pipeline.add_act(
                    act_name=_("整机卸载成功后删除元数据"),
                    act_component_code=MySQLDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.remotedb_migrate_remove_storage.__name__,
                            cluster=node_cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                # 下线机器
                uninstall_sub_pipeline.add_act(
                    act_name=_("清理机器配置"),
                    act_component_code=MySQLClearMachineComponent.code,
                    kwargs=asdict(
                        ClearMachineKwargs(
                            exec_ip=ip,
                            bk_cloud_id=self.data["bk_cloud_id"],
                        )
                    ),
                )
                uninstall_db_sub_pipeline_list.append(
                    uninstall_sub_pipeline.build_sub_process(sub_name=_("卸载节点实例{}".format(ip)))
                )

            #  安装实例
            svr_sub_pipeline.add_parallel_acts(install_sub_pipeline_list)
            # 同步数据
            svr_sub_pipeline.add_parallel_acts(sync_data_sub_pipeline_list)
            # 人工确认切换
            svr_sub_pipeline.add_act(act_name=_("人工确认切换remote节点"), act_component_code=PauseComponent.code, kwargs={})
            svr_sub_pipeline.add_parallel_acts(switch_sub_pipeline_list)
            # 人工确认卸载实例
            svr_sub_pipeline.add_act(act_name=_("人工确认卸载实例"), act_component_code=PauseComponent.code, kwargs={})
            svr_sub_pipeline.add_parallel_acts(uninstall_db_sub_pipeline_list)
            # 加入并发列表
            svr_sub_pipeline_list.append(
                svr_sub_pipeline.build_sub_process(
                    sub_name=_("成对迁移remote 节点主从实例 {} {}".format(node["master"]["ip"], node["slave"]["ip"]))
                )
            )
        tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=svr_sub_pipeline_list)
        tendb_migrate_pipeline.run_pipeline()
