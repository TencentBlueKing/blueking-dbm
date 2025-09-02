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
import datetime
import logging
import uuid
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterPhase, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_report.mysql_backup.handers import MySQLBackupHandler
from backend.flow.consts import DBA_SYSTEM_USER, MySQLBackupTypeEnum, RollbackType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.get_local_backup import check_storage_database
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import (
    change_master_by_master_status,
    tendbha_rollback_data_sub_flow,
)
from backend.flow.engine.bamboo.scene.spider.common.exceptions import (
    NormalSpiderFlowException,
    TendbGetBackupInfoFailedException,
)
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_crond_control import MysqlCrondMonitorControlComponent
from backend.flow.plugins.components.collections.mysql.mysql_rds_execute import MySQLExecuteRdsComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.remotedb_node_priv_recover import RemoteDbPrivRecoverComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
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

    def tendb_rollback_data(self):  # noqa C901
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
                backup_handler = MySQLBackupHandler(cluster_id=source_cluster.id, is_full_backup=True)
                rollback_time = str2datetime(self.data["rollback_time"])
                backup_info = backup_handler.get_spider_rollback_backup_info(latest_time=rollback_time, limit_one=True)
                if backup_info is None:
                    logger.error("cluster {} backup info not exists".format(self.data["source_cluster_id"]))
                    raise TendbGetBackupInfoFailedException(
                        message=_(
                            "获取实例 {} 的备份信息失败 {} sql: {}".format(
                                self.data["source_cluster_id"], backup_handler.errmsg, backup_handler.query
                            )
                        )
                    )
            # 将shard id 转换为int类型。字段入库后，后端存储是json字段，会自动把key为int --> str。
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
            # rds先抽取出spider spider_slave 实例列表
            remote_node_users = {}
            spider_instance_list = []

            cluster = {
                "cluster_id": target_cluster.id,
                "cluster_phase": ClusterPhase.OFFLINE.value,
            }
            tendb_rollback_pipeline.add_act(
                act_name=_("设置集群为禁用状态"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.tendb_modify_cluster_phase.__name__,
                        cluster=cluster,
                        is_update_trans_data=False,
                    )
                ),
            )
            tendb_rollback_pipeline.add_act(
                act_name=_("屏蔽 {} 告警".format(clusters_info["target_immute_domain"])),
                act_component_code=AddAlarmShieldComponent.code,
                kwargs={
                    "begin_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": (datetime.datetime.now() + datetime.timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
                    "description": clusters_info["target_immute_domain"],
                    "dimensions": [
                        {
                            "name": "instance_host",
                            "values": clusters_info["ip_list"],
                        }
                    ],
                },
            )
            cluster = {
                "host": clusters_info["target"]["dbctl_ip"],
                "port": clusters_info["target"]["spider_port"],
                "backup_id": str(uuid.uuid1()),
            }
            exec_act_kwargs = ExecActuatorKwargs(
                exec_ip=clusters_info["target"]["dbctl_ip"],
                bk_cloud_id=target_cluster.bk_cloud_id,
                cluster_type=target_cluster.cluster_type,
                run_as_system_user=DBA_SYSTEM_USER,
                cluster=cluster,
                get_mysql_payload_func=MysqlActPayload.spider_priv_backup_demand_payload.__name__,
            )
            tendb_rollback_pipeline.add_act(
                act_name=_("回滚前在中控节点备份权限{}").format(exec_act_kwargs.exec_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )
            exec_act_kwargs.run_as_system_user = None
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
                spider_instance_list.append(spider_node["instance"])
                target_spider = target_cluster.proxyinstance_set.get(
                    machine__ip=spider_node["ip"], port=spider_node["port"]
                )
                spd_cluster = {
                    "charset": charset,
                    # "backupinfo": backup_info["spider_node"],
                    "file_target_path": f'{self.backup_target_path}/{spider_node["port"]}',
                    "rollback_ip": spider_node["ip"],
                    "rollback_port": spider_node["port"],
                    "instance": spider_node["instance"],
                    "bk_cloud_id": source_cluster.bk_cloud_id,
                    "cluster_id": source_cluster.id,
                    "rollback_time": self.data["rollback_time"],
                    "databases": self.data["databases"],
                    "tables": self.data["tables"],
                    "databases_ignore": self.data["databases_ignore"],
                    "tables_ignore": self.data["tables_ignore"],
                    "change_master": False,
                    "all_database_rollback": self.data["all_database_rollback"],
                    # 由于不恢复binlog。所以设置为仅 BACKUPID 恢复
                    "rollback_type": RollbackType.REMOTE_AND_BACKUPID,
                }
                spd_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))

                cluster = {"proxy_status": InstanceStatus.RESTORING.value, "proxy_ids": [target_spider.id]}
                spd_sub_pipeline.add_act(
                    act_name=_("设置节点为恢复中状态"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.tendb_modify_proxy_status.__name__,
                            cluster=cluster,
                            is_update_trans_data=False,
                        )
                    ),
                )
                backup_info_tmp, spider_restore_sub_flow = tendbha_rollback_data_sub_flow(
                    root_id=self.root_id,
                    uid=self.ticket_data["uid"],
                    cluster_model=source_cluster,
                    cluster_info=spd_cluster,
                    backup_info=backup_info["spider_node"],
                )
                spd_sub_pipeline.add_sub_pipeline(sub_flow=spider_restore_sub_flow)

                cluster = {"proxy_status": InstanceStatus.RUNNING.value, "proxy_ids": [target_spider.id]}
                spd_sub_pipeline.add_act(
                    act_name=_("设置节点为正常状态"),
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
                    # ctl_cluster["backupinfo"] = backup_info["tdbctl_node"]
                    ctl_cluster["rollback_port"] = spider_node["admin_port"]
                    ctl_cluster["file_target_path"] = f'{self.backup_target_path}/{spider_node["admin_port"]}'
                    ctl_cluster["instance"] = f'{spider_node["ip"]}{IP_PORT_DIVIDER}{spider_node["admin_port"]}'
                    ctl_cluster["init_command"] = "set tc_admin=0"
                    ctl_cluster["enable_binlog"] = True

                    backup_info_tmp, dbctl_restore_sub_flow = tendbha_rollback_data_sub_flow(
                        root_id=self.root_id,
                        uid=self.ticket_data["uid"],
                        cluster_model=source_cluster,
                        cluster_info=ctl_cluster,
                        backup_info=backup_info["tdbctl_node"],
                    )
                    ctl_sub_pipeline.add_sub_pipeline(sub_flow=dbctl_restore_sub_flow)
                    ins_sub_pipeline_list.insert(
                        0, ctl_sub_pipeline.build_sub_process(sub_name=_("{} 中控节点恢复".format(ctl_cluster["instance"])))
                    )

                    ip_results = DRSApi.rpc(
                        {
                            "addresses": [ctl_cluster["instance"]],
                            "cmds": [
                                "select distinct Host from mysql.servers where  Wrapper in ('SPIDER','TDBCTL','SPIDER_SLAVE')"
                            ],
                            "force": False,
                            "bk_cloud_id": target_cluster.bk_cloud_id,
                        }
                    )
                    # 查询代理层作为需要授权的白名单IP
                    if ip_results[0]["error_msg"]:
                        raise NormalSpiderFlowException(message=_("中控节点查询spider/spider_slave/dbCtl信息错误"))
                    if len(ip_results[0]["cmd_results"][0]["table_data"]) < 1:
                        raise NormalSpiderFlowException(message=_("中控节点查询spider/spider_slave/dbCtl数据为空"))

                    spider_instance_list = [i["Host"] for i in ip_results[0]["cmd_results"][0]["table_data"]]
                    # 查询数据层账号密码作为需要执行授权的信息
                    ins_results = DRSApi.rpc(
                        {
                            "addresses": [ctl_cluster["instance"]],
                            "cmds": [
                                """select distinct concat(Host,'{}',Port) as instance, Host,Port,Username,Password from
                                mysql.servers where  Wrapper in ('mysql','mysql_slave') order by Host,Port,Username""".format(
                                    IP_PORT_DIVIDER
                                )
                            ],
                            "force": False,
                            "bk_cloud_id": target_cluster.bk_cloud_id,
                        }
                    )
                    # 查询代理层作为需要授权的白名单IP
                    if ins_results[0]["error_msg"]:
                        raise NormalSpiderFlowException(message=_("中控节点查询remotedb/dr信息错误"))
                    if len(ins_results[0]["cmd_results"][0]["table_data"]) < 1:
                        raise NormalSpiderFlowException(message=_("中控节点查询remotedb/dr数据为空"))
                    for one_ins in ins_results[0]["cmd_results"][0]["table_data"]:
                        remote_node_users[one_ins["instance"]] = one_ins

            # 记录实例的版本,用于权限恢复
            for shard_id, remote_node in clusters_info["shards"].items():
                if int(shard_id) not in backup_info["remote_node"]:
                    raise TendbGetBackupInfoFailedException(message=_("获取remotedb分片 {} 的备份信息不存在".format(shard_id)))
                if backup_info["remote_node"][int(shard_id)] == "":
                    raise TendbGetBackupInfoFailedException(message=_("获取remotedb分片 {} 的备份信息为空".format(shard_id)))

                shard = target_cluster.tendbclusterstorageset_set.get(shard_id=shard_id)
                target_slave = target_cluster.storageinstance_set.get(id=shard.storage_instance_tuple.receiver.id)
                target_master = target_cluster.storageinstance_set.get(id=shard.storage_instance_tuple.ejector.id)

                shard_backup_info = backup_info["remote_node"][int(shard_id)]
                ins_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                cluster = {
                    "storage_status": InstanceStatus.RESTORING.value,
                    "storage_ids": [target_slave.id, target_master.id],
                }
                ins_sub_pipeline.add_act(
                    act_name=_("设置分片为恢复中状态"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.tendb_modify_storage_status.__name__,
                            cluster=cluster,
                            is_update_trans_data=False,
                        )
                    ),
                )

                data_restore_sub_list = []
                master_cluster_info = {
                    "rollback_ip": remote_node["new_master"]["ip"],
                    "rollback_port": remote_node["new_master"]["port"],
                    "file_target_path": f'{self.backup_target_path}/{remote_node["new_master"]["port"]}',
                    "rollback_type": self.data["rollback_type"],
                    "charset": charset,
                    "databases": self.data["databases"],
                    "tables": self.data["tables"],
                    "databases_ignore": self.data["databases_ignore"],
                    "tables_ignore": self.data["tables_ignore"],
                    "rollback_time": self.data["rollback_time"],
                    # "backupinfo": shard_backup_info,
                }
                backup_info_tmp, master_restore_sub_flow = tendbha_rollback_data_sub_flow(
                    root_id=self.root_id,
                    uid=self.ticket_data["uid"],
                    cluster_model=source_cluster,
                    cluster_info=master_cluster_info,
                    backup_info=shard_backup_info,
                )
                data_restore_sub_list.append(master_restore_sub_flow)

                # 由于构造到新tendbCluster集群remote从节点可能是虚拟出来的节点，有可能实际上是主节点信息。
                if remote_node["new_master"]["instance"] != remote_node["new_slave"]["instance"]:
                    slave_cluster_info = {
                        "rollback_ip": remote_node["new_slave"]["ip"],
                        "rollback_port": remote_node["new_slave"]["port"],
                        "file_target_path": f'{self.backup_target_path}/{remote_node["new_slave"]["port"]}',
                        "rollback_type": self.data["rollback_type"],
                        "charset": charset,
                        "databases": self.data["databases"],
                        "tables": self.data["tables"],
                        "databases_ignore": self.data["databases_ignore"],
                        "tables_ignore": self.data["tables_ignore"],
                        "rollback_time": self.data["rollback_time"],
                        # "backupinfo": shard_backup_info,
                    }
                    backup_info_tmp, slave_restore_sub_flow = tendbha_rollback_data_sub_flow(
                        root_id=self.root_id,
                        uid=self.ticket_data["uid"],
                        cluster_model=source_cluster,
                        cluster_info=slave_cluster_info,
                        backup_info=shard_backup_info,
                    )
                    data_restore_sub_list.append(slave_restore_sub_flow)

                ins_sub_pipeline.add_parallel_sub_pipeline(data_restore_sub_list)
                if remote_node["new_master"]["instance"] != remote_node["new_slave"]["instance"]:
                    if shard_backup_info.get("backup_type", "") == MySQLBackupTypeEnum.PHYSICAL.value:
                        change_master_info = {
                            "target_ip": remote_node["new_master"]["ip"],
                            "target_port": remote_node["new_master"]["port"],
                            "repl_ip": remote_node["new_slave"]["ip"],
                            "repl_port": remote_node["new_slave"]["port"],
                            "bk_cloud_id": target_cluster.bk_cloud_id,
                            "cluster_type": target_cluster.cluster_type,
                            "change_master_force": True,
                        }
                        ins_sub_pipeline.add_sub_pipeline(
                            sub_flow=change_master_by_master_status(
                                root_id=self.root_id, uid=self.ticket_data["uid"], cluster_info=change_master_info
                            )
                        )
                    else:
                        ins_sub_pipeline.add_act(
                            act_name=_("从库start slave {}").format(remote_node["new_slave"]["instance"]),
                            act_component_code=MySQLExecuteRdsComponent.code,
                            kwargs=asdict(
                                ExecuteRdsKwargs(
                                    bk_cloud_id=target_cluster.bk_cloud_id,
                                    instance_ip=remote_node["new_slave"]["ip"],
                                    instance_port=remote_node["new_slave"]["port"],
                                    sqls=["start slave"],
                                )
                            ),
                        )

                # 如果备份是物理备份，spider层的路由账号需要恢复
                if shard_backup_info.get("backup_type", "") == MySQLBackupTypeEnum.PHYSICAL.value:
                    ins_sub_pipeline.add_act(
                        act_name=_("恢复所有remoteDB->spider的权限"),
                        act_component_code=RemoteDbPrivRecoverComponent.code,
                        kwargs={
                            "spider_instance_list": spider_instance_list,
                            "bk_cloud_id": target_cluster.bk_cloud_id,
                            "instance_version": target_master.version,
                            "instance": remote_node["new_master"]["instance"],
                            "remote_node_user": remote_node_users[remote_node["new_master"]["instance"]],
                        },
                    )
                    ins_sub_pipeline.add_act(
                        act_name=_("恢复所有remoteDR->spider的权限"),
                        act_component_code=RemoteDbPrivRecoverComponent.code,
                        kwargs={
                            "spider_instance_list": spider_instance_list,
                            "bk_cloud_id": target_cluster.bk_cloud_id,
                            "instance_version": target_slave.version,
                            "instance": remote_node["new_slave"]["instance"],
                            "remote_node_user": remote_node_users[remote_node["new_slave"]["instance"]],
                        },
                    )

                cluster = {
                    "storage_status": InstanceStatus.RUNNING.value,
                    "storage_ids": [target_slave.id, target_master.id],
                }
                ins_sub_pipeline.add_act(
                    act_name=_("设置分片为正常状态"),
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
            cluster = {
                "cluster_id": target_cluster.id,
                "cluster_phase": ClusterPhase.ONLINE.value,
            }
            tendb_rollback_pipeline.add_act(
                act_name=_("设置集群为正常状态"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.tendb_modify_cluster_phase.__name__,
                        cluster=cluster,
                        is_update_trans_data=False,
                    )
                ),
            )
            tendb_rollback_list.append(
                tendb_rollback_pipeline.build_sub_process(
                    sub_name=_("回档集群: {} -> {}".format(source_cluster.id, target_cluster.id))
                )
            )
        tendb_rollback_pipeline_all.add_parallel_sub_pipeline(sub_flow_list=tendb_rollback_list)
        tendb_rollback_pipeline_all.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)
