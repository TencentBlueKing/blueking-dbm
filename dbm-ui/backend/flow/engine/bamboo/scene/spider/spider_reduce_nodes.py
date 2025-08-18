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

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryRole, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.consts import MIN_SPIDER_MASTER_COUNT, MIN_SPIDER_SLAVE_COUNT, DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildEntrysManageSubflow
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import reduce_spider_slaves_flow
from backend.flow.engine.bamboo.scene.spider.common.exceptions import NormalSpiderFlowException
from backend.flow.engine.validate.base_validate import BaseValidator
from backend.flow.engine.validate.exceptions import CheckDisasterToleranceException
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.check_client_connections import CheckClientConnComponent
from backend.flow.plugins.components.collections.spider.drop_spider_ronting import DropSpiderRoutingComponent
from backend.flow.utils.mysql.mysql_act_dataclass import CheckClientConnKwargs
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
        self.mix_spider_master_count = MIN_SPIDER_MASTER_COUNT
        self.mix_spider_slave_count = MIN_SPIDER_SLAVE_COUNT

    def __pre_check_and_calc_reduce_spiders(
        self,
        cluster: Cluster,
        reduce_spider_role: TenDBClusterSpiderRole,
        spider_reduced_hosts: list,
        spider_reduced_to_count_snapshot: int,
        is_check_min_count: bool = True,
        is_check_disaster_tolerance_level: bool = True,
    ):
        """
        根据每个子单据的操作spider角色和缩容剩余数量，来计算出合理的待回收spider节点列表
        @param cluster: 集群对象
        @param reduce_spider_role: 待回收角色
        @param spider_reduced_hosts: 缩容指定的主机
        @param spider_reduced_to_count_snapshot: 单据传入的剩余spider实例数量快照
        @param is_check_min_count 是否要做下架后spider角色的数量的检测，默认是检测的。但特殊情况可以不检测，比如替换spider实例
        @param is_check_disaster_tolerance_level: 是否评估缩容后的是否满足容灾要求，默认是检测的。但特殊情况可以不检测，比如替换spider实例
        """
        # 检测
        # 如果是指定缩容IP，则直接返回
        if not spider_reduced_hosts:
            raise NormalSpiderFlowException(message=_("传入的spider_reduced_hosts参数为空，请联系系统管理员"))

        # spider节点数量
        spiders_count = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=reduce_spider_role).count()

        # 计算出剩余spider节点
        remaining_spiders = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=reduce_spider_role
        ).exclude(machine__ip__in=[i["ip"] for i in spider_reduced_hosts])

        if spider_reduced_to_count_snapshot + len(spider_reduced_hosts) != spiders_count:
            # 此时计算的单据传入的spider数量， 不等于此时的集群的spider数量总数，则认为该单据运行前拓扑发生变更，如果执行下去就会有风险
            raise NormalSpiderFlowException(
                message=_(
                    "[{}]判断到集群{}数量执行前发生变化，有风险！单据记录数量[{}]， 此时的集群数量[{}]".format(
                        cluster.immute_domain,
                        reduce_spider_role,
                        spider_reduced_to_count_snapshot + len(spider_reduced_hosts),
                        spiders_count,
                    )
                )
            )

        if (
            reduce_spider_role == TenDBClusterSpiderRole.SPIDER_MASTER.value
            and (spiders_count - len(spider_reduced_hosts) < self.mix_spider_master_count)
            and is_check_min_count
        ):

            raise NormalSpiderFlowException(
                message=_("[{}]集群最后不能少于{}个spider_master实例".format(cluster.immute_domain, self.mix_spider_master_count))
            )

        if (
            reduce_spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE.value
            and (spiders_count - len(spider_reduced_hosts) < self.mix_spider_slave_count)
            and is_check_min_count
        ):

            raise NormalSpiderFlowException(
                message=_("[{}]集群最后不能少于{}个spider_slave实例".format(cluster.immute_domain, self.mix_spider_slave_count))
            )
        # 判断剩余的spider节点是否满足集群的容灾要求, 如果只剩一个spider节点，则不做判断.
        # spider_slave 角色，不做容灾检查
        if reduce_spider_role == TenDBClusterSpiderRole.SPIDER_MASTER.value:
            check_hosts = [
                {"ip": i.machine.ip, "sub_zone_id": i.machine.bk_sub_zone_id, "rack_id": i.machine.bk_rack_id}
                for i in remaining_spiders
            ]
            if len(check_hosts) > 1:
                if is_check_disaster_tolerance_level and not BaseValidator.check_disaster_tolerance_level(
                    cluster=cluster, hosts=check_hosts
                ):
                    raise CheckDisasterToleranceException(
                        message=_(
                            "[{}]集群剩余spider节点不满足容灾要求[{}]，请检查，剩余的节点信息:{}".format(
                                cluster.immute_domain, cluster.disaster_tolerance_level, check_hosts
                            )
                        )
                    )

        return [{"ip": host["ip"]} for host in spider_reduced_hosts]

    def reduce_spider_nodes_with_cluster(
        self,
        cluster_id: int,
        spider_reduced_hosts: list,
        reduce_spider_role: TenDBClusterSpiderRole,
        spider_reduced_to_count_snapshot: int,
        is_check_min_count: bool = True,
        is_check_disaster_tolerance_level: bool = True,
    ):
        """
        根据cluster维度处理缩容子流程
        @param cluster_id: 集群id
        @param spider_reduced_hosts: 带下架的实例ip
        @param reduce_spider_role: 下架角色
        @param spider_reduced_to_count_snapshot 单据传入的剩余spider实例数量快照
        @param is_check_min_count 是否要做下架后spider角色的数量的检测，默认是检测的。但特殊情况可以不检测，比如替换spider实例
        @param is_check_disaster_tolerance_level: 是否评估缩容后的是否满足容灾要求，默认是检测的。但特殊情况可以不检测，比如替换spider实例
        """
        disable_manual_confirm = self.data.get("disable_manual_confirm", False)

        # 获取对应集群相关对象
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
            )

        # 计算待下架的spider节点列表,转化成全局参数
        reduce_spiders = self.__pre_check_and_calc_reduce_spiders(
            cluster=cluster,
            reduce_spider_role=reduce_spider_role,
            spider_reduced_hosts=spider_reduced_hosts,
            spider_reduced_to_count_snapshot=spider_reduced_to_count_snapshot,
            is_check_min_count=is_check_min_count,
            is_check_disaster_tolerance_level=is_check_disaster_tolerance_level,
        )

        # 拼接子流程全局变量
        sub_flow_context = {
            "uid": self.data["uid"],
            "bk_biz_id": cluster.bk_biz_id,
            "cluster_id": cluster.id,
            "created_by": self.data["created_by"],
            "ticket_type": self.data["ticket_type"],
            "reduce_spiders": reduce_spiders,
            "force": True,
        }

        # 启动子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

        # 预检测
        if self.data["is_safe"]:
            sub_pipeline.add_act(
                act_name=_("检测回收Spider端连接情况"),
                act_component_code=CheckClientConnComponent.code,
                kwargs=asdict(
                    CheckClientConnKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        check_instances=[
                            f"{i['ip']}{IP_PORT_DIVIDER}{cluster.proxyinstance_set.first().port}"
                            for i in reduce_spiders
                        ],
                    )
                ),
            )

        entry_role = ClusterEntryRole.MASTER_ENTRY.value
        if reduce_spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE.value:
            entry_role = ClusterEntryRole.SLAVE_ENTRY.value
        entry_sub_process = BuildEntrysManageSubflow(
            root_id=self.root_id,
            ticket_data=self.data,
            op_type=DnsOpType.RECYCLE_RECORD,
            param={
                "cluster_id": cluster.id,
                "port": cluster.proxyinstance_set.first().port,
                "del_ips": [info["ip"] for info in reduce_spiders],
                "entry_role": [entry_role],
            },
        )
        sub_pipeline.add_sub_pipeline(sub_flow=entry_sub_process)
        # 后续流程需要在这里加一个暂停节点，让用户在合适的时间执行下架
        if not disable_manual_confirm:
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

        # 删除spider的路由关系
        sub_pipeline.add_act(
            act_name=_("删除spider的路由关系"),
            act_component_code=DropSpiderRoutingComponent.code,
            kwargs=asdict(
                DropSpiderRoutingKwargs(
                    cluster_id=cluster.id,
                    reduce_spiders=reduce_spiders,
                )
            ),
        )

        # 根据场景执行下架spider子流程
        sub_pipeline.add_sub_pipeline(
            sub_flow=reduce_spider_slaves_flow(
                cluster=cluster,
                reduce_spiders=reduce_spiders,
                root_id=self.root_id,
                parent_global_data=sub_flow_context,
                spider_role=reduce_spider_role,
            )
        )
        return sub_pipeline.build_sub_process(sub_name=_("[{}]减少spider节点流程".format(cluster.immute_domain)))

    def reduce_spider_nodes(self):
        """
        定义TenDB Cluster缩容接入层的后端流程
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines = []
        for info in self.data["infos"]:
            sub_pipelines.append(
                self.reduce_spider_nodes_with_cluster(
                    cluster_id=info["cluster_id"],
                    spider_reduced_hosts=info["spider_reduced_hosts"],
                    reduce_spider_role=info["reduce_spider_role"],
                    spider_reduced_to_count_snapshot=info["spider_reduced_to_count"],
                )
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
