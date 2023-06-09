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
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_cluster_info
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


class MysqlFlashbackFlow(object):
    """
    mysql flashback 回档数据
    支持跨云管理
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def mysql_flashback_flow(self):
        """
        flashback 回档数据
        """
        mysql_restore_slave_pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.data))
        sub_pipeline_list = []
        for info in self.data["infos"]:
            ticket_data = copy.deepcopy(self.data)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
            one_cluster = get_cluster_info(info["cluster_id"])
            one_cluster.update(info)
            one_cluster["work_dir"] = f"/data/dbbak/{self.root_id}"

            sub_pipeline.add_act(
                act_name=_("下发db-actor到集群主节点{}").format(one_cluster["master_ip"]),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=one_cluster["bk_cloud_id"],
                        exec_ip=one_cluster["master_ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("flashback启动恢复数据中{}").format(one_cluster["master_ip"]),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=one_cluster["master_ip"],
                        bk_cloud_id=one_cluster["bk_cloud_id"],
                        cluster=one_cluster,
                        get_mysql_payload_func=MysqlActPayload.get_mysql_flashback_payload.__name__,
                    )
                ),
            )
            sub_pipeline_list.append(sub_pipeline.build_sub_process(sub_name=_("flash开始恢复数据")))

        mysql_restore_slave_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_restore_slave_pipeline.run_pipeline()
