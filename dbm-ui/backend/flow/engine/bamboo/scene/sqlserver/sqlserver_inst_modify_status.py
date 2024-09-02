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

from django.utils.translation import ugettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta

logger = logging.getLogger("flow")


class SqlserverModifyStatusFlow(BaseFlow):
    """
    构建Sqlserver的数据库建立同步的流程类
    兼容跨云集群的执行
    """

    def run_flow(self):
        """
        定义Sqlserver的修改故障实例状态的执行流程，支持多集群并发执行
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            cluster = Cluster.objects.get(id=info["cluster_id"])
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            sub_pipeline.add_act(
                act_name=_("修改故障实例状态【未接入DBHA】"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.modify_status_for_not_joined_dbha.__name__,
                    )
                ),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}修改故障实例状态".format(cluster.name))))

        # 内部检测sub_pipelines是否为空
        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
