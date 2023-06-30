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
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import reduce_spider_slaves_flow
from backend.flow.engine.bamboo.scene.spider.common.exceptions import NormalSpiderFlowException
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.spider.drop_spider_ronting import DropSpiderRoutingComponent
from backend.flow.utils.mysql.mysql_act_dataclass import RecycleDnsRecordKwargs
from backend.flow.utils.spider.spider_act_dataclass import DropSpiderRoutingKwargs

logger = logging.getLogger("flow")


class TenDBClusterReduceNodesFlow(object):
    """
    构建TenDB Cluster 减少 spider 节点；添加不同角色的spider，处理方式不一样
    目前只支持spider_master/spider_slave 角色的减少
    节点减少不是无脑操作，应该有数量上限制：spider_master至少需要保留2台；spider_slave至少需要保留1台
    支持不同云区域的合并操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.mix_spider_master_count = 2
        self.mix_spider_slave_count = 1

    def __calc_reduce_spiders(
        self, cluster: Cluster, reduce_spider_role: TenDBClusterSpiderRole, spider_reduced_to_count: int
    ):
        """
        根据每个子单据的操作spider角色和缩容剩余数量，来计算出合理的待回收spider节点列表
        @param cluster: 集群对象
        @param reduce_spider_role: 待回收角色
        @param spider_reduced_to_count: 缩容至数量
        """
        # 检测
        spiders_count = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=reduce_spider_role).count()
        if reduce_spider_role == TenDBClusterSpiderRole.SPIDER_MASTER.value and (
            spider_reduced_to_count < self.mix_spider_master_count or spider_reduced_to_count >= spiders_count
        ):

            raise NormalSpiderFlowException(
                message=_(
                    "集群最后不能少于{}个spider_master实例,或者不能大于集群存量[{}]".format(self.mix_spider_master_count, spiders_count)
                )
            )

        if reduce_spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE.value and (
            spider_reduced_to_count < self.mix_spider_slave_count or spider_reduced_to_count >= spiders_count
        ):

            raise NormalSpiderFlowException(
                message=_(
                    "集群最后不能少于{}个spider_slave实例，或者不能大于集群存量[{}]".format(self.mix_spider_slave_count, spiders_count)
                )
            )

        # 计算合理的待下架的spider节点列表

        ctl_primary = cluster.tendbcluster_ctl_primary_address()

        # 选择上尽量避开ctl_primary的选择, 避免做一次切换逻辑
        reduce_spiders = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=reduce_spider_role
        ).exclude(machine__ip=ctl_primary.split(":"[0]))[: spiders_count - spider_reduced_to_count]

        return [{"ip": s.machine.ip} for s in reduce_spiders]

    def reduce_spider_nodes(self):
        """
        定义TenDB Cluster缩容接入层的后端流程
        todo 目前spider-master缩容功能开发中，当前中控版本需要调整，等最新版本做联调工作
        """

        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            # 拼接子流程的全局参数
            sub_flow_context.update(info)

            # 卸载spider实例级别默认先为True， 看看是否后续让用户自行选择？
            sub_flow_context["force"] = True

            # 获取对应集群相关对象
            cluster = Cluster.objects.get(id=info["cluster_id"])

            # 计算待下架的spider节点列表,转化成全局参数
            reduce_spiders = self.__calc_reduce_spiders(
                cluster=cluster,
                reduce_spider_role=info["reduce_spider_role"],
                spider_reduced_to_count=int(info["spider_reduced_to_count"]),
            )
            sub_flow_context["reduce_spiders"] = reduce_spiders

            # 启动子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 删除spider的路由关系
            sub_pipeline.add_act(
                act_name=_("删除spider的路由关系"),
                act_component_code=DropSpiderRoutingComponent.code,
                kwargs=asdict(
                    DropSpiderRoutingKwargs(
                        cluster_id=cluster.id,
                        is_safe=self.data["is_safe"],
                        reduce_spiders=reduce_spiders,
                    )
                ),
            )

            # 回收对应的域名关系
            sub_pipeline.add_act(
                act_name=_("回收对应spider集群映射"),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    RecycleDnsRecordKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        dns_op_exec_port=cluster.proxyinstance_set.first().port,
                        exec_ip=[info["ip"] for info in reduce_spiders],
                    ),
                ),
            )

            # 后续流程需要在这里加一个暂停节点，让用户在合适的时间执行下架
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

            # 根据场景执行下架spider子流程
            sub_pipeline.add_sub_pipeline(
                sub_flow=reduce_spider_slaves_flow(
                    cluster=cluster,
                    reduce_spiders=reduce_spiders,
                    root_id=self.root_id,
                    parent_global_data=sub_flow_context,
                    spider_role=info["reduce_spider_role"],
                )
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]减少spider节点流程".format(cluster.name))))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
