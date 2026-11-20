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

import logging
import re
from dataclasses import asdict
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_services.mongodb.restore.handlers import MongoDBRestoreHandler
from backend.flow.consts import DirEnum, MongoDBActuatorActionEnum, MongoDBClusterRole
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.download_subtask import DownloadSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.exec_shell_script import ExecShellScript
from backend.flow.engine.bamboo.scene.mongodb.sub_task.instance_op import InstanceOpSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.restore_sub import RestoreSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import (
    MongoDBCluster,
    MongoDBNsFilter,
    MongoNode,
    MongoNodeWithLabel,
    MongoRepository,
    ReplicaSet,
)
from backend.flow.utils.mongodb.mongodb_script_template import prepare_recover_dir_script
from backend.flow.utils.mongodb.mongodb_util import MongoUtil
from backend.flow.utils.mongodb.mongoshake_conf import (
    assert_target_user_collections_sharded_script,
    check_empty_target_script,
    replica_set_connect_uri,
)
from backend.flow.utils.mongodb.version_utils import compare_mongodb_versions
from backend.flow.utils.mysql.mysql_act_dataclass import P2PFileKwargs

logger = logging.getLogger("flow")

SOURCE_BACKUP_TICKET = "backup_ticket"
SOURCE_CLUSTER = "cluster"
BILL_DUMP_DIR = "/data/dbbak/billdump"
BILL_BACKUP_LOOKBACK_DAYS = 30
# 用户库迁移不携带集群元数据。config 在 configsvr 上，灌进去就要重启并改写路由，那是数据构造。
SYSTEM_IGNORE_DBS = ["admin", "config", "local"]


