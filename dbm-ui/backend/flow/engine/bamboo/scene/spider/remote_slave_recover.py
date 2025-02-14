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
from typing import Dict, Optional

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType, MySQLMonitorPauseTime
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.exceptions import MasterInstanceNotExistException
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_surrounding_apps_sub_flow,
    install_mysql_in_cluster_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_instance_config
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import mysql_restore_data_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.recover_slave_instance import slave_recover_sub_flow
from backend.flow.engine.bamboo.scene.spider.spider_remote_node_migrate import remote_node_uninstall_sub_flow
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_crond_control import MysqlCrondMonitorControlComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.plugins.components.collections.spider.switch_remote_slave_routing import (
    SwitchRemoteSlaveRoutingComponent,
)
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
from backend.flow.utils.spider.spider_act_dataclass import InstancePairs, SwitchRemoteSlaveRoutingKwargs
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.flow.utils.spider.tendb_cluster_info import get_slave_recover_info
from backend.ticket.builders.common.constants import MySQLBackupSource

logger = logging.getLogger("flow")


class TenDBRemoteSlaveRecoverFlow(object):
    """
    TenDB Cluster 后端从节点恢复: 迁移机器恢复,指定实例的本地恢复
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param ticket_data : 单据传递参数
        """
        self.root_id = root_id
        self.ticket_data = ticket_data
        self.data = {}
        self.backup_target_path = f"/data/dbbak/{self.root_id}"

    def tendb_remote_slave_recover(self):
        """
        tendb cluster remote slave recover
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = [i["cluster_id"] for i in self.ticket_data["infos"]]
        tendb_migrate_pipeline_all = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        tendb_migrate_pipeline_all_list = []
        # 阶段1 获取集群所有信息。计算端口,构建数据。
        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            cluster_class = Cluster.objects.get(id=self.data["cluster_id"])
            self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
            self.data["root_id"] = self.root_id
            self.data["uid"] = self.ticket_data["uid"]
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["bk_biz_id"] = cluster_class.bk_biz_id
            self.data["db_module_id"] = cluster_class.db_module_id
            self.data["cluster_type"] = cluster_class.cluster_type
            self.data["force"] = True
            self.data["target_ip"] = self.data["new_slave_ip"]
            self.data["source_ip"] = self.data["old_slave_ip"]
            self.data["charset"], self.data["db_version"] = get_version_and_charset(
                bk_biz_id=cluster_class.bk_biz_id,
                db_module_id=cluster_class.db_module_id,
                cluster_type=cluster_class.cluster_type,
            )

            tendb_migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            cluster_info = get_slave_recover_info(cluster_class.id, self.data["source_ip"])
            cluster_info["ports"] = []
            for shard_id, shard in cluster_info["my_shards"].items():
                slave = {
                    "ip": self.data["target_ip"],
                    "port": shard["slave"]["port"],
                    "bk_cloud_id": cluster_class.bk_cloud_id,
                    "instance": "{}{}{}".format(self.data["target_ip"], IP_PORT_DIVIDER, shard["slave"]["port"]),
                }
                cluster_info["my_shards"][shard_id]["new_slave"] = slave
                cluster_info["ports"].append(shard["slave"]["port"])
            #  获取主节点ip
            slaves = StorageInstance.objects.filter(
                machine__bk_cloud_id=cluster_class.bk_cloud_id, machine__ip=self.data["source_ip"]
            )
            slave_tuple = StorageInstanceTuple.objects.filter(receiver=slaves[0])
            if slave_tuple is None or len(slave_tuple) == 0:
                raise MasterInstanceNotExistException(
                    cluster_type=cluster_class.cluster_type, cluster_id=cluster_class.id
                )
            master = StorageInstance.objects.get(id=slave_tuple[0].ejector_id)

            db_config = get_instance_config(cluster_class.bk_cloud_id, master.machine.ip, cluster_info["ports"])

            install_sub_pipeline_list = []
            install_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            install_sub_pipeline.add_sub_pipeline(
                sub_flow=install_mysql_in_cluster_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster_class,
                    new_mysql_list=[self.data["target_ip"]],
                    install_ports=cluster_info["ports"],
                    bk_host_ids=[self.data["bk_new_slave"]["bk_host_id"]],
                    db_config=db_config,
                )
            )
            cluster = {
                "new_slave_ip": self.data["target_ip"],
                "cluster_id": cluster_class.id,
                "bk_cloud_id": cluster_class.bk_cloud_id,
                "bk_biz_id": cluster_class.bk_biz_id,
                "ports": cluster_info["ports"],
                "version": cluster_class.major_version,
            }
            install_sub_pipeline.add_act(
                act_name=_("写入初始化实例的db_meta元信息"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.tendb_slave_recover_add_nodes.__name__,
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
                        download_host_list=[cluster["new_slave_ip"]],
                        bk_biz_id=cluster_class.bk_biz_id,
                    )
                ),
            )

            exec_act_kwargs = ExecActuatorKwargs(
                cluster=cluster,
                bk_cloud_id=cluster_class.bk_cloud_id,
                cluster_type=cluster_class.cluster_type,
                get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
            )
            exec_act_kwargs.exec_ip = [cluster["new_slave_ip"]]
            install_sub_pipeline.add_act(
                act_name=_("安装临时备份程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )
            install_sub_pipeline_list.append(install_sub_pipeline.build_sub_process(sub_name=_("安装remote从节点")))

            sync_data_sub_pipeline_list = []
            for shard_id, node in cluster_info["my_shards"].items():
                ins_cluster = {
                    "cluster_id": cluster_class.id,
                    "master_ip": node["master"]["ip"],
                    "master_port": node["master"]["port"],
                    "new_slave_ip": node["new_slave"]["ip"],
                    "new_slave_port": node["new_slave"]["port"],
                    "bk_cloud_id": cluster_class.bk_cloud_id,
                    "file_target_path": f'{self.backup_target_path}/{node["master"]["port"]}',
                    "change_master_force": True,
                    "charset": self.data["charset"],
                    "cluster_type": cluster_class.cluster_type,
                    "shard_id": shard_id,
                }

                sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                if self.ticket_data["backup_source"] == MySQLBackupSource.REMOTE.value:
                    sync_data_sub_pipeline.add_sub_pipeline(
                        sub_flow=slave_recover_sub_flow(
                            root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=ins_cluster
                        )
                    )
                else:
                    ins_cluster["change_master"] = True
                    inst_list = ["{}{}{}".format(node["master"]["ip"], IP_PORT_DIVIDER, node["master"]["port"])]
                    #  查询出正常的slave节点
                    slaves = cluster_class.storageinstance_set.filter(
                        machine__ip=node["slave"]["ip"],
                        port=node["slave"]["port"],
                        instance_inner_role=InstanceInnerRole.SLAVE.value,
                        status=InstanceStatus.RUNNING.value,
                    ).exclude(machine__ip__in=[node["new_slave"]["ip"]])
                    if len(slaves) > 0:
                        inst_list.append("{}{}{}".format(slaves[0].machine.ip, IP_PORT_DIVIDER, slaves[0].port))
                    sync_data_sub_pipeline.add_sub_pipeline(
                        sub_flow=mysql_restore_data_sub_flow(
                            root_id=self.root_id,
                            ticket_data=copy.deepcopy(self.data),
                            cluster=ins_cluster,
                            cluster_model=cluster_class,
                            ins_list=inst_list,
                        )
                    )
                sync_data_sub_pipeline.add_act(
                    act_name=_("同步完毕,写入主从关系,设置节点为running状态"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.tendb_slave_recover_add_tuple.__name__,
                            cluster=ins_cluster,
                            is_update_trans_data=True,
                        )
                    ),
                )
                sync_data_sub_pipeline_list.append(
                    sync_data_sub_pipeline.build_sub_process(
                        sub_name=_("{}:{}恢复实例数据".format(node["new_slave"]["ip"], node["new_slave"]["port"]))
                    )
                )
            # 阶段4 切换
            switch_sub_pipeline_list = []
            # 切换后写入元数据
            switch_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            tdbctl_pass = get_random_string(length=10)
            switch_slave_class = SwitchRemoteSlaveRoutingKwargs(
                cluster_id=cluster_class.id, switch_remote_instance_pairs=[]
            )
            for shard_id, node in cluster_info["my_shards"].items():
                inst_pairs = InstancePairs(
                    old_ip=node["slave"]["ip"],
                    old_port=node["slave"]["port"],
                    new_ip=node["new_slave"]["ip"],
                    new_port=node["new_slave"]["port"],
                    server_name=f"SPT_SLAVE{shard_id}",
                    tdbctl_pass=tdbctl_pass,
                )
                switch_slave_class.switch_remote_instance_pairs.append(inst_pairs)

            switch_sub_pipeline.add_act(
                act_name=_("切换到新SLAVE机器"),
                act_component_code=SwitchRemoteSlaveRoutingComponent.code,
                kwargs=asdict(switch_slave_class),
            )

            switch_sub_pipeline.add_act(
                act_name=_("SLAVE切换完毕后修改元数据指向"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.tendb_slave_recover_switch.__name__,
                        cluster=cluster_info,
                        is_update_trans_data=True,
                    )
                ),
            )
            switch_sub_pipeline_list.append(switch_sub_pipeline.build_sub_process(sub_name=_("切换SLAVE节点")))

            # 阶段5: 新机器安装周边组件
            surrounding_sub_pipeline_list = []
            re_surrounding_sub_pipeline_list = []
            surrounding_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            surrounding_sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    slave_ip_list=[self.data["target_ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(self.data),
                    collect_sysinfo=True,
                    cluster_type=ClusterType.TenDBCluster.value,
                    is_install_backup=False,
                )
            )
            surrounding_sub_pipeline.add_act(
                act_name=_("屏蔽监控 {}").format(self.data["target_ip"]),
                act_component_code=MysqlCrondMonitorControlComponent.code,
                kwargs=asdict(
                    CrondMonitorKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        exec_ips=[self.data["target_ip"]],
                        port=0,
                        minutes=MySQLMonitorPauseTime.SLAVE_DELAY,
                    )
                ),
            )
            surrounding_sub_pipeline_list.append(surrounding_sub_pipeline.build_sub_process(sub_name=_("新机器安装周边组件")))

            re_surrounding_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            re_surrounding_sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    master_ip_list=[master.machine.ip],
                    slave_ip_list=[self.data["target_ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(self.data),
                    is_init=False,
                    cluster_type=ClusterType.TenDBCluster.value,
                )
            )
            re_surrounding_sub_pipeline.add_act(
                act_name=_("解除屏蔽监控 {}").format(self.data["target_ip"]),
                act_component_code=MysqlCrondMonitorControlComponent.code,
                kwargs=asdict(
                    CrondMonitorKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        exec_ips=[self.data["target_ip"]],
                        port=0,
                        enable=True,
                    )
                ),
            )
            re_surrounding_sub_pipeline_list.append(
                re_surrounding_sub_pipeline.build_sub_process(sub_name=_("切换后重新安装周边组件"))
            )

            # 阶段6 卸载
            uninstall_svr_sub_pipeline_list = []
            uninstall_svr_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            ins_cluster = {"uninstall_ip": self.data["source_ip"], "cluster_id": cluster_info["cluster_id"]}
            uninstall_svr_sub_pipeline.add_act(
                act_name=_("卸载实例前先删除元数据"),
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
                act_name=_("下发db-actor到节点{}".format(self.data["source_ip"])),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        exec_ip=[self.data["source_ip"]],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            uninstall_svr_sub_pipeline.add_act(
                act_name=_("清理机器配置"),
                act_component_code=MySQLClearMachineComponent.code,
                kwargs=asdict(
                    ClearMachineKwargs(
                        exec_ip=self.data["source_ip"],
                        bk_cloud_id=self.data["bk_cloud_id"],
                    )
                ),
            )
            uninstall_svr_sub_pipeline.add_sub_pipeline(
                sub_flow=remote_node_uninstall_sub_flow(
                    root_id=self.root_id, ticket_data=copy.deepcopy(self.data), ip=self.data["source_ip"]
                )
            )
            uninstall_svr_sub_pipeline_list.append(
                uninstall_svr_sub_pipeline.build_sub_process(sub_name=_("卸载remote节点{}".format(self.data["source_ip"])))
            )

            # 安装实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=install_sub_pipeline_list)
            # 数据同步
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
            # 数据同步完毕 安装周边
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=surrounding_sub_pipeline_list)
            # 人工确认切换迁移实例
            tendb_migrate_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})
            # 切换迁移实例
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_sub_pipeline_list)
            # 实例切换完毕 安装周边
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=re_surrounding_sub_pipeline_list)
            # 卸载流程人工确认
            tendb_migrate_pipeline.add_act(act_name=_("人工确认卸载实例"), act_component_code=PauseComponent.code, kwargs={})
            # 卸载remote节点
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_svr_sub_pipeline_list)
            tendb_migrate_pipeline_all_list.append(
                tendb_migrate_pipeline.build_sub_process(_("集群迁移{}").format(self.data["cluster_id"]))
            )
        # 运行流程
        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(tendb_migrate_pipeline_all_list)
        tendb_migrate_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)
