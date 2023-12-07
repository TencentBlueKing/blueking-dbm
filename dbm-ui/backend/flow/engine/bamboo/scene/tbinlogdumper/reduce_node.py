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

from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.common_sub_flow import reduce_tbinlogdumper_sub_flow
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import NormalTBinlogDumperFlowException
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class TBinlogDumperReduceNodesFlow(object):
    """
    构建  tbinlogdumper节点删除, 按集群维度去聚合卸载
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

    def reduce_nodes(self):

        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:

            # 启动子流程
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            # 拼接子流程的全局参数
            sub_flow_context.update(info)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 按集群维度卸载TBinlogDumper实例
            sub_pipeline.add_sub_pipeline(
                sub_flow=reduce_tbinlogdumper_sub_flow(
                    bk_biz_id=int(self.data["bk_biz_id"]),
                    bk_cloud_id=int(info["bk_cloud_id"]),
                    root_id=self.root_id,
                    uid=self.data["uid"],
                    reduce_ids=info["reduce_ids"],
                    created_by=self.data["created_by"],
                )
            )

            # 删除元数据
            sub_pipeline.add_act(
                act_name=_("删除实例元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.reduce_tbinlogdumper.__name__,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("云区域[{}]下架TBinlogDumper实例".format(info["bk_cloud_id"])))
            )

        if not sub_pipelines:
            raise NormalTBinlogDumperFlowException(message=_("找不到需要下架的实例，拼装TBinlogDumper下架流程失败"))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
