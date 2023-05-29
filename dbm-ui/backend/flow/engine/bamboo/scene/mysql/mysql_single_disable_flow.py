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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DeleteClusterDnsKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLSingleDisableFlow(object):
    """
    构建mysql单节点版禁用流程抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def disable_mysql_single_flow(self):
        """
        定义mysql单节点版禁用流程，支持同时多集群并发禁用模式
        """
        mysql_single_disable_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 多集群下架时循环加入集群下架子流程
        for cluster_id in self.data["cluster_ids"]:

            cluster = Cluster.objects.get(id=cluster_id)

            # 按照集群维度声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            sub_pipeline.add_act(
                act_name=_("回收集群域名"),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    DeleteClusterDnsKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        delete_cluster_id=cluster_id,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("集群变更OFFLINE状态"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_cluster_offline.__name__,
                        cluster={"id": cluster_id},
                    )
                ),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("禁用MySQL单节点集群[{}]").format(cluster.name)))

        mysql_single_disable_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_single_disable_pipeline.run_pipeline()
