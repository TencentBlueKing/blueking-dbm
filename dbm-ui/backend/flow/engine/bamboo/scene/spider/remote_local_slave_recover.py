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

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceStatus
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.spider.common.exceptions import TendbGetBackupInfoFailedException
from backend.flow.engine.bamboo.scene.spider.spider_remote_node_migrate import remote_slave_recover_sub_flow
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.flow.utils.spider.tendb_cluster_info import get_slave_local_recover_info

logger = logging.getLogger("flow")


class TenDBRemoteSlaveLocalRecoverFlow(object):
    """
    TenDB 后端从节点恢复: 迁移机器恢复,指定实例的本地恢复
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param ticket_data : 单据传递参数
        """
        self.root_id = root_id
        self.ticket_data = ticket_data
        self.data = {}

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
            self.data["bk_cloud_id"] = self.ticket_data["bk_cloud_id"]
            self.data["root_id"] = self.root_id
            self.data["uid"] = self.ticket_data["uid"]
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["bk_biz_id"] = self.ticket_data["bk_biz_id"]
            self.data["created_by"] = self.ticket_data["created_by"]
            # self.data["module"] = info["module"]
            # 卸载流程时强制卸载
            self.data["force"] = True
            #  先判断备份是否存在
            backup_handler = FixPointRollbackHandler(self.data["cluster_id"])
            restore_time = datetime.now()
            # restore_time = datetime.strptime("2023-07-31 17:40:00", "%Y-%m-%d %H:%M:%S")
            backup_info = backup_handler.query_latest_backup_log(restore_time)
            if backup_info is None:
                logger.error("cluster {} backup info not exists".format(self.data["cluster_id"]))
                raise TendbGetBackupInfoFailedException(message=_("获取集群 {} 的备份信息失败".format(self.data["cluster_id"])))
            logger.debug(backup_info)

            cluster_info = get_slave_local_recover_info(self.data["cluster_id"], self.data["storage_id"])
            charset, db_version = get_version_and_charset(
                bk_biz_id=cluster_info["bk_biz_id"],
                db_module_id=cluster_info["db_module_id"],
                cluster_type=cluster_info["cluster_type"],
            )
            cluster_info["charset"] = charset
            cluster_info["db_version"] = db_version
            self.data["target_ip"] = cluster_info["target_ip"]
            tendb_migrate_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))

            cluster_info["ports"] = []
            for shard_id, shard in cluster_info["my_shards"].items():
                slave = {
                    "ip": self.data["target_ip"],
                    "port": shard["port"],
                    "bk_cloud_id": self.data["bk_cloud_id"],
                    "instance": "{}{}{}".format(self.data["target_ip"], IP_PORT_DIVIDER, shard["port"]),
                }
                cluster_info["my_shards"][shard_id]["new_slave"] = slave
                cluster_info["ports"].append(shard["port"])

            sync_data_sub_pipeline_list = []
            for shard_id, node in cluster_info["my_shards"].items():
                ins_cluster = copy.deepcopy(cluster_info["cluster"])
                ins_cluster["charset"] = cluster_info["charset"]
                ins_cluster["new_slave_ip"] = node["new_slave"]["ip"]
                ins_cluster["new_slave_port"] = node["new_slave"]["port"]
                ins_cluster["master_ip"] = node["master"]["ip"]
                ins_cluster["slave_ip"] = node["slave"]["ip"]
                ins_cluster["master_port"] = node["master"]["port"]
                ins_cluster["slave_port"] = node["slave"]["port"]
                # 设置实例状态
                ins_cluster["storage_id"] = node["slave"]["id"]
                ins_cluster["storage_status"] = InstanceStatus.RESTORING.value
                # todo 正式环境放开file_target_path,需要备份接口支持自动创建目录
                # ins_cluster["file_target_path"] = "/data/dbbak/{}/{}"\
                #     .format(self.root_id, ins_cluster["new_master_port"])
                ins_cluster["file_target_path"] = "/home/mysql/install"
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
                sync_data_sub_pipeline.add_act(
                    act_name=_("写入初始化实例的db_meta元信息"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.tendb_modify_storage_status.__name__,
                            cluster=copy.deepcopy(ins_cluster),
                            is_update_trans_data=False,
                        )
                    ),
                )
                exec_act_kwargs = ExecActuatorKwargs(
                    bk_cloud_id=int(ins_cluster["bk_cloud_id"]),
                    cluster_type=ClusterType.TenDBCluster,
                )
                exec_act_kwargs.exec_ip = ins_cluster["new_slave_ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clean_mysql_payload.__name__
                sync_data_sub_pipeline.add_act(
                    act_name=_("slave重建之清理从库{}").format(exec_act_kwargs.exec_ip),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )

                sync_data_sub_pipeline.add_sub_pipeline(
                    sub_flow=remote_slave_recover_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=ins_cluster
                    )
                )
                ins_cluster["storage_status"] = InstanceStatus.RUNNING.value
                sync_data_sub_pipeline.add_act(
                    act_name=_("写入初始化实例的db_meta元信息"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.tendb_modify_storage_status.__name__,
                            cluster=copy.deepcopy(ins_cluster),
                            is_update_trans_data=False,
                        )
                    ),
                )
                sync_data_sub_pipeline_list.append(sync_data_sub_pipeline.build_sub_process(sub_name=_("恢复实例数据")))

            tendb_migrate_pipeline.add_act(
                act_name=_("下发工具"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster_info["bk_cloud_id"],
                        exec_ip=self.data["target_ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )
            tendb_migrate_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
            tendb_migrate_pipeline_all_list.append(
                tendb_migrate_pipeline.build_sub_process(_("集群迁移{}").format(self.data["cluster_id"]))
            )

        # 运行流程
        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(tendb_migrate_pipeline_all_list)
        tendb_migrate_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)
