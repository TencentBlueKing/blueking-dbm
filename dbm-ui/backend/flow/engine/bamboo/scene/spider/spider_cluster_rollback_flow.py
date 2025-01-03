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

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.flow.consts import RollbackType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.get_local_backup import check_storage_database
from backend.flow.engine.bamboo.scene.spider.common.exceptions import (
    NormalSpiderFlowException,
    TendbGetBackupInfoFailedException,
)
from backend.flow.engine.bamboo.scene.spider.spider_recover import remote_node_rollback, spider_recover_sub_flow
from backend.flow.plugins.components.collections.mysql.mysql_crond_control import MysqlCrondMonitorControlComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import CrondMonitorKwargs, DBMetaOPKwargs, DownloadMediaKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.flow.utils.spider.tendb_cluster_info import get_rollback_clusters_info
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")


class TenDBRollBackDataFlow(object):
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
        self.backup_target_path = f"/data/dbbak/{self.root_id}"

    def tendb_rollback_data(self):
        """
        tendb rollback data
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = [i["source_cluster_id"] for i in self.ticket_data["infos"]]
        cluster_desc = [i["target_cluster_id"] for i in self.ticket_data["infos"]]
        cluster_ids.extend(cluster_desc)
        tendb_rollback_pipeline_all = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        tendb_rollback_list = []
        for info in self.ticket_data["infos"]:
            self.data = info
            # 判断是否全库回档,默认是全库,全库包括逻辑备份，物理备份. todo 如果指定部分库。则只能使用逻辑备份。
            self.data["all_database_rollback"] = True
            if not (
                self.data["databases"][0] == "*"
                and self.data["tables"][0] == "*"
                and len(self.data["databases_ignore"]) == 0
            ):
                self.data["all_database_rollback"] = False
            source_cluster = Cluster.objects.get(id=self.data["source_cluster_id"])
            target_cluster = Cluster.objects.get(id=self.data["target_cluster_id"])
            self.data["uid"] = self.ticket_data["uid"]
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["bk_biz_id"] = source_cluster.bk_biz_id
            self.data["bk_cloud_id"] = source_cluster.bk_cloud_id
            self.data["module"] = source_cluster.db_module_id
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            tendb_rollback_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            clusters_info = get_rollback_clusters_info(
                source_cluster_id=self.data["source_cluster_id"], target_cluster_id=self.data["target_cluster_id"]
            )
            charset, db_version = get_version_and_charset(
                bk_biz_id=source_cluster.bk_biz_id,
                db_module_id=source_cluster.db_module_id,
                cluster_type=source_cluster.cluster_type,
            )
            # 先查询恢复介质
            if self.data["rollback_type"] == RollbackType.REMOTE_AND_BACKUPID.value:
                backup_info = self.data["backupinfo"]
            else:
                rollback_handler = FixPointRollbackHandler(self.data["source_cluster_id"])
                rollback_time = self.data["rollback_time"]
                backup_info = rollback_handler.query_latest_backup_log(str2datetime(rollback_time))
                if backup_info is None:
                    logger.error("cluster {} backup info not exists".format(self.data["source_cluster_id"]))
                    raise TendbGetBackupInfoFailedException(
                        message=_("获取实例 {} 的备份信息失败".format(self.data["source_cluster_id"]))
                    )
            # 将shard id 转换为int类型。TODO: 字段入库后，后端存储是json字段，会自动把key为int --> str。
            backup_info["remote_node"] = {int(shard_id): info for shard_id, info in backup_info["remote_node"].items()}

            # 下发 actuator
            tendb_rollback_pipeline.add_act(
                act_name=_("下发actuator工具 {}".format(clusters_info["ip_list"])),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=target_cluster.bk_cloud_id,
                        exec_ip=clusters_info["ip_list"],
                        file_list=GetFileList(DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            ins_sub_pipeline_list = []
            for spider_node in clusters_info["target_spiders"]:
                if "spider_node" not in backup_info:
                    raise TendbGetBackupInfoFailedException(message=_("获取spider节点备份信息不存在"))
                if backup_info["spider_node"] == "" or len(backup_info["spider_node"]) == 0:
                    raise TendbGetBackupInfoFailedException(message=_("获取spider节点备份信息为空"))
                if not check_storage_database(target_cluster.bk_cloud_id, spider_node["ip"], spider_node["port"]):
                    logger.error("cluster {} check database fail".format(target_cluster.id))
                    raise NormalSpiderFlowException(
                        message=_("回档集群 {} 空闲检查不通过，请确认回档集群是否存在非系统数据库".format(target_cluster.id))
                    )
                target_spider = target_cluster.proxyinstance_set.get(
                    machine__ip=spider_node["ip"], port=spider_node["port"]
                )
                spd_cluster = {
                    "charset": charset,
                    "backupinfo": backup_info["spider_node"],
                    "file_target_path": f'{self.backup_target_path}/{spider_node["port"]}',
                    "rollback_ip": spider_node["ip"],
                    "rollback_port": spider_node["port"],
                    "instance": spider_node["instance"],
                    "bk_cloud_id": source_cluster.bk_cloud_id,
                    "cluster_id": source_cluster.id,
                    "rollback_time": self.data["rollback_time"],
                    "rollback_type": self.data["rollback_type"],
                    "databases": self.data["databases"],
                    "tables": self.data["tables"],
                    "databases_ignore": self.data["databases_ignore"],
                    "tables_ignore": self.data["tables_ignore"],
                    "change_master": False,
                    "all_database_rollback": self.data["all_database_rollback"],
                }
                spd_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                spd_sub_pipeline.add_act(
                    act_name=_("屏蔽监控 {}").format(spider_node["instance"]),
                    act_component_code=MysqlCrondMonitorControlComponent.code,
                    kwargs=asdict(
                        CrondMonitorKwargs(
                            bk_cloud_id=target_cluster.bk_cloud_id,
                            exec_ips=[spider_node["ip"]],
                            port=spider_node["port"],
                        )
                    ),
                )
                cluster = {"proxy_status": InstanceStatus.RESTORING.value, "proxy_ids": [target_spider.id]}
                spd_sub_pipeline.add_act(
                    act_name=_("写入初始化实例的db_meta元信息"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.tendb_modify_proxy_status.__name__,
                            cluster=cluster,
                            is_update_trans_data=False,
                        )
                    ),
                )
                spd_sub_pipeline.add_sub_pipeline(
                    sub_flow=spider_recover_sub_flow(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster=spd_cluster
                    )
                )

                cluster = {"proxy_status": InstanceStatus.RUNNING.value, "proxy_ids": [target_spider.id]}
                spd_sub_pipeline.add_act(
                    act_name=_("写入初始化实例的db_meta元信息"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.tendb_modify_proxy_status.__name__,
                            cluster=cluster,
                            is_update_trans_data=False,
                        )
                    ),
                )
                spd_sub_pipeline.add_act(
                    act_name=_("解除监控屏蔽 {}").format(spider_node["instance"]),
                    act_component_code=MysqlCrondMonitorControlComponent.code,
                    kwargs=asdict(
                        CrondMonitorKwargs(
                            bk_cloud_id=target_cluster.bk_cloud_id,
                            exec_ips=[spider_node["ip"]],
                            port=spider_node["port"],
                            enable=True,
                        )
                    ),
                )
                ins_sub_pipeline_list.append(
                    spd_sub_pipeline.build_sub_process(sub_name=_("{} spider节点恢复".format(spider_node["instance"])))
                )
                # 恢复中控节点，有且只有1个中控
                if spider_node["is_admin"]:
                    if "tdbctl_node" not in backup_info:
                        raise TendbGetBackupInfoFailedException(message=_("获取中控节点备份信息不存在"))
                    if backup_info["tdbctl_node"] == "" or len(backup_info["tdbctl_node"]) == 0:
                        raise TendbGetBackupInfoFailedException(message=_("获取中控节点备份信息为空"))
                    ctl_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                    ctl_cluster = copy.deepcopy(spd_cluster)
                    ctl_cluster["backupinfo"] = backup_info["tdbctl_node"]
                    ctl_cluster["rollback_port"] = spider_node["admin_port"]
                    ctl_cluster["file_target_path"] = f'{self.backup_target_path}/{spider_node["admin_port"]}'
                    ctl_cluster["instance"] = f'{spider_node["ip"]}{IP_PORT_DIVIDER}{spider_node["admin_port"]}'
                    ctl_cluster["init_command"] = "set tc_admin=0"
                    ctl_cluster["enable_binlog"] = True
                    ctl_sub_pipeline.add_sub_pipeline(
                        sub_flow=spider_recover_sub_flow(
                            root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster=ctl_cluster
                        )
                    )
                    ins_sub_pipeline_list.insert(
                        0, ctl_sub_pipeline.build_sub_process(sub_name=_("{} 中控节点恢复".format(ctl_cluster["instance"])))
                    )

            for shard_id, remote_node in clusters_info["shards"].items():
                if int(shard_id) not in backup_info["remote_node"]:
                    raise TendbGetBackupInfoFailedException(message=_("获取remotedb分片 {} 的备份信息不存在".format(shard_id)))
                if backup_info["remote_node"][int(shard_id)] == "":
                    raise TendbGetBackupInfoFailedException(message=_("获取remotedb分片 {} 的备份信息为空".format(shard_id)))

                shard = target_cluster.tendbclusterstorageset_set.get(shard_id=shard_id)
                target_slave = target_cluster.storageinstance_set.get(id=shard.storage_instance_tuple.receiver.id)
                target_master = target_cluster.storageinstance_set.get(id=shard.storage_instance_tuple.ejector.id)

                shd_cluster = {
                    "charset": charset,
                    "shard_id": shard_id,
                    "new_master_ip": remote_node["new_master"]["ip"],
                    "new_master_port": remote_node["new_master"]["port"],
                    "new_slave_ip": remote_node["new_slave"]["ip"],
                    "new_master": remote_node["new_master"],
                    "new_slave": remote_node["new_slave"],
                    "new_slave_port": remote_node["new_slave"]["port"],
                    "master_ip": remote_node["master"]["ip"],
                    "master_port": remote_node["master"]["port"],
                    "slave_ip": remote_node["slave"]["ip"],
                    "slave_port": remote_node["slave"]["port"],
                    "master": remote_node["master"],
                    "slave": remote_node["slave"],
                    "file_target_path": f'{self.backup_target_path}/{remote_node["new_master"]["port"]}',
                    "cluster_id": source_cluster.id,
                    "bk_cloud_id": source_cluster.bk_cloud_id,
                    "backupinfo": backup_info["remote_node"][int(shard_id)],
                    "rollback_time": self.data["rollback_time"],
                    "rollback_type": self.data["rollback_type"],
                    "databases": self.data["databases"],
                    "tables": self.data["tables"],
                    "databases_ignore": self.data["databases_ignore"],
                    "tables_ignore": self.data["tables_ignore"],
                    "change_master": False,
                    "all_database_rollback": self.data["all_database_rollback"],
                }

                ins_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                cluster = {
                    "storage_status": InstanceStatus.RESTORING.value,
                    "storage_ids": [target_slave.id, target_master.id],
                }
                ins_sub_pipeline.add_act(
                    act_name=_("写入初始化实例的db_meta元信息"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.tendb_modify_storage_status.__name__,
                            cluster=cluster,
                            is_update_trans_data=False,
                        )
                    ),
                )
                # 屏蔽监控
                ins_sub_pipeline.add_act(
                    act_name=_("屏蔽监控 {}").format(shard_id),
                    act_component_code=MysqlCrondMonitorControlComponent.code,
                    kwargs=asdict(
                        CrondMonitorKwargs(
                            bk_cloud_id=target_cluster.bk_cloud_id,
                            exec_ips=[remote_node["new_master"]["ip"], remote_node["new_slave"]["ip"]],
                            port=remote_node["new_master"]["port"],
                        )
                    ),
                )

                ins_sub_pipeline.add_sub_pipeline(
                    sub_flow=remote_node_rollback(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster=shd_cluster
                    )
                )
                cluster = {
                    "storage_status": InstanceStatus.RUNNING.value,
                    "storage_ids": [target_slave.id, target_master.id],
                }
                ins_sub_pipeline.add_act(
                    act_name=_("写入初始化实例的db_meta元信息"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.tendb_modify_storage_status.__name__,
                            cluster=cluster,
                            is_update_trans_data=False,
                        )
                    ),
                )
                ins_sub_pipeline.add_act(
                    act_name=_("解除监控屏蔽 {}").format(shard_id),
                    act_component_code=MysqlCrondMonitorControlComponent.code,
                    kwargs=asdict(
                        CrondMonitorKwargs(
                            bk_cloud_id=target_cluster.bk_cloud_id,
                            exec_ips=[remote_node["new_master"]["ip"], remote_node["new_slave"]["ip"]],
                            port=remote_node["new_master"]["port"],
                            enable=True,
                        )
                    ),
                )
                ins_sub_pipeline_list.append(
                    ins_sub_pipeline.build_sub_process(sub_name=_("{} 分片主从恢复".format(shard_id)))
                )
            tendb_rollback_pipeline.add_parallel_sub_pipeline(sub_flow_list=ins_sub_pipeline_list)
            tendb_rollback_list.append(
                tendb_rollback_pipeline.build_sub_process(
                    sub_name=_("集群回档: src:{} desc:{}".format(source_cluster.id, target_cluster.id))
                )
            )
        tendb_rollback_pipeline_all.add_parallel_sub_pipeline(sub_flow_list=tendb_rollback_list)
        tendb_rollback_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)
