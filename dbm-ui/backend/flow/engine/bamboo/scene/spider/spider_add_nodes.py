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
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import (
    add_spider_masters_sub_flow,
    add_spider_slaves_sub_flow,
)
from backend.flow.engine.bamboo.scene.spider.common.exceptions import NormalSpiderFlowException
from backend.flow.engine.validate.base_validate import BaseValidator
from backend.flow.engine.validate.exceptions import CheckDisasterToleranceException
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
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
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            sub_pipelines.append(
                self.add_spider_nodes_with_cluster(
                    cluster_id=info["cluster_id"],
                    add_spider_role=info["add_spider_role"],
                    add_spider_hosts=info["spider_ip_list"],
                )
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline(init_trans_data_class=SystemInfoContext())

    def add_spider_nodes_with_cluster(
        self,
        cluster_id: int,
        add_spider_role: TenDBClusterSpiderRole,
        add_spider_hosts: list,
        new_db_module_id: int = 0,
        new_pkg_id: int = 0,
        is_check_disaster_tolerance_level: bool = True,
    ):
        """
        定义添加节点的子流程
        """

        # 获取对应集群相关对象
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
            )

        # 在做一下容灾级别检查，因为flow validator 只能做前置检验，这是没有申请到机器，所以只能在flow构建时判断
        # 查询出集群已经存在的spider信息
        exists_hosts = [
            {"ip": i.machine.ip, "sub_zone_id": i.machine.bk_sub_zone_id, "rack_id": i.machine.bk_rack_id}
            for i in cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=add_spider_role)
        ]
        if is_check_disaster_tolerance_level and not BaseValidator.check_disaster_tolerance_level(
            cluster, add_spider_hosts + exists_hosts
        ):
            raise CheckDisasterToleranceException(
                message=_(
                    "[{}]集群spider节点不满足容灾要求[{}]，请检查，添加后预期节点信息:{}".format(
                        cluster.immute_domain, cluster.disaster_tolerance_level, add_spider_hosts + exists_hosts
                    )
                )
            )

        # 补充这次单据需要的隐形参数，spider版本以及字符集
        sub_flow_context = {
            "uid": self.data["uid"],
            "bk_biz_id": cluster.bk_biz_id,
            "cluster_id": cluster.id,
            "created_by": self.data["created_by"],
            "ticket_type": self.data["ticket_type"],
            "spider_ip_list": add_spider_hosts,
            "new_db_module_id": new_db_module_id,
        }

        if add_spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:

            # 加入spider-master 子流程
            return self.add_spider_master_notes(sub_flow_context, cluster, new_db_module_id, new_pkg_id)

        elif add_spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE:

            # 加入spider-slave 子流程
            return self.add_spider_slave_notes(sub_flow_context, cluster, new_db_module_id, new_pkg_id)

        else:
            # 理论上不会出现，出现就中断这次流程构造
            raise NormalSpiderFlowException(
                message=_("[{}]This type of role addition is not supported".format(add_spider_role))
            )

    def add_spider_master_notes(
        self, sub_flow_context: dict, cluster: Cluster, new_db_module_id: int = 0, new_pkg_id: int = 0
    ):
        """
        定义spider master集群部署子流程
        目前产品形态 spider专属一套集群，所以流程只支持spider单机单实例安装
        """

        # 启动子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

        # 阶段1 根据场景执行添加spider-master子流程
        sub_pipeline.add_sub_pipeline(
            sub_flow=add_spider_masters_sub_flow(
                cluster=cluster,
                add_spider_masters=sub_flow_context["spider_ip_list"],
                root_id=self.root_id,
                uid=sub_flow_context["uid"],
                parent_global_data=sub_flow_context,
                is_add_spider_mnt=False,
                new_db_module_id=new_db_module_id,
                new_pkg_id=new_pkg_id,
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
            sub_flow=standardize_mysql_cluster_subflow(
                bk_cloud_id=cluster.bk_cloud_id,
                bk_biz_id=cluster.bk_biz_id,
                instances=[
                    "{}:{}".format(spider["ip"], cluster.proxyinstance_set.first().port)
                    for spider in sub_flow_context["spider_ip_list"]
                ],
                root_id=self.root_id,
                data=copy.deepcopy(sub_flow_context),
                with_actuator=False,
            )
        )
        return sub_pipeline.build_sub_process(sub_name=_("[{}]添加spider-master节点流程".format(cluster.name)))

    def add_spider_slave_notes(
        self, sub_flow_context: dict, cluster: Cluster, new_db_module_id: int = 0, new_pkg_id: int = 0
    ):
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
                uid=sub_flow_context["uid"],
                parent_global_data=copy.deepcopy(sub_flow_context),
                new_db_module_id=new_db_module_id,
                new_pkg_id=new_pkg_id,
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
            sub_flow=standardize_mysql_cluster_subflow(
                bk_cloud_id=cluster.bk_cloud_id,
                bk_biz_id=cluster.bk_biz_id,
                instances=[
                    "{}:{}".format(spider["ip"], cluster.proxyinstance_set.first().port)
                    for spider in sub_flow_context["spider_ip_list"]
                ],
                root_id=self.root_id,
                data=copy.deepcopy(sub_flow_context),
                with_actuator=False,
                with_bk_plugin=False,
                with_instance_standardize=False,
                with_cc_standardize=False,
                with_collect_sysinfo=False,
            )
        )
        return sub_pipeline.build_sub_process(sub_name=_("[{}]添加spider-slave节点流程".format(cluster.name)))
