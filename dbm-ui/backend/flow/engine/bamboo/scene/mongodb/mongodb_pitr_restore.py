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
import logging.config
from typing import Dict, Optional

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.flow.consts import DirEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.download_subtask import DownloadSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.exec_shell_script import ExecShellScript
from backend.flow.engine.bamboo.scene.mongodb.sub_task.fetch_backup_record_subtask import FetchBackupRecordSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.hello_sub import HelloSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.pitr_restore_sub import PitrRestoreSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoNode, MongoRepository
from backend.flow.utils.mongodb.mongodb_script_template import prepare_recover_dir_script
from backend.flow.utils.mongodb.mongodb_util import MongoUtil

logger = logging.getLogger("flow")


class BsTask:
    """备份系统Task，前端传来的数据"""

    class Serializer(serializers.Serializer):
        task_id = serializers.CharField()
        file_name = serializers.CharField()

    task_id: str = ""
    file_name: str = ""


class MongoPitrRestoreFlow(MongoBaseFlow):
    class Serializer(serializers.Serializer):
        class DataRow(serializers.Serializer):
            task_ids = BsTask.Serializer(many=True, required=False)
            src_cluster_id = serializers.IntegerField()
            dst_cluster_id = serializers.IntegerField()
            dst_cluster_type = serializers.CharField()
            dst_time = serializers.CharField()
            apply_oplog = serializers.BooleanField()

        uid = serializers.CharField()
        created_by = serializers.CharField()
        bk_biz_id = serializers.IntegerField()
        ticket_type = serializers.CharField()
        infos = DataRow(many=True)

    """MongoPitrRestoreFlow
    分析 payload，检查输入，生成Flow """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        super().__init__(root_id, data)
        self.check_payload()

    def check_payload(self):
        print("payload", self.payload)
        s = self.Serializer(data=self.payload)
        if not s.is_valid():
            raise Exception("payload is invalid {}".format(s.errors))

    def start(self):
        """
        MongoPitrRestoreFlow 流程
        """
        logger.debug("MongoPitrRestoreFlow start, payload", self.payload)
        # actuator_workdir 提前创建好的，在部署的时候就创建好了.
        actuator_workdir = MongoUtil().get_mongodb_os_conf()["file_path"]
        file_list = GetFileList(db_type=DBType.MongoDB).get_db_actuator_package()

        # 解析输入 确定每个输入的域名实例都存在.
        # 1. 部署临时集群（目前省略）
        # 2. 获得每个目标集群的信息
        # 3-1. 预处理. 准备数据文件目录 mkdir -p $MONGO_RECOVER_DIR
        # 3-2. 预处理. 获得每个目标集群的备份文件列表，下载备份文件
        # 4. 执行回档任务

        # 所有涉及的cluster
        cluster_id_list = [row["dst_cluster_id"] for row in self.payload["infos"]]
        self.check_cluster_id_list(cluster_id_list)
        clusters = MongoRepository.fetch_many_cluster_dict(id__in=cluster_id_list)
        dest_dir = str(DirEnum.MONGO_RECOVER_DIR.value)

        # dest_dir 必须是 '/data/dbbak' 开头
        if not dest_dir.startswith("/data/dbbak"):
            raise Exception("dest_dir must start with /data/dbbak")

        # 确定exec_node
        exec_node_list = []
        all_iplist = []
        cloud_id = []
        for row in self.payload["infos"]:
            try:
                # 检查目标cluster是否存在
                dst_cluster_id = row["dst_cluster_id"]
                cluster = clusters[dst_cluster_id]
                self.check_cluster_valid(cluster, self.payload)
            except Exception as e:
                logger.exception("check_cluster_valid fail")
                raise Exception("check_cluster_valid fail cluster_id:{} {}".format(row["cluster_id"], e))
            exec_node_list.extend(self.set_exec_node(row, cluster))
            all_iplist.extend(cluster.get_iplist())
            cloud_id.append(cluster.bk_cloud_id)

        cloud_id = list(set(cloud_id))
        if len(cloud_id) != 1:
            raise Exception("There are different cloud id")
        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.payload)
        cluster_pipes = []
        for row in self.payload["infos"]:
            cluster = clusters[row["dst_cluster_id"]]
            logger.debug("sub_pipline start row", row)
            logger.debug("sub_pipline start cluster", cluster)
            cluster_sb = self.process_cluster(
                row=row, cluster=cluster, actuator_workdir=actuator_workdir, dest_dir=dest_dir
            )
            cluster_pipes.append(cluster_sb.build_sub_process(_("cluster {}").format(cluster.name)))

        # 1. 统一预处理
        # 2. 统一下发文件
        # 3. 执行cluster_sub
        bk_host_list = list(map(lambda x: {"ip": x, "bk_cloud_id": cloud_id[0]}, set(all_iplist)))
        # 开始组装流程
        # Step1 执行做准备脚本  执行mkdir -p /data/dbbak/recover_mg
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MongoDB-预处理 {}".format(len(bk_host_list))),
                file_list=file_list,
                bk_host_list=bk_host_list,
                exec_account="root",
                script_content=prepare_recover_dir_script(dest_dir),
            )
        )

        # Step2 介质下发
        pipeline.add_act(
            **SendMedia.act(
                act_name=_("MongoDB-介质下发 {}".format(len(bk_host_list))),
                file_list=file_list,
                bk_host_list=bk_host_list,
                file_target_path=actuator_workdir,
            )
        )

        # 按Cluster执行流程
        pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)

        pipeline.run_pipeline()

    @staticmethod
    def set_exec_node(row: Dict, cluster: MongoDBCluster) -> list[MongoNode]:
        """
        确定每个shard的exec_node
        """
        exec_node_list = []
        row["__exec_node"] = {}
        for shard in cluster.get_shards():
            exec_node = shard.get_not_backup_nodes()[0]
            row["__exec_node"][shard.set_name] = exec_node
            exec_node_list.append(exec_node)
        if cluster.is_sharded_cluster():
            shard = cluster.get_config()
            exec_node = shard.get_not_backup_nodes()[0]
            row["__exec_node"][shard.set_name] = exec_node
            exec_node_list.append(exec_node)
        return exec_node_list

    def process_cluster(self, row: Dict, cluster: MongoDBCluster, actuator_workdir: str, dest_dir: str) -> SubBuilder:
        """
        cluster pitr_restore_flow
        """
        cluster_sb = SubBuilder(root_id=self.root_id, data=self.payload)
        shard_pipes = []

        if cluster.is_sharded_cluster():
            self.check_empty_cluster(
                row=row, cluster=cluster, actuator_workdir=actuator_workdir, dest_dir=dest_dir, cluster_sb=cluster_sb
            )

            self.stop_mongos(
                row=row, cluster=cluster, actuator_workdir=actuator_workdir, dest_dir=dest_dir, cluster_sb=cluster_sb
            )

        # 准备主节点:
        #  让第1个节点成为Primary，remove掉其它成员，start as standalone mode
        # self.remove_none_exec_node
        # restart exec_node as standalone node

        self.stop_not_exec_node(
            row=row, cluster=cluster, actuator_workdir=actuator_workdir, dest_dir=dest_dir, cluster_sb=cluster_sb
        )
        self.restart_as_standalone(
            row=row, cluster=cluster, actuator_workdir=actuator_workdir, dest_dir=dest_dir, cluster_sb=cluster_sb
        )

        # 为每个Shard执行回档，包括configsvr
        restore_sb = SubBuilder(root_id=self.root_id, data=self.payload)
        for shard in cluster.get_shards(with_config=True):
            shard_sb = SubBuilder(root_id=self.root_id, data=self.payload)
            self.process_shard(
                row=row,
                cluster=cluster,
                shard=shard,
                actuator_workdir=actuator_workdir,
                dest_dir=dest_dir,
                shard_sub=shard_sb,
            )
            shard_pipes.append(shard_sb.build_sub_process(_("{} {}").format(shard.set_type, shard.set_name)))

        restore_sb.add_parallel_sub_pipeline(sub_flow_list=shard_pipes)
        cluster_sb.add_sub_pipeline(sub_flow=restore_sb.build_sub_process("restore_by_shard"))
        # restore_sb end

        if cluster.is_sharded_cluster():
            # if sharded_cluster
            # 处理各个分片和configsvr的关系.
            # start as clusterRole: shardsvr
            self.rebuild_cluster(
                row=row, cluster=cluster, actuator_workdir=actuator_workdir, dest_dir=dest_dir, cluster_sb=cluster_sb
            )

        # todo restart as auth mode && and re add secondary

        return cluster_sb

    def check_empty_cluster(
        self, row: Dict, cluster: MongoDBCluster, actuator_workdir: str, dest_dir: str, cluster_sb: SubBuilder
    ):

        exec_node = cluster.get_mongos()[0]
        HelloSubTask.process_node(
            root_id=self.root_id,
            ticket_data=self.payload,
            sub_ticket_data=row,
            sub_pipeline=cluster_sb,
            exec_node=exec_node,
            file_path=actuator_workdir,
            act_name=_("空闲检查"),
        )
        return

    def process_shard(self, row: Dict, cluster, shard, actuator_workdir: str, dest_dir: str, shard_sub: SubBuilder):
        """
        pitr_restore_flow one shard
        """
        # FetchBackupRecordSubTask 根据 sub_ticket_data中的src_cluster_id, dst_time 获得备份文件列表.
        FetchBackupRecordSubTask.process_shard(
            root_id=self.root_id,
            ticket_data=self.payload,
            sub_ticket_data=row,
            cluster=cluster,
            shard=shard,
        )
        exec_node = row["__exec_node"][shard.set_name]

        logger.debug("sub_ticket_data {}".format(row))
        # process_cluster 会根据src_cluster_id, dst_time 获得备份文件列表.
        DownloadSubTask.process_shard(
            root_id=self.root_id,
            ticket_data=self.payload,
            sub_ticket_data=row,
            shard=shard,
            file_path=actuator_workdir,
            dest_dir=dest_dir,
            dest_node=exec_node,
            sub_pipeline=shard_sub,
        )

        PitrRestoreSubTask.process_shard(
            root_id=self.root_id,
            ticket_data=self.payload,
            sub_ticket_data=row,
            shard=shard,
            file_path=actuator_workdir,
            dest_dir=dest_dir,
            exec_node=exec_node,
            sub_pipeline=shard_sub,
        )

        return

    def stop_mongos(
        self, row: Dict, cluster: MongoDBCluster, actuator_workdir: str, dest_dir: str, cluster_sb: SubBuilder
    ):

        acts_list = []
        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        for mongos in cluster.get_mongos():
            acts_list.append(
                {
                    "act_name": _("stop_mongos {}:{}".format(mongos.ip, mongos.port)),
                    "act_component_code": ExecJobComponent2.code,
                    "kwargs": HelloSubTask.make_kwargs(exec_node=mongos, file_path=actuator_workdir),
                }
            )

        # 可能会存在mongos列表为空的情况吗？
        if len(acts_list) == 0:
            return

        sb.add_parallel_acts(acts_list=acts_list)
        cluster_sb.add_sub_pipeline(sub_flow=sb.build_sub_process("stop_mongos"))

    def stop_not_exec_node(
        self, row: Dict, cluster: MongoDBCluster, actuator_workdir: str, dest_dir: str, cluster_sb: SubBuilder
    ):

        acts_list = []
        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        for mongos in cluster.get_mongos():
            acts_list.append(
                {
                    "act_name": _("stop {}:{}".format(mongos.ip, mongos.port)),
                    "act_component_code": ExecJobComponent2.code,
                    "kwargs": HelloSubTask.make_kwargs(exec_node=mongos, file_path=actuator_workdir),
                }
            )

        # 可能会存在mongos列表为空的情况吗？
        if len(acts_list) == 0:
            return

        sb.add_parallel_acts(acts_list=acts_list)
        cluster_sb.add_sub_pipeline(sub_flow=sb.build_sub_process("stop_not_exec_node"))

    def restart_as_standalone(
        self, row: Dict, cluster: MongoDBCluster, actuator_workdir: str, dest_dir: str, cluster_sb: SubBuilder
    ):

        acts_list = []
        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        for mongos in cluster.get_mongos():
            acts_list.append(
                {
                    "act_name": _("restart {}:{}".format(mongos.ip, mongos.port)),
                    "act_component_code": ExecJobComponent2.code,
                    "kwargs": HelloSubTask.make_kwargs(exec_node=mongos, file_path=actuator_workdir),
                }
            )

        # 可能会存在mongos列表为空的情况吗？
        if len(acts_list) == 0:
            return

        sb.add_parallel_acts(acts_list=acts_list)
        cluster_sb.add_sub_pipeline(sub_flow=sb.build_sub_process("restart_as_standalone"))

    def rebuild_cluster(
        self, row: Dict, cluster: MongoDBCluster, actuator_workdir: str, dest_dir: str, cluster_sb: SubBuilder
    ):

        acts_list = []
        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        for mongos in cluster.get_mongos():
            acts_list.append(
                {
                    "act_name": _("rebuild {}:{}".format(mongos.ip, mongos.port)),
                    "act_component_code": ExecJobComponent2.code,
                    "kwargs": HelloSubTask.make_kwargs(exec_node=mongos, file_path=actuator_workdir),
                }
            )

        # 可能会存在mongos列表为空的情况吗？
        if len(acts_list) == 0:
            return

        sb.add_parallel_acts(acts_list=acts_list)
        cluster_sb.add_sub_pipeline(sub_flow=sb.build_sub_process("rebuild_cluster"))
