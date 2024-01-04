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
from backend.flow.engine.bamboo.scene.mongodb.sub_task.remove_ns import RemoveNsSubTask
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs, MongoRepository

logger = logging.getLogger("flow")


class MongoRemoveNsFlow(object):
    """MongoRemoveNsFlowflow
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
        fix me
        """
        helper = ActKwargs()
        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.payload)
        backup_dir = helper.get_backup_dir()
        file_list = GetFileList(db_type=DBType.MongoDB).get_db_actuator_package()

        print("data_for_backup", self.payload["data_for_backup"])

        # todo 改为批量查询.
        sub_pipelines = []
        # bk_host {ip:"1.1.1.1", bk_cloud_id: "0"}
        bk_host_list = []
        # todo 同一机器的多个集群一起备份时，执行备份的机器要尽量错开.

        for row in self.payload["data_for_remove_ns"]:
            cluster = MongoRepository.fetch_one_cluster(immute_domain=row["cluster_domain"])
            check_cluster(cluster, self.payload)
            print("sub_pipline start", row)
            sub_pl, sub_bk_host_list = RemoveNsSubTask.process_cluster(
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
        print("send_media_kwargs", send_media_kwargs)
        pipeline.add_act(
            act_name=_("MongoDB-介质下发"),
            act_component_code=ExecSendMediaOperationComponent.code,
            kwargs=send_media_kwargs,
        )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 运行流程
        pipeline.run_pipeline()


def check_cluster(cluster, payload):
    if cluster is None:
        raise Exception("row.cluster_domain is not exists.")
    if str(cluster.bk_biz_id) != payload["bk_biz_id"]:
        raise Exception(
            "bad bk_biz_id {} vs {} {} {}".format(
                cluster.bk_biz_id, payload["bk_biz_id"], type(cluster.bk_biz_id), type(payload["bk_biz_id"])
            )
        )
