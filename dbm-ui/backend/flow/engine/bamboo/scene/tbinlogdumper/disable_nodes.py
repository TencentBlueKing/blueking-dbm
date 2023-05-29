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

from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import NormalTBinlogDumperFlowException
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.tbinlogdumper.stop_slave import TBinlogDumperStopSlaveComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.tbinlogdumper.context_dataclass import StopSlaveKwargs

logger = logging.getLogger("flow")


class TBinlogDumperDisableNodesFlow(object):
    """
    构建  tbinlogdumper 节点禁用
    目前仅支持 tendb-ha 架构
    支持不同云区域的合并操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

        tbinlogdumpers = ExtraProcessInstance.objects.filter(id__in=self.data["disable_ids"])
        if len(tbinlogdumpers) == 0:
            # 如果根据下架的id list 获取的元信息为空，则作为异常处理
            raise NormalTBinlogDumperFlowException(
                message=_("传入的TBinlogDumper进程信息已不存在[{}]，请联系系统管理员".format(self.data["disable_ids"]))
            )
        self.nodes = tbinlogdumpers

    def disable_nodes(self):
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for node in self.nodes:
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context["disable_ids"] = [node.id]

            # 生成子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            sub_pipeline.add_act(
                act_name=_("中断同步"),
                act_component_code=TBinlogDumperStopSlaveComponent.code,
                kwargs=asdict(
                    StopSlaveKwargs(
                        bk_cloud_id=node.bk_cloud_id,
                        is_safe=True,
                        tbinlogdumper_ip=node.ip,
                        tbinlogdumper_port=node.listen_port,
                    )
                ),
            )
            sub_pipeline.add_act(
                act_name=_("变更实例状态"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.disable_tbinlogdumper.__name__,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("[{}:{}]实例禁用".format(node.ip, node.listen_port)))
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
