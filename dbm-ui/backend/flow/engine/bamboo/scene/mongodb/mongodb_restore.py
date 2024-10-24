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
from backend.flow.engine.bamboo.scene.mongodb.sub_task.restore_sub import RestoreSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.utils.mongodb.mongodb_repo import MongoDBNsFilter, MongoRepository
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


class MongoRestoreFlow(MongoBaseFlow):
    class Serializer(serializers.Serializer):
        class DataRow(serializers.Serializer):
            task_ids = BsTask.Serializer(many=True)
            src_cluster_id = serializers.IntegerField()
            dst_cluster_id = serializers.IntegerField()
            dst_cluster_type = serializers.CharField()
            dst_time = serializers.CharField()
            apply_oplog = serializers.BooleanField()
            ns_filter = MongoDBNsFilter.Serializer(allow_null=True)

        uid = serializers.CharField()
        created_by = serializers.CharField()
        bk_biz_id = serializers.IntegerField()
        ticket_type = serializers.CharField()
        infos = DataRow(many=True)

    """MongoDBRestoreFlow
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
        MongoDBRestoreFlow 流程
        """
        logger.debug("MongoDBRestoreFlow start, payload", self.payload)
        # actuator_workdir 提前创建好的，在部署的时候就创建好了.
        actuator_workdir = MongoUtil().get_mongodb_os_conf()["file_path"]
        file_list = GetFileList(db_type=DBType.MongoDB).get_db_actuator_package()

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.payload)
        root_sub = []

        # 解析输入 确定每个输入的域名实例都存在.
        # 1. 部署临时集群（目前省略）
        # 2. 获得每个目标集群的信息
        # 3-1. 准备数据文件目录 mkdir -p $MONGO_RECOVER_DIR
        # 3-2. 获得每个目标集群的备份文件列表，下载备份文件 （todo: 如果存在的情况下跳过）
        # 4. 执行回档任务
        # # ### 获取机器磁盘备份目录信息 ##########################################################

        # 所有涉及的cluster
        cluster_id_list = [row["dst_cluster_id"] for row in self.payload["infos"]]
        self.check_cluster_id_list(cluster_id_list)
        clusters = MongoRepository.fetch_many_cluster_dict(id__in=cluster_id_list)
        dest_dir = DirEnum.MONGO_RECOVER_DIR.value

        # dest_dir 必须是 '/data/dbbak' 开头
        if not dest_dir.startswith("/data/dbbak"):
            raise Exception("dest_dir must start with /data/dbbak")

        # by Cluster
        for row in self.payload["infos"]:
            try:
                dst_cluster_id = row["dst_cluster_id"]
                cluster = clusters[dst_cluster_id]
                self.check_cluster_valid(cluster, self.payload)
            except Exception as e:
                logger.exception("check_cluster_valid fail")
                raise Exception("check_cluster_valid fail cluster_id:{} {}".format(row["cluster_id"], e))
            logger.debug("sub_pipline start row", row)
            logger.debug("sub_pipline start cluster", cluster)

            # bk_host {ip:"1.1.1.1", bk_cloud_id: "0"}
            step3_sub, step4_sub, bk_host_list = [], [], []
            sb = SubBuilder(root_id=self.root_id, data=row)

            # 保存一些初始内容，在不同的步骤中共享
            row["_tmp_data"] = {
                "cluster": cluster,
            }

            # if row["import_to"] == "mongos":

            # 分离备份文件. 确定回档机器-文件列表-回档目标
            rs = cluster.get_shards()[0]
            exec_node = rs.get_not_backup_nodes()[0]

            # 在备份系统中提单，将所需要的文件复制过去
            sub_pl = DownloadSubTask.process_shard(
                root_id=self.root_id,
                ticket_data=self.payload,
                sub_ticket_data=row,
                shard=rs,
                file_path=actuator_workdir,
                dest_dir=dest_dir,
                dest_node=exec_node,
            )
            step3_sub.append(sub_pl.build_sub_process(_("下载备份文件-{}").format(cluster.name)))

            sub_pl4, sub_bk_host_list4 = RestoreSubTask.process_cluster(
                root_id=self.root_id,
                ticket_data=self.payload,
                sub_ticket_data=row,
                cluster=cluster,
                file_path=actuator_workdir,
                dest_dir=dest_dir,
                exec_node=exec_node,
            )
            step4_sub.append(sub_pl4.build_sub_process(_("执行导入命令-{}").format(cluster.name)))

            # 开始组装流程 从Step1 开始
            # Step1 执行做准备脚本  执行mkdir -p /data/dbbak/recover_mg
            sb.add_act(
                **ExecShellScript.act(
                    act_name=_("MongoDB-预处理"),
                    file_list=file_list,
                    bk_host_list=bk_host_list,
                    exec_account="root",
                    script_content=prepare_recover_dir_script(dest_dir),
                )
            )

            # Step2 介质下发 bk_host_list 在SendMedia.act会去重.
            sb.add_act(
                **SendMedia.act(
                    act_name=_("MongoDB-介质下发"),
                    file_list=file_list,
                    bk_host_list=bk_host_list,
                    file_target_path=actuator_workdir,
                )
            )
            # Step3 下载备份文件
            sb.add_parallel_sub_pipeline(sub_flow_list=step3_sub)
            # Step4 执行回档
            sb.add_parallel_sub_pipeline(sub_flow_list=step4_sub)

            root_sub.append(sb.build_sub_process(_("{}").format(cluster.name)))

        #
        pipeline.add_parallel_sub_pipeline(sub_flow_list=root_sub)
        # 运行流程
        pipeline.run_pipeline()
