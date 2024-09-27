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

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import build_surrounding_apps_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import mysql_restore_data_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.recover_slave_instance import slave_recover_sub_flow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_crond_control import MysqlCrondMonitorControlComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.mysql_rds_execute import MySQLExecuteRdsComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.switch_remote_spt_routing import (
    SwitchRemoteShardRoutingComponent,
)
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CrondMonitorKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    ExecuteRdsKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.spider.spider_act_dataclass import InstanceServerName, SwitchRemoteShardRoutingKwargs
from backend.ticket.builders.common.constants import MySQLBackupSource

logger = logging.getLogger("flow")


class TenDBRemoteSlaveLocalRecoverFlow(object):
    """
    TenDB Cluster 后端从节点实例数据修复
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

    def tendb_remote_slave_local_recover(self):
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
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["bk_biz_id"] = cluster_class.bk_biz_id
            self.data["db_module_id"] = cluster_class.db_module_id
            self.data["cluster_type"] = cluster_class.cluster_type
            self.data["force"] = True
            self.data["charset"], self.data["db_version"] = get_version_and_charset(
                bk_biz_id=cluster_class.bk_biz_id,
                db_module_id=cluster_class.db_module_id,
                cluster_type=cluster_class.cluster_type,
            )
            tendb_migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            tendb_migrate_pipeline.add_act(
                act_name=_("下发db-actor到节点{}".format(self.data["slave_ip"])),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        exec_ip=[self.data["slave_ip"]],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )
            sync_data_sub_pipeline_list = []
            for shard_id in self.data["shard_ids"]:
                shard = cluster_class.tendbclusterstorageset_set.get(shard_id=shard_id)
                self.data["master"] = shard.storage_instance_tuple.ejector.ip_port
                self.data["master_ip"] = shard.storage_instance_tuple.ejector.machine.ip
                self.data["master_port"] = shard.storage_instance_tuple.ejector.port
                self.data["slave_port"] = shard.storage_instance_tuple.receiver.port
                target_slave = cluster_class.storageinstance_set.get(id=shard.storage_instance_tuple.receiver.id)
                master = cluster_class.storageinstance_set.get(id=shard.storage_instance_tuple.ejector.id)
                cluster = {"storage_status": InstanceStatus.RESTORING.value, "storage_id": target_slave.id}
                sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                sync_data_sub_pipeline.add_act(
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
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    cluster_type=cluster_class.cluster_type,
                    cluster=cluster,
                    exec_ip=target_slave.machine.ip,
                )

                sync_data_sub_pipeline.add_act(
                    act_name=_("屏蔽监控 {}").format(target_slave.ip_port),
                    act_component_code=MysqlCrondMonitorControlComponent.code,
                    kwargs=asdict(
                        CrondMonitorKwargs(
                            bk_cloud_id=cluster_class.bk_cloud_id,
                            exec_ips=[target_slave.machine.ip],
                            port=target_slave.port,
                        )
                    ),
                )

                sync_data_sub_pipeline.add_act(
                    act_name=_("从库reset slave {}").format(target_slave.ip_port),
                    act_component_code=MySQLExecuteRdsComponent.code,
                    kwargs=asdict(
                        ExecuteRdsKwargs(
                            bk_cloud_id=cluster_class.bk_cloud_id,
                            instance_ip=target_slave.machine.ip,
                            instance_port=target_slave.port,
                            sqls=["stop slave", "reset slave all"],
                        )
                    ),
                )

                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clean_mysql_payload.__name__
                sync_data_sub_pipeline.add_act(
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
                    "cluster_id": cluster_class.id,
                    "master_ip": master.machine.ip,
                    "master_port": master.port,
                    "new_slave_ip": target_slave.machine.ip,
                    "new_slave_port": target_slave.port,
                    "bk_cloud_id": cluster_class.bk_cloud_id,
                    "file_target_path": f"{self.backup_target_path}/{master.port}",
                    "charset": self.data["charset"],
                    "change_master_force": True,
                    "cluster_type": cluster_class.cluster_type,
                    "shard_id": shard_id,
                }
                if self.ticket_data["backup_source"] == MySQLBackupSource.REMOTE.value:
                    sync_data_sub_pipeline.add_sub_pipeline(
                        sub_flow=slave_recover_sub_flow(
                            root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=cluster
                        )
                    )
                else:
                    cluster["change_master"] = True
                    inst_list = [master.ip_port]
                    sync_data_sub_pipeline.add_sub_pipeline(
                        sub_flow=mysql_restore_data_sub_flow(
                            root_id=self.root_id,
                            ticket_data=copy.deepcopy(self.data),
                            cluster=cluster,
                            cluster_model=cluster_class,
                            ins_list=inst_list,
                        )
                    )
                cluster = {"storage_status": InstanceStatus.RUNNING.value, "storage_id": target_slave.id}
                sync_data_sub_pipeline.add_act(
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
                sync_data_sub_pipeline_list.append(
                    sync_data_sub_pipeline.build_sub_process(
                        _("{} shard {} 原地重建").format(target_slave.ip_port, shard_id)
                    )
                )
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
            tdbctl_pass = get_random_string(length=10)
            switch_slave_class = SwitchRemoteShardRoutingKwargs(cluster_id=cluster_class.id, switch_remote_shard=[])
            for shard_id in self.data["shard_ids"]:
                shard = cluster_class.tendbclusterstorageset_set.get(shard_id=shard_id)
                inst_pairs = InstanceServerName(
                    server_name=f"SPT_SLAVE{shard_id}",
                    new_ip=shard.storage_instance_tuple.receiver.machine.ip,
                    new_port=shard.storage_instance_tuple.receiver.port,
                    tdbctl_pass=tdbctl_pass,
                )
                switch_slave_class.switch_remote_shard.append(inst_pairs)
            tendb_migrate_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})
            tendb_migrate_pipeline.add_act(
                act_name=_("切换回原slave节点"),
                act_component_code=SwitchRemoteShardRoutingComponent.code,
                kwargs=asdict(switch_slave_class),
            )

            #  安装周边
            tendb_migrate_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    master_ip_list=None,
                    slave_ip_list=[self.data["slave_ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(self.data),
                    cluster_type=cluster_class.cluster_type,
                )
            )
            tendb_migrate_pipeline_all_list.append(
                tendb_migrate_pipeline.build_sub_process(_("slave原地重建{}".format(self.data["slave_ip"])))
            )
        # 运行流程
        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(tendb_migrate_pipeline_all_list)
        tendb_migrate_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)
