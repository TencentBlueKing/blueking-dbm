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

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import (
    add_spider_masters_sub_flow,
    build_apps_for_spider_sub_flow,
)
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class TenDBClusterAddSpiderMNTFlow(object):
    """
    tendb cluster添加运维节点
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def add_spider_mnt(self):
        """
        上架spider节点，授予中控访问权限
        加入路由
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            # 拼接子流程所需全局参数
            sub_flow_context = copy.deepcopy(self.data)
            # 拷贝了字典类型的参数，并将键 infos 剔除
            sub_flow_context.pop("infos")
            # 加入info，info中包含实例的私有信息
            sub_flow_context.update(info)
            # 通过cluster_id获取对应集群对象
            cluster = Cluster.objects.get(id=info["cluster_id"])
            # 通过bk—config获取版本号和字符集信息
            # 获取的是业务默认配置，不一定是集群当前配置
            spider_charset, spider_version = get_spider_version_and_charset(
                bk_biz_id=cluster.bk_biz_id, db_module_id=cluster.db_module_id
            )
            # 补充这次单据需要的隐形参数，spider版本以及字符集
            sub_flow_context["spider_charset"] = spider_charset
            sub_flow_context["spider_version"] = spider_version
            # 启动子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
            # 阶段1 根据场景执行添加spider-master子流程
            sub_pipeline.add_sub_pipeline(
                sub_flow=add_spider_masters_sub_flow(
                    cluster=cluster,
                    add_spider_masters=sub_flow_context["spider_ip_list"],
                    root_id=self.root_id,
                    parent_global_data=sub_flow_context,
                    is_add_spider_mnt=True,
                )
            )

            # 阶段2 变更db_meta数据
            sub_pipeline.add_act(
                act_name=_("更新DBMeta元信息"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=SpiderDBMeta.add_spider_mnt.__name__)),
            )

            # 阶段3 安装周边程序
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_apps_for_spider_sub_flow(
                    bk_cloud_id=cluster.bk_cloud_id,
                    spiders=[spider["ip"] for spider in sub_flow_context["spider_ip_list"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(sub_flow_context),
                    spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
                )
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}添加spider_mnt节点流程".format(cluster.name))))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
