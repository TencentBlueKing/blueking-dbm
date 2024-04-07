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

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.backup import BackupSubTask
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs
from backend.flow.utils.mongodb.mongodb_repo import MongoDBNsFilter, MongoRepository

logger = logging.getLogger("flow")


class MongoBackupFlow(MongoBaseFlow):
    class Serializer(serializers.Serializer):
        class DataRow(serializers.Serializer):
            cluster_id = serializers.IntegerField()
            cluster_type = serializers.CharField()
            backup_type = serializers.CharField(allow_blank=True)
            backup_host = serializers.CharField(allow_blank=True)
            ns_filter = MongoDBNsFilter.Serializer(allow_null=True)

        uid = serializers.CharField()
        created_by = serializers.CharField()
        bk_biz_id = serializers.IntegerField()
        ticket_type = serializers.CharField()
        file_tag = serializers.CharField()
        oplog = serializers.BooleanField()
        infos = DataRow(many=True)

    """MongoDB备份flow
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
        s = self.Serializer(data=self.payload)
        if not s.is_valid():
            raise Exception("payload is invalid {}".format(s.errors))

    def start(self):
        """
        mongo_backup install流程
        """
        logger.debug("MongoBackupFlow start, payload", self.payload)
        # actuator_workdir 提前创建好的，在部署的时候就创建好了.
        actuator_workdir = ActKwargs().get_mongodb_os_conf()["file_path"]
        file_list = GetFileList(db_type=DBType.MongoDB).get_db_actuator_package()

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.payload)

        # 解析输入 确定每个输入的域名实例都存在.
        # 1. 解析每个集群Id的节点列表
        # 2. 备份一般在某个Secondary且非Backup节点上执行
        # 3. 获得密码列表
        # 4. 生成并发子任务.
        # 介质下发——job的api可以多个IP并行执行

        sub_pipelines = []
        # bk_host {ip:"1.1.1.1", bk_cloud_id: "0"}
        bk_host_list = []

        cluster_id_list = [row["cluster_id"] for row in self.payload["infos"]]
        clusters = MongoRepository.fetch_many_cluster_dict(id__in=cluster_id_list)

        for row in self.payload["infos"]:
            try:
                cluster_id = row["cluster_id"]
                cluster = clusters[cluster_id]
                self.check_cluster_valid(cluster, self.payload)
            except Exception as e:
                logger.exception("check_cluster_valid fail")
                raise Exception("check_cluster_valid fail cluster_id:{} {}".format(row["cluster_id"], e))
            logger.debug("sub_pipline start row", row)
            print("sub_pipline start cluster", cluster)

            sub_pl, sub_bk_host_list = BackupSubTask.process_cluster(
                root_id=self.root_id,
                ticket_data=self.payload,
                sub_ticket_data=row,
                cluster=cluster,
                file_path=actuator_workdir,
            )
            if sub_pl is None:
                raise Exception("sub_pl is None")
            if sub_bk_host_list is None or len(sub_bk_host_list) == 0:
                raise Exception("sub_bk_host_list is None")

            bk_host_list.extend(sub_bk_host_list)
            sub_pipelines.append(sub_pl.build_sub_process(_("MongoDB-备份-{}").format(cluster.name)))

        # 介质下发 bk_host_list 在SendMedia.act会去重.
        pipeline.add_act(
            **SendMedia.act(
                act_name=_("MongoDB-介质下发"),
                file_list=file_list,
                bk_host_list=bk_host_list,
                file_target_path=actuator_workdir,
            )
        )
        # 并行执行备份
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 运行流程
        pipeline.run_pipeline()
