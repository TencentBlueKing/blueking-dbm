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
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import (
    add_spider_slaves_sub_flow,
    build_apps_for_spider_sub_flow,
)
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class TenDBSlaveClusterApplyFlow(object):
    """
    构建spider slave 集群添加流程抽象类
    支持不同云区域的db集群合并操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def deploy_slave_cluster(self):
        """
        定义spider slave集群部署流程
        目前产品形态 spider专属一套集群，所以流程只支持spider单机单实例安装
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 机器维度部署spider节点
        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            # 拼接子流程的全局参数
            sub_flow_context.update(info)

            # 获取对应集群相关对象
            try:
                cluster = Cluster.objects.get(id=info["cluster_id"], bk_biz_id=int(self.data["bk_biz_id"]))
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=info["cluster_id"], bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
                )

            # 根据集群去bk-config获取对应spider版本和字符集
            spider_charset, spider_version = get_spider_version_and_charset(
                bk_biz_id=cluster.bk_biz_id, db_module_id=cluster.db_module_id
            )

            # 补充这次单据需要的隐形参数，spider版本以及字符集
            sub_flow_context["spider_charset"] = spider_charset
            sub_flow_context["spider_version"] = spider_version

            # 启动子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 阶段1 按照spider-slave实例
            sub_pipeline.add_sub_pipeline(
                sub_flow=add_spider_slaves_sub_flow(
                    cluster=cluster,
                    add_spider_slaves=info["spider_slave_ip_list"],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(sub_flow_context),
                    slave_domain=info["slave_domain"],
                )
            )

            # 阶段2 添加元数据
            sub_pipeline.add_act(
                act_name=_("更新DBMeta元信息"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=SpiderDBMeta.tendb_cluster_slave_apply.__name__)),
            )

            # 阶段3 spider安装周边组件
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_apps_for_spider_sub_flow(
                    bk_cloud_id=cluster.bk_cloud_id,
                    spiders=[spider["ip"] for spider in info["spider_slave_ip_list"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(sub_flow_context),
                    spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE,
                )
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]添加slave集群".format(cluster.name))))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
