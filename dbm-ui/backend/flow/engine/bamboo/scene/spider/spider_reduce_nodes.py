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
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryRole, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.flow.consts import MIN_SPIDER_MASTER_COUNT, MIN_SPIDER_SLAVE_COUNT, DnsOpType, InstanceStatus
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildEntrysManageSubflow
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import reduce_spiders_flow
from backend.flow.engine.bamboo.scene.spider.common.exceptions import NormalSpiderFlowException
from backend.flow.engine.validate.base_validate import BaseValidator
from backend.flow.engine.validate.exceptions import CheckDisasterToleranceException
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.check_client_connections import CheckClientConnComponent
from backend.flow.plugins.components.collections.mysql.flow_output_summary import MysqlFlowOutputSummaryComponent
from backend.flow.plugins.components.collections.spider.drop_spider_ronting import DropSpiderRoutingComponent
from backend.flow.utils.mysql.flow_output_presets.instance_change import InstanceChangeAction
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

    @staticmethod
    def _build_reduce_items(
        cluster: Cluster,
        reduce_spider_role: TenDBClusterSpiderRole,
        reduce_spider_hosts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """按调用方持有的 cluster 对象直接装配"spider 缩容摘要" items（对齐 :class:`InstanceChangeSummarySerializer`）。

        设计要点 / 怎么做：
          - 调用方（:meth:`reduce_spider_nodes_with_cluster`）已持有 :class:`Cluster` model 实例，
            本方法直接复用，**不再重复反查 db_meta**。
          - **必须在 flow 构建阶段调用**：缩容流程会在运行时清理 db_meta 中被下架实例，
            届时反查端口将失败；因此在构建期把端口冻结进 items，交由 pipeline 运行时直落。
          - 端口按"被下架实例自身"反查（同角色 + IP 精确定位到 ProxyInstance），
            避免"取剩余任一实例端口"在异构端口场景下失真。
          - `.value` 显式取字符串，用于 QuerySet 过滤与出参 extra 展示；避免依赖
            :class:`StrStructuredEnum` 的隐式 ``__str__`` 序列化行为。
          - db_meta 约束下同业务同 IP:Port 唯一归属一个集群，`instance` 单键即可承载幂等；
            集群归属通过一等字段 `cluster_domain` 表达。

        :param cluster: 集群 model 实例；调用方已持有，直接复用避免二次反查
        :param reduce_spider_role: 待下架的 spider 角色枚举，必须是
                                   :class:`TenDBClusterSpiderRole.SPIDER_MASTER` 或
                                   :class:`TenDBClusterSpiderRole.SPIDER_SLAVE`
        :param reduce_spider_hosts: 待下架的 spider 机器列表；每项至少含 ``ip`` 字段
        :return: 摘要行列表；结构严格对齐 InstanceChangeSummarySerializer 字段契约；
                 ``reduce_spider_hosts`` 为空时返回空列表，由外层调用方走 "items 空 → no-op"
                 分支，不阻塞流程。

        边界 / 异常：
          - ``reduce_spider_hosts`` 为空 -> 返回空列表（属兜底防御，主流程更早的
            ``__pre_check_and_calc_reduce_spiders`` 空列表校验会先失败）；
          - 某 IP 在该集群该角色下未找到对应 :class:`ProxyInstance` -> 忽略该 IP，
            不产出对应行（属兜底防御，主流程 pre_check 会更早失败）。
        """
        if not reduce_spider_hosts:
            return []

        # 批量反查目标 IP 的 ProxyInstance（同角色 + 同集群 + IP 属于待下架列表），避免 N+1 查询
        ip_list: List[str] = [str(h["ip"]) for h in reduce_spider_hosts]
        proxy_map: Dict[str, ProxyInstance] = {
            pi.machine.ip: pi
            for pi in cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=reduce_spider_role.value,
                machine__ip__in=ip_list,
            )
        }

        items: List[Dict[str, Any]] = []
        for host in reduce_spider_hosts:
            ip: str = str(host["ip"])
            proxy: Optional[ProxyInstance] = proxy_map.get(ip)
            if proxy is None:
                # 待下架实例在 db_meta 中该角色下不存在；属兜底防御，主流程 pre_check 会更早失败
                continue
            items.append(
                {
                    "cluster_domain": cluster.immute_domain,
                    "instance": f"{ip}{IP_PORT_DIVIDER}{int(proxy.port)}",
                    "action": InstanceChangeAction.REDUCE.value,
                    "status": "success",
                    "related_instance": "",
                    "message": "",
                    # 扩展信息承载 spider 角色语义，供前端区分 spider_master / spider_slave
                    "extra": _("操作角色{}").format(reduce_spider_role.value),
                }
            )
        return items

    def reduce_spider_nodes_with_cluster(
        self,
        cluster_id: int,
        spider_reduced_hosts: list,
        reduce_spider_role: TenDBClusterSpiderRole,
        spider_reduced_to_count_snapshot: int,
        is_check_min_count: bool = True,
        is_check_disaster_tolerance_level: bool = True,
        is_check_process: bool = True,
        disable_manual_confirm: bool = False,
        is_rebuild: bool = False,
        is_print_summary: bool = False,
    ):
        """
        根据cluster维度处理缩容子流程
        @param cluster_id: 集群id
        @param spider_reduced_hosts: 带下架的实例ip
        @param reduce_spider_role: 下架角色
        @param spider_reduced_to_count_snapshot 单据传入的剩余spider实例数量快照
        @param is_check_min_count 是否要做下架后spider角色的数量的检测，默认是检测的。但特殊情况可以不检测，比如替换spider实例
        @param is_check_disaster_tolerance_level: 是否评估缩容后的是否满足容灾要求，默认是检测的。但特殊情况可以不检测，比如替换spider实例
        @param is_check_process: 是否需要检测spider端连接情况，默认是检测的。如果用户不做检测，可以设置为False
        @param disable_manual_confirm: 是否禁用人工确认，默认是不禁用的。但特殊情况可以禁用，比如自愈所产生的替换单据
        @param is_rebuild: 是否是重建场景，默认是False, 非重建场景
        @param is_print_summary: 是否在子流程尾部追加"写入spider变更摘要"act，默认False；
            - True：仅供 "spider 缩容顶层入口"（:meth:`reduce_spider_nodes`）调用；本方法在
              build_sub_process 之前调用 :meth:`_build_reduce_items` **在 flow 构建阶段就地装配**
              REDUCE 语义的 InstanceChangeSummary 行（此时 db_meta 完好，端口可反查），
              装配好的 items 随 pipeline 打包，运行时直接落库。
            - False：不挂载摘要节点，供衍生 flow（Switch / Rebuild / DisasterRecover）复用时
              避免误落"缩容"语义摘要。
        """
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

        # 这种处理其实隐含了一个前提就是一个ip只能有一个port
        available_spider_addresses = []
        unavailable_spider_addresses = []
        for pi in ProxyInstance.objects.filter(machine__ip__in=[i["ip"] for i in reduce_spiders], cluster=cluster):
            if pi.status == InstanceStatus.UNAVAILABLE:
                unavailable_spider_addresses.append(pi.ip_port)
            else:
                available_spider_addresses.append(pi.ip_port)

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
        if is_check_process and not disable_manual_confirm:
            check_client_connection_acts = []
            if available_spider_addresses:
                check_client_connection_acts.append(
                    {
                        "act_name": _("检测回收Spider端连接情况"),
                        "act_component_code": CheckClientConnComponent.code,
                        "kwargs": asdict(
                            CheckClientConnKwargs(
                                bk_cloud_id=cluster.bk_cloud_id,
                                check_instances=available_spider_addresses,
                            )
                        ),
                    }
                )

            if unavailable_spider_addresses:
                check_client_connection_acts.append(
                    {
                        "act_name": _("检测回收 Unavailable Spider端连接情况"),
                        "act_component_code": CheckClientConnComponent.code,
                        "kwargs": asdict(
                            CheckClientConnKwargs(
                                bk_cloud_id=cluster.bk_cloud_id,
                                check_instances=unavailable_spider_addresses,
                            )
                        ),
                        "error_ignorable": True,
                    }
                )

            sub_pipeline.add_parallel_acts(check_client_connection_acts)

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
            sub_flow=reduce_spiders_flow(
                cluster=cluster,
                reduce_spiders=reduce_spiders,
                root_id=self.root_id,
                parent_global_data=sub_flow_context,
                spider_role=reduce_spider_role,
                is_rebuild=is_rebuild,
            )
        )

        # 尾部（可选）写入spider变更摘要：必须放在 build_sub_process 之前才能追加进 pipeline。
        # items 必须在 flow 构建阶段就地装配完成——运行时 db_meta 里的被下架实例会被清理，
        # 届时反查端口将失败。幂等由 InstanceChangeSummarySerializer.table_primary_key = "instance"
        # 保证：同 IP:Port 重复写入 → 后写覆盖前写。
        if is_print_summary:
            # reduce_spider_role 可能是枚举成员或枚举 value 字符串（历史调用点异构），统一归一为枚举成员
            role_enum: TenDBClusterSpiderRole = (
                reduce_spider_role
                if isinstance(reduce_spider_role, TenDBClusterSpiderRole)
                else TenDBClusterSpiderRole(reduce_spider_role)
            )
            sub_pipeline.add_act(
                act_name=_("写入spider变更摘要"),
                act_component_code=MysqlFlowOutputSummaryComponent.code,
                kwargs={
                    "preset": "instance_change",
                    "items": self._build_reduce_items(cluster, role_enum, spider_reduced_hosts),
                },
            )

        return sub_pipeline.build_sub_process(
            sub_name=_("[{}]减少{}节点流程".format(cluster.immute_domain, reduce_spider_role))
        )

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
                    is_check_process=self.data.get("is_safe", True),
                    # 仅"缩容"单据顶层入口开启摘要写入；衍生 flow（Switch / Rebuild /
                    # DisasterRecover）不传该参数，走默认 False，天然不会误落 REDUCE 摘要行。
                    is_print_summary=True,
                )
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # pipeline.run_pipeline()
        # 启动接入单据值守监听
        pipeline.run_pipeline_with_sidecar(
            check_ai_monitor_cluster_list=[int(info["cluster_id"]) for info in self.data["infos"]],
        )