class MongoDBDataMigrateFlow(MongoBaseFlow):
    """把用户库迁入已存在的空集群。

    源可以是单据备份，或可访问集群（含 PITR 构造实例）。
    目标集群保持在线：不重启，不改 configsvr 上的 config.shards / shardIdentity。
    分片→分片：不恢复 configsvr；先从源解析分片表，在目标 mongos 上 shardCollection，再经 mongos 导入。
    分片→副本集：不做 shardCollection，导入同一副本集节点。
    源为分片集群且 source_mode=cluster 时经源 mongos 整体导出，避免孤儿文档和 chunk 迁移带来的重复数据；
    backup_ticket 只有各 shard 的备份，按 shard 串行导入。
    副本集→分片：不做自动 shardCollection，经 mongos 导入。是否已分片默认不检查。
    """

    class Serializer(serializers.Serializer):
        class DataRow(serializers.Serializer):
            source_mode = serializers.ChoiceField(choices=[SOURCE_BACKUP_TICKET, SOURCE_CLUSTER])
            source_cluster_id = serializers.IntegerField()
            target_cluster_id = serializers.IntegerField()
            backup_ticket_id = serializers.IntegerField(required=False)
            ns_filter = MongoDBNsFilter.Serializer(allow_null=True, required=False)

            def validate(self, attrs):
                if attrs["source_mode"] == SOURCE_BACKUP_TICKET and not attrs.get("backup_ticket_id"):
                    raise serializers.ValidationError(_("backup_ticket 模式必须提供 backup_ticket_id"))
                if attrs["source_cluster_id"] == attrs["target_cluster_id"]:
                    raise serializers.ValidationError(_("源集群和目标集群不能相同"))
                return attrs

        uid = serializers.CharField()
        created_by = serializers.CharField()
        bk_biz_id = serializers.IntegerField()
        ticket_type = serializers.CharField()
        infos = DataRow(many=True)

    def __init__(self, root_id: str, data: Optional[Dict]):
        super().__init__(root_id, data)
        self.check_payload()

    def check_payload(self):
        serializer = self.Serializer(data=self.payload)
        if not serializer.is_valid():
            raise Exception("payload is invalid {}".format(serializer.errors))

    def start(self):
        logger.debug("MongoDBDataMigrateFlow start, payload %s", self.payload)
        actuator_workdir = MongoUtil().get_mongodb_os_conf()["file_path"]
        file_list = GetFileList(db_type=DBType.MongoDB).get_db_actuator_package()
        dest_dir = DirEnum.MONGO_RECOVER_DIR.value
        if not dest_dir.startswith("/data/dbbak"):
            raise Exception("dest_dir must start with /data/dbbak")

        cluster_ids = []
        for row in self.payload["infos"]:
            cluster_ids.append(row["source_cluster_id"])
            cluster_ids.append(row["target_cluster_id"])
        cluster_ids = list(dict.fromkeys(cluster_ids))
        clusters = MongoRepository.fetch_many_cluster_dict(id__in=cluster_ids)

        pipeline = Builder(root_id=self.root_id, data=self.payload)
        cluster_pipes = []
        bk_host_list = []
        for row in self.payload["infos"]:
            cluster_sb, row_hosts = self.build_row(row, clusters, actuator_workdir, dest_dir)
            cluster_pipes.append(cluster_sb.build_sub_process(_("MG-DataMigrate-{}").format(row["target_cluster_id"])))
            bk_host_list.extend(row_hosts)

        pipeline.add_act(
            **SendMedia.act(
                act_name=_("MG-SendMedia"),
                file_list=file_list,
                bk_host_list=bk_host_list,
                file_target_path=actuator_workdir,
            )
        )
        pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)
        pipeline.run_pipeline()

    def build_row(self, row: Dict, clusters: Dict, actuator_workdir: str, dest_dir: str):
        try:
            src_cluster = clusters[row["source_cluster_id"]]
            dst_cluster = clusters[row["target_cluster_id"]]
        except KeyError as err:
            raise Exception("cluster not found: {}".format(err))
        self.check_cluster_valid(src_cluster, self.payload)
        self.check_cluster_valid(dst_cluster, self.payload)
        self.ensure_same_topology(src_cluster, dst_cluster)
        ns_filter = self.user_data_ns_filter(row.get("ns_filter"))
        source_is_sharded = src_cluster.is_sharded_cluster()
        restore_via_mongos = dst_cluster.is_sharded_cluster()
        mongos_node = dst_cluster.get_connect_node() if restore_via_mongos else None
        # 多个源 shard 会把同一张分片表的不同数据先后导入，后面的包要追加到已有集合。
        # RS→分片：目标上可能已有用户预建的空分片表，restore 需跳过 exist 检查。
        skip_exist_check = source_is_sharded or restore_via_mongos
        migrate_sources = self.migrate_sources(row["source_mode"], src_cluster, dst_cluster, mongos_node)

        backup_files = {}
        config_backup = None
        if row["source_mode"] == SOURCE_BACKUP_TICKET:
            set_names = [src_rs.set_name for src_rs, _dst_node in migrate_sources]
            # 仅分片→分片需要 configsvr 备份来解析 shardCollection 规格。
            if source_is_sharded and restore_via_mongos:
                set_names.append(src_cluster.get_config().set_name)
            backup_files = self.load_ticket_backup_files(
                row["source_cluster_id"],
                row["backup_ticket_id"],
                set_names,
            )
            if source_is_sharded and restore_via_mongos:
                config_backup = backup_files.pop(src_cluster.get_config().set_name)

        cluster_sb = SubBuilder(root_id=self.root_id, data=self.payload)
        bk_host_list = []
        self._add_host(bk_host_list, dst_cluster.get_connect_node())
        if restore_via_mongos and row["source_mode"] == SOURCE_CLUSTER:
            self._add_host(bk_host_list, src_cluster.get_connect_node())
        # 副本集→分片：允许预建空分片表，仍要求每个用户集合无文档。
        # shardCollection 检查默认关闭，单据 require_target_sharded=true 时才加。
        if restore_via_mongos and not source_is_sharded:
            self._add_no_docs_check_act(cluster_sb, dst_cluster)
            if row.get("require_target_sharded"):
                self._add_target_sharded_check_act(cluster_sb, dst_cluster)
        else:
            InstanceOpSubTask.process_node(
                root_id=self.root_id,
                ticket_data=self.payload,
                sub_ticket_data=row,
                sub_pipeline=cluster_sb,
                exec_node=dst_cluster.get_connect_node(),
                file_path=actuator_workdir,
                act_name=_("MG-CheckEmptyData"),
                op="check_empty_data",
            )

        dst_exec_nodes = []
        shard_pipes = []
        for src_rs, dst_node in migrate_sources:
            src_node = self.pick_exec_node(src_rs)
            if row["source_mode"] == SOURCE_CLUSTER and src_node.bk_cloud_id != dst_node.bk_cloud_id:
                raise Exception(
                    "bk_cloud_id differs, set {} {} vs {}".format(
                        src_rs.set_name, src_node.bk_cloud_id, dst_node.bk_cloud_id
                    )
                )
            self._add_host(bk_host_list, dst_node)
            dst_exec_nodes.append(dst_node)
            if row["source_mode"] == SOURCE_CLUSTER:
                self._add_host(bk_host_list, src_node)

            shard_sb = SubBuilder(root_id=self.root_id, data=self.payload)
            shard_payload = {
                "ns_filter": ns_filter,
                "task_ids": [],
            }
            restore_exec = dst_node
            restore_dest = mongos_node if restore_via_mongos else dst_node
            restore_type = "mongos" if restore_via_mongos else "mongod"
            if row["source_mode"] == SOURCE_BACKUP_TICKET:
                shard_payload["task_ids"] = [backup_files[src_rs.set_name]]
                DownloadSubTask.process_shard(
                    root_id=self.root_id,
                    ticket_data=self.payload,
                    sub_ticket_data=shard_payload,
                    shard=src_rs,
                    file_path=actuator_workdir,
                    dest_dir=dest_dir,
                    dest_node=dst_node,
                    sub_pipeline=shard_sb,
                    src_set_name=src_rs.set_name,
                )
                self._add_restore_act(
                    shard_sb,
                    actuator_workdir,
                    dest_dir,
                    restore_exec,
                    shard_payload,
                    dest_node=restore_dest,
                    dest_type=restore_type,
                    skip_exist_check=skip_exist_check,
                )
            else:
                archive_base = self.archive_base_name(self.root_id, src_rs.set_name)
                tar_name = "{}.tar.gz".format(archive_base)
                src_tar = "{}/{}".format(BILL_DUMP_DIR, tar_name)
                dst_tar = "{}/{}".format(dest_dir, tar_name)
                self._add_dump_act(shard_sb, actuator_workdir, src_cluster, src_rs, src_node, archive_base, ns_filter)
                shard_sb.add_act(
                    act_name=_("MG-TransDump-{}").format(src_rs.set_name),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict_p2p(
                        bk_cloud_id=dst_node.bk_cloud_id,
                        exec_ip=dst_node.ip,
                        source_ip_list=[src_node.ip],
                        file_list=[src_tar],
                        file_target_path=dest_dir,
                    ),
                )
                self._add_restore_act(
                    shard_sb,
                    actuator_workdir,
                    dest_dir,
                    restore_exec,
                    shard_payload,
                    local_file=dst_tar,
                    dest_node=restore_dest,
                    dest_type=restore_type,
                    skip_exist_check=skip_exist_check,
                )
                self._add_cleanup_act(shard_sb, src_node, dst_node, src_tar, dst_tar)

            shard_pipes.append(shard_sb.build_sub_process(_("MG-MigrateShard-{}").format(src_rs.set_name)))

        prepare_hosts = [{"ip": node.ip, "bk_cloud_id": node.bk_cloud_id} for node in dst_exec_nodes]
        if restore_via_mongos:
            prepare_hosts.append({"ip": mongos_node.ip, "bk_cloud_id": mongos_node.bk_cloud_id})
        # 源 mongos 上要导出分片表清单或整体 dump。
        if (restore_via_mongos or source_is_sharded) and row["source_mode"] == SOURCE_CLUSTER:
            src_mongos = src_cluster.get_connect_node()
            item = {"ip": src_mongos.ip, "bk_cloud_id": src_mongos.bk_cloud_id}
            if item not in prepare_hosts:
                prepare_hosts.append(item)
        cluster_sb.add_act(
            **ExecShellScript.act(
                act_name=_("MG-Prepare"),
                file_list=[],
                bk_host_list=prepare_hosts,
                exec_account="root",
                script_content=prepare_recover_dir_script(dest_dir),
            )
        )
        # 分片→分片才自动 shardCollection；副本集→分片由用户预先完成。
        if source_is_sharded and restore_via_mongos:
            self._add_shard_collection_pipeline(
                cluster_sb,
                row,
                src_cluster,
                actuator_workdir,
                dest_dir,
                mongos_node,
                config_backup,
            )
        # 同一张用户表可能分布在多个源 shard 上，并行导入会互相覆盖或冲突，改成串行。
        if source_is_sharded:
            for shard_pipe in shard_pipes:
                cluster_sb.add_sub_pipeline(sub_flow=shard_pipe)
        else:
            cluster_sb.add_parallel_sub_pipeline(sub_flow_list=shard_pipes)
        return cluster_sb, bk_host_list

    def migrate_sources(
        self,
        source_mode: str,
        src_cluster: MongoDBCluster,
        dst_cluster: MongoDBCluster,
        mongos_node: Optional[MongoNode],
    ) -> List[Tuple[ReplicaSet, MongoNode]]:
        """返回 (源集合, 目标落盘/导入执行节点) 列表。"""
        if src_cluster.is_sharded_cluster():
            file_node = mongos_node or self.pick_exec_node(dst_cluster.get_shards()[0])
            if source_mode == SOURCE_CLUSTER:
                # 经源 mongos 整体导出：直连 shard 会带出孤儿文档，chunk 迁移时同一 _id 还会出现在两个 shard。
                return [(self.source_mongos_set(src_cluster), file_node)]
            return [(src_rs, file_node) for src_rs in self.iter_source_shards(src_cluster)]
        if mongos_node:
            # 副本集→分片：经 mongos 导入；shardCollection 由用户预先完成。
            return [(src_cluster.get_shards()[0], mongos_node)]
        return [
            (src_rs, self.pick_exec_node(dst_rs))
            for src_rs, dst_rs in self.iter_migrate_pairs(src_cluster, dst_cluster)
        ]

    def _add_shard_collection_pipeline(
        self,
        cluster_sb: SubBuilder,
        row: Dict,
        src_cluster: MongoDBCluster,
        actuator_workdir: str,
        dest_dir: str,
        mongos_node: MongoNode,
        config_backup: Optional[Dict],
    ):
        """导入前在目标 mongos 上 shardCollection。configsvr 备份只用来读 config.collections，不恢复。"""
        spec_path = "{}/{}".format(dest_dir, self.archive_base_name(self.root_id, "sharded-collections") + ".json")
        shard_sb = SubBuilder(root_id=self.root_id, data=self.payload)
        if row["source_mode"] == SOURCE_BACKUP_TICKET:
            conf = src_cluster.get_config()
            DownloadSubTask.process_shard(
                root_id=self.root_id,
                ticket_data=self.payload,
                sub_ticket_data={"task_ids": [config_backup], "ns_filter": None},
                shard=conf,
                file_path=actuator_workdir,
                dest_dir=dest_dir,
                dest_node=mongos_node,
                sub_pipeline=shard_sb,
                src_set_name=conf.set_name,
            )
            backup_path = "{}/{}".format(dest_dir, config_backup["file_name"])
            self._add_shard_coll_act(
                shard_sb,
                actuator_workdir,
                mongos_node,
                "apply",
                spec_path,
                backup_file=backup_path,
                ns_filter=row.get("ns_filter"),
            )
        else:
            src_mongos = src_cluster.get_connect_node()
            self._add_shard_coll_act(
                shard_sb, actuator_workdir, src_mongos, "export", spec_path, ns_filter=row.get("ns_filter")
            )
            shard_sb.add_act(
                act_name=_("MG-TransShardCollections"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict_p2p(
                    bk_cloud_id=mongos_node.bk_cloud_id,
                    exec_ip=mongos_node.ip,
                    source_ip_list=[src_mongos.ip],
                    file_list=[spec_path],
                    file_target_path=dest_dir,
                ),
            )
            self._add_shard_coll_act(
                shard_sb, actuator_workdir, mongos_node, "apply", spec_path, ns_filter=row.get("ns_filter")
            )
        cluster_sb.add_sub_pipeline(sub_flow=shard_sb.build_sub_process(_("MG-ShardCollections")))

    def _add_shard_coll_act(
        self,
        shard_sb: SubBuilder,
        actuator_workdir: str,
        node: MongoNode,
        op: str,
        collections_file: str,
        backup_file: str = "",
        ns_filter: Optional[Dict] = None,
    ):
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        sudo_account = MongoUtil().get_mongodb_os_conf()["user"]
        payload = {
            "ip": node.ip,
            "port": int(node.port),
            "adminUsername": dba_user,
            "adminPassword": dba_pwd,
            "op": op,
            "collectionsFile": collections_file,
            "nsFilter": self.user_data_ns_filter(ns_filter),
        }
        if backup_file:
            payload["backupFile"] = backup_file
        shard_sb.add_act(
            act_name=_("MG-ShardCollections-{}-{}:{}".format(op, node.ip, node.port)),
            act_component_code=ExecJobComponent2.code,
            kwargs={
                "set_trans_data_dataclass": CommonContext.__name__,
                "get_trans_data_ip_var": None,
                "bk_cloud_id": node.bk_cloud_id,
                "exec_ip": node.ip,
                "db_act_template": {
                    "action": MongoDBActuatorActionEnum.MongoShardCollections,
                    "file_path": actuator_workdir,
                    "exec_account": "root",
                    "sudo_account": sudo_account,
                    "payload": payload,
                },
            },
        )

    def _add_dump_act(
        self,
        shard_sb: SubBuilder,
        actuator_workdir: str,
        src_cluster: MongoDBCluster,
        src_rs: ReplicaSet,
        src_node: MongoNode,
        archive_base: str,
        ns_filter,
    ):
        dba_user, dba_pwd = MongoUtil().get_dba_user_password(src_node.ip, src_node.port, src_node.bk_cloud_id)
        is_partial = MongoDBNsFilter.is_partial(ns_filter)
        bk_dbm_instance = MongoNodeWithLabel.from_node(src_node, src_rs, src_cluster)
        sudo_account = MongoUtil().get_mongodb_os_conf()["user"]
        shard_sb.add_act(
            act_name=_("MG-Dump-{}-{}:{}".format(src_rs.set_name, src_node.ip, src_node.port)),
            act_component_code=ExecJobComponent2.code,
            kwargs={
                "set_trans_data_dataclass": CommonContext.__name__,
                "get_trans_data_ip_var": None,
                "bk_cloud_id": src_node.bk_cloud_id,
                "exec_ip": src_node.ip,
                "db_act_template": {
                    "action": MongoDBActuatorActionEnum.Backup,
                    "file_path": actuator_workdir,
                    "exec_account": "root",
                    "sudo_account": sudo_account,
                    "payload": {
                        "bk_dbm_instance": bk_dbm_instance.__json__(),
                        "ip": src_node.ip,
                        "port": int(src_node.port),
                        "adminUsername": dba_user,
                        "adminPassword": dba_pwd,
                        "skipBackupSysDb": True,
                        "backupType": "logical",
                        "skipUpload": True,
                        "archiveBaseName": archive_base,
                        "args": {
                            "backupNode": "",
                            "isPartial": is_partial,
                            "oplog": False,
                            "nsFilter": ns_filter,
                        },
                    },
                },
            },
        )

    def _add_restore_act(
        self,
        shard_sb: SubBuilder,
        actuator_workdir: str,
        dest_dir: str,
        exec_node: MongoNode,
        shard_payload: Dict,
        local_file: str = None,
        dest_node: MongoNode = None,
        dest_type: str = "mongod",
        skip_exist_check: bool = False,
    ):
        dest_node = dest_node or exec_node
        kwargs = RestoreSubTask.make_kwargs(
            shard_payload,
            actuator_workdir,
            dest_dir,
            exec_node,
            dest_node,
            dest_type,
            local_file=local_file,
            skip_exist_check=skip_exist_check,
        )
        shard_sb.add_act(
            act_name=_("MG-Restore-{}:{}".format(dest_node.ip, dest_node.port)),
            act_component_code=ExecJobComponent2.code,
            kwargs=kwargs,
        )

    def _add_cleanup_act(
        self, shard_sb: SubBuilder, src_node: MongoNode, dst_node: MongoNode, src_tar: str, dst_tar: str
    ):
        hosts = [{"ip": src_node.ip, "bk_cloud_id": src_node.bk_cloud_id}]
        if dst_node.ip != src_node.ip:
            hosts.append({"ip": dst_node.ip, "bk_cloud_id": dst_node.bk_cloud_id})
        script = "rm -f {} {}\n".format(src_tar, dst_tar)
        shard_sb.add_act(
            **ExecShellScript.act(
                act_name=_("MG-CleanupDump"),
                file_list=[],
                bk_host_list=hosts,
                exec_account="root",
                script_content=script,
            )
        )

    def _add_no_docs_check_act(self, cluster_sb: SubBuilder, cluster: MongoDBCluster):
        node = cluster.get_connect_node()
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        cluster_sb.add_act(
            **ExecShellScript.act(
                act_name=_("MG-CheckNoDocs"),
                file_list=[],
                bk_host_list=[{"ip": node.ip, "bk_cloud_id": node.bk_cloud_id}],
                exec_account="root",
                script_content=check_empty_target_script(
                    node.ip,
                    node.port,
                    dba_user,
                    dba_pwd,
                    connect_uri=self._admin_connect_uri(cluster),
                ),
            )
        )

    def _add_target_sharded_check_act(self, cluster_sb: SubBuilder, cluster: MongoDBCluster):
        node = cluster.get_connect_node()
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        cluster_sb.add_act(
            **ExecShellScript.act(
                act_name=_("MG-CheckTargetSharded"),
                file_list=[],
                bk_host_list=[{"ip": node.ip, "bk_cloud_id": node.bk_cloud_id}],
                exec_account="root",
                script_content=assert_target_user_collections_sharded_script(
                    node.ip,
                    node.port,
                    dba_user,
                    dba_pwd,
                    connect_uri=self._admin_connect_uri(cluster),
                ),
            )
        )

    @staticmethod
    def _admin_connect_uri(cluster: MongoDBCluster) -> str:
        if cluster.is_sharded_cluster():
            return ""
        shard = cluster.get_shards()[0]
        addrs = [node.addr() for node in shard.members]
        return replica_set_connect_uri(addrs, shard.set_name or cluster.name)

    @staticmethod
    def _add_host(hosts: List[Dict], node: MongoNode):
        item = {"ip": node.ip, "bk_cloud_id": node.bk_cloud_id}
        if item not in hosts:
            hosts.append(item)

    @staticmethod
    def pick_exec_node(rs: ReplicaSet) -> MongoNode:
        nodes = rs.get_not_backup_nodes()
        if not nodes:
            raise Exception("no exec node. rs:{}".format(rs.set_name))
        return nodes[0]

    @staticmethod
    def ensure_same_topology(src_cluster: MongoDBCluster, dst_cluster: MongoDBCluster):
        """
        支持拓扑：
          RS → RS、分片 → 分片、分片 → RS、RS → 分片。
        RS → 分片时不做自动 shardCollection，默认也不检查目标是否已分片。
        """
        src_sharded = src_cluster.is_sharded_cluster()
        dst_sharded = dst_cluster.is_sharded_cluster()
        # 非 RS/分片 的其它类型组合仍拒绝。
        if not src_sharded and not dst_sharded and src_cluster.cluster_type != dst_cluster.cluster_type:
            raise Exception(
                "cluster_type differs: {} vs {}".format(src_cluster.cluster_type, dst_cluster.cluster_type)
            )
        try:
            target_is_lower = compare_mongodb_versions(dst_cluster.major_version, src_cluster.major_version) < 0
        except ValueError as err:
            raise Exception(
                "invalid major_version {} vs {}: {}".format(src_cluster.major_version, dst_cluster.major_version, err)
            )
        if target_is_lower:
            raise Exception(
                "target major_version {} is lower than source {}".format(
                    dst_cluster.major_version, src_cluster.major_version
                )
            )

    @staticmethod
    def user_data_ns_filter(ns_filter: Optional[Dict]) -> Dict:
        """只迁用户库。admin/config/local 留在目标集群自己的元数据里。"""
        if not ns_filter:
            return {
                "db_patterns": ["*"],
                "table_patterns": ["*"],
                "ignore_dbs": list(SYSTEM_IGNORE_DBS),
                "ignore_tables": [],
            }
        merged = dict(ns_filter)
        ignore = [db for db in (merged.get("ignore_dbs") or []) if db]
        for name in SYSTEM_IGNORE_DBS:
            if name not in ignore:
                ignore.append(name)
        merged["ignore_dbs"] = ignore
        if not merged.get("db_patterns"):
            merged["db_patterns"] = ["*"]
        if not merged.get("table_patterns"):
            merged["table_patterns"] = ["*"]
        if merged.get("ignore_tables") is None:
            merged["ignore_tables"] = []
        return merged

    @staticmethod
    def iter_source_shards(src_cluster: MongoDBCluster) -> List[ReplicaSet]:
        """遍历源 shard，不含 configsvr。目标可以是分片数不同的集群，也可以是副本集。"""
        if src_cluster.get_config() is None:
            raise Exception("sharded cluster missing configsvr")
        return src_cluster.get_shards(with_config=False, sort_by_set_name=True)

    @staticmethod
    def source_mongos_set(src_cluster: MongoDBCluster) -> ReplicaSet:
        """把源 mongos 包成单成员集合，复用按集合 dump/传输/导入的步骤。"""
        mongos = src_cluster.get_connect_node()
        return ReplicaSet(MongoDBClusterRole.Mongos.value, set_name="mongos", members=[mongos])

    @staticmethod
    def iter_migrate_pairs(
        src_cluster: MongoDBCluster, dst_cluster: MongoDBCluster
    ) -> List[Tuple[ReplicaSet, ReplicaSet]]:
        """副本集一对一。分片集群不在这里配对。"""
        src_shards = src_cluster.get_shards()
        dst_shards = dst_cluster.get_shards()
        if len(src_shards) != len(dst_shards):
            raise Exception("replicaset count differs: {} vs {}".format(len(src_shards), len(dst_shards)))
        return list(zip(src_shards, dst_shards))

    @staticmethod
    def archive_base_name(root_id: str, set_name: str) -> str:
        raw = "migrate-{}-{}".format(root_id, set_name)
        return re.sub(r"[^A-Za-z0-9._-]", "_", raw)[:160]

    @classmethod
    def load_ticket_backup_files(cls, source_cluster_id: int, backup_ticket_id: int, set_names: List[str]) -> Dict:
        end_time = timezone.now()
        start_time = end_time - timedelta(days=BILL_BACKUP_LOOKBACK_DAYS)
        logs = MongoDBRestoreHandler._get_log_from_bklog(
            collector="mongo_backup_result",
            start_time=start_time,
            end_time=end_time,
            query_string="cluster_id: {} AND related_bill_id: {}".format(source_cluster_id, backup_ticket_id),
        )
        if not logs:
            raise Exception(
                "no backup log for ticket {} cluster {} in last {} days".format(
                    backup_ticket_id, source_cluster_id, BILL_BACKUP_LOOKBACK_DAYS
                )
            )
        return cls.pick_backup_files(logs, set_names)

    @staticmethod
    def pick_backup_files(logs: List[Dict], set_names: List[str]) -> Dict[str, Dict]:
        grouped = {name: [] for name in set_names}
        for log in logs:
            set_name = log.get("set_name")
            if set_name in grouped:
                grouped[set_name].append(log)
        missing = [name for name, items in grouped.items() if not items]
        if missing:
            raise Exception("backup files missing for set_name: {}".format(",".join(missing)))

        picked = {}
        for set_name, items in grouped.items():
            usable = [item for item in items if str(item.get("is_empty_backup") or "0") not in ("1", "true", "True")]
            if not usable:
                raise Exception("all backups are empty for set_name: {}".format(set_name))
            usable.sort(key=lambda item: item.get("end_time") or item.get("start_time") or "")
            chosen = usable[-1]
            task_id = chosen.get("bs_taskid") or chosen.get("task_id")
            file_name = chosen.get("file_name")
            if not task_id or not file_name:
                raise Exception("backup log missing bs_taskid/file_name for {}".format(set_name))
            picked[set_name] = {"task_id": str(task_id), "file_name": file_name}
        return picked


def asdict_p2p(bk_cloud_id: int, exec_ip: str, source_ip_list: List[str], file_list: List[str], file_target_path: str):
    return asdict(
        P2PFileKwargs(
            bk_cloud_id=bk_cloud_id,
            exec_ip=exec_ip,
            source_ip_list=source_ip_list,
            file_list=file_list,
            file_target_path=file_target_path,
        )
    )
