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

from backend.db_meta.enums import ClusterEntryRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import (
    add_spider_masters_sub_flow,
    add_spider_slaves_sub_flow,
    build_apps_for_spider_sub_flow,
)
from backend.flow.engine.bamboo.scene.spider.common.exceptions import NormalSpiderFlowException
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class TenDBClusterAddNodesFlow(object):
    """
    构建TenDB Cluster 添加 spider 节点；添加不同角色的spider，处理方式不一样
    目前只支持spider_master/spider_slave 角色的添加
    支持不同云区域的合并操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def add_spider_nodes(self):
        """
        定义TenDB Cluster扩容接入层的后端流程
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            # 获取对应集群相关对象
            cluster = Cluster.objects.get(id=info["cluster_id"])

            # 根据集群去bk-config获取对应spider版本和字符集
            spider_charset, spider_version = get_spider_version_and_charset(
                bk_biz_id=cluster.bk_biz_id, db_module_id=cluster.db_module_id
            )

            # 拼接子流程的全局参数
            sub_flow_context.update(info)

            # 补充这次单据需要的隐形参数，spider版本以及字符集
            sub_flow_context["spider_charset"] = spider_charset
            sub_flow_context["spider_version"] = spider_version

            if info["add_spider_role"] == TenDBClusterSpiderRole.SPIDER_MASTER:

                # 加入spider-master 子流程
                sub_pipelines.append(self.add_spider_master_notes(sub_flow_context, cluster))

            elif info["add_spider_role"] == TenDBClusterSpiderRole.SPIDER_SLAVE:

                # 先判断集群是否存在已添加从集群，如果没有则跳过这次扩容，判断依据是集群是存在有且只有一个的从域名
                slave_dns = cluster.clusterentry_set.get(role=ClusterEntryRole.SLAVE_ENTRY)
                if not slave_dns:
                    logger.warning(_("[{}]The cluster has not added a slave cluster, skip".format(cluster.name)))
                    continue

                # 加入spider-slave 子流程
                sub_pipelines.append(self.add_spider_slave_notes(sub_flow_context, cluster, slave_dns.entry))

            else:
                # 理论上不会出现，出现就中断这次流程构造
                raise NormalSpiderFlowException(
                    message=_("[{}]This type of role addition is not supported".format(info["add_spider_role"]))
                )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()

    def add_spider_master_notes(self, sub_flow_context: dict, cluster: Cluster):
        """
        定义spider master集群部署子流程
        目前产品形态 spider专属一套集群，所以流程只支持spider单机单实例安装
        todo 目前spider-master扩容功能开发中，当前中控版本需要调整，等最新版本做联调工作
        """

        # 启动子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

        # 阶段1 根据场景执行添加spider-master子流程
        sub_pipeline.add_sub_pipeline(
            sub_flow=add_spider_masters_sub_flow(
                cluster=cluster,
                add_spider_masters=sub_flow_context["spider_ip_list"],
                root_id=self.root_id,
                parent_global_data=sub_flow_context,
                is_add_spider_mnt=False,
            )
        )

        # 阶段2 变更db_meta数据
        sub_pipeline.add_act(
            act_name=_("更新DBMeta元信息"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=SpiderDBMeta.add_spider_master_nodes_apply.__name__)),
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
        return sub_pipeline.build_sub_process(sub_name=_("[{}]添加spider-master节点流程".format(cluster.name)))

    def add_spider_slave_notes(self, sub_flow_context: dict, cluster: Cluster, slave_dns: str):
        """
        添加spider-slave节点的子流程流程逻辑
        必须集群存在从集群，才能添加
        """

        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

        # 阶段1 根据场景执行添加spider-slave子流程
        sub_pipeline.add_sub_pipeline(
            sub_flow=add_spider_slaves_sub_flow(
                cluster=cluster,
                add_spider_slaves=sub_flow_context["spider_ip_list"],
                root_id=self.root_id,
                parent_global_data=copy.deepcopy(sub_flow_context),
                slave_domain=slave_dns,
            )
        )
        # 阶段2 变更db_meta数据
        sub_pipeline.add_act(
            act_name=_("更新DBMeta元信息"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=SpiderDBMeta.add_spider_slave_nodes_apply.__name__)),
        )

        # 阶段3 安装周边程序
        sub_pipeline.add_sub_pipeline(
            sub_flow=build_apps_for_spider_sub_flow(
                bk_cloud_id=cluster.bk_cloud_id,
                spiders=[spider["ip"] for spider in sub_flow_context["spider_ip_list"]],
                root_id=self.root_id,
                parent_global_data=copy.deepcopy(sub_flow_context),
                spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE,
            )
        )
        return sub_pipeline.build_sub_process(sub_name=_("[{}]添加spider-slave节点流程".format(cluster.name)))
