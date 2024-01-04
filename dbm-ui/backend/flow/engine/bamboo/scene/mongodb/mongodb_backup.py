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

from backend.configuration.constants import DBType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_fake_install import FlowActKwargs
from backend.flow.engine.bamboo.scene.mongodb.sub_task.backup import BackupSubTask
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import MongoRepository

logger = logging.getLogger("flow")


class MongoBackupFlow(MongoBaseFlow):
    """MongoDB备份flow
    分析 payload，检查输入，生成Flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        self.root_id = root_id
        self.payload = data

    def start(self):
        """
        mongo_backup install流程
        """

        # backup_dir 提前创建好的，在部署的时候就创建好了.
        backup_dir = FlowActKwargs(self.payload).get_backup_dir()
        file_list = GetFileList(db_type=DBType.MongoDB).get_db_actuator_package()

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.payload)

        # 解析输入
        # 1. 解析每个集群Id的节点列表
        # 2. 备份一般在某个Secondary且非Backup节点上执行. 但由于无法连接mongod，这里怎么搞？
        # 3. 获得密码列表
        # 4. 生成并发子任务.
        # 介质下发——job的api可以多个IP并行执行

        sub_pipelines = []
        # bk_host {ip:"x.x.x.x", bk_cloud_id: "0"}
        bk_host_list = []

        # 域名忽略大小写.
        cluster_domain_list = [row["cluster_domain"].lower() for row in self.payload["data_for_backup"]]
        clusters = MongoRepository.fetch_many_cluster_dict(immute_domain__in=cluster_domain_list)

        for row in self.payload["data_for_backup"]:
            domain_lower = row["cluster_domain"].lower()
            cluster = clusters[domain_lower]
            self.check_cluster(cluster, self.payload)
            sub_pl, sub_bk_host_list = BackupSubTask.process_cluster(
                root_id=self.root_id,
                ticket_data=self.payload,
                sub_ticket_data=row,
                cluster=cluster,
                backup_dir=backup_dir,
            )
            bk_host_list.extend(sub_bk_host_list)
            sub_pipelines.append(sub_pl.build_sub_process(_("MongoDB-备份-{}".format(cluster.name))))

        send_media_kwargs = {
            "file_list": file_list,
            "ip_list": bk_host_list,
            "exec_ips": [item["ip"] for item in bk_host_list],
            "file_target_path": backup_dir + "/install",
        }
        pipeline.add_act(
            act_name=_("MongoDB-介质下发"),
            act_component_code=ExecSendMediaOperationComponent.code,
            kwargs=send_media_kwargs,
        )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 运行流程
        pipeline.run_pipeline()
