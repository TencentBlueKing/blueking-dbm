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
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.spider_add_nodes import TenDBClusterAddNodesFlow
from backend.flow.engine.bamboo.scene.spider.spider_reduce_nodes import TenDBClusterReduceNodesFlow
from backend.flow.engine.validate.base_validate import BaseValidator
from backend.flow.engine.validate.exceptions import CheckDisasterToleranceException
from backend.flow.plugins.components.collections.common.add_unlock_ticket_type_config import (
    AddUnlockTicketTypeConfigComponent,
)
from backend.flow.plugins.components.collections.common.pause_with_ticket_lock_check import (
    PauseWithTicketLockCheckComponent,
)
from backend.flow.plugins.components.collections.mysql.flow_output_summary import MysqlFlowOutputSummaryComponent
from backend.flow.plugins.components.collections.spider.check_if_normal_for_cluster import (
    CheckIfNormalSpiderNodeComponent,
)
from backend.flow.utils.base.base_dataclass import AddUnLockTicketTypeKwargs, ReleaseUnLockTicketTypeKwargs
from backend.flow.utils.mysql.flow_output_presets.instance_change import InstanceChangeAction
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class TenDBClusterSwitchNodesFlow(TenDBClusterAddNodesFlow, TenDBClusterReduceNodesFlow):
    """
    基于扩容spider实例和缩容spider实例的flow的基类，定义替换spider的flow
    ticket_data参数：
        {
          "uid": "1",
          "created_by": "xxx",
          "bk_biz_id": "1",
          "ticket_type": "TENDBCLUSTER_SPIDER_SWITCH_NODES",
          "infos": [
                      {
                        "cluster_id": 1,
                        "switch_spider_role": "spider_master"
                        "spider_old_ip_list":  [
                          {"ip":"x","bk_cloud_id": 0,"bk_host_id":1},
                          {"ip":"x","bk_cloud_id": 0,"bk_host_id":2}
                        ],
                        "spider_new_ip_list":  [
                          {"ip":"x","bk_cloud_id": 0,"bk_host_id":3,"spec":{}},
                          {"ip":"x","bk_cloud_id": 0,"bk_host_id":4,"spec":{}}
                        ],
                      }
                ]

        }
    """

    # 定义临时解除单据互斥锁的单据类型列表
    temporary_unlock_ticket_type_list = [
        TicketType.TENDBCLUSTER_IMPORT_SQLFILE,
        TicketType.TENDBCLUSTER_FORCE_IMPORT_SQLFILE,
        TicketType.TENDBCLUSTER_SEMANTIC_CHECK,
        TicketType.TENDBCLUSTER_AUTHORIZE_RULES,
    ]

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        # 分别初始化父类的init方法
        super().__init__(root_id=root_id, data=data)
        super(TenDBClusterAddNodesFlow, self).__init__(root_id=root_id, data=data)

    def get_spider_pkg_id_for_tmp_spider_ip(self, cluster_id: int, tmp_spider_ip: str):
        """
        根据已存在的spider机器，获取待添加spider节点版本介质包
        @param cluster_id: 参考集群ID
        @param tmp_spider_ip: 参考spider ip, 必须参数
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
            )

        # 根据参考spider节点
        # 返回对应的 package id
        version_no = cluster.proxyinstance_set.get(machine__ip=tmp_spider_ip).version
        return Package.get_package_for_version_no(
            db_type=DBType.MySQL, pkg_type=PackageType.Spider, version_no=version_no
        ).id

    def calc_install_version_for_each_node(self):
        """
        计算每个待加入的spider节点，需要安装的版本介质包信息
        """
        for info in self.data["infos"]:
            for index, new_spider in enumerate(info["spider_new_ip_list"]):
                new_spider["pkg_id"] = self.get_spider_pkg_id_for_tmp_spider_ip(
                    cluster_id=info["cluster_id"], tmp_spider_ip=info["spider_old_ip_list"][index]["ip"]
                )

    def trans_ticket_data(self) -> Dict[str, Any]:
        """
        根据SaaS传入ticket_data进行转换，转换成适合flow的结构体
        """
        # 使用字典分组集群信息
        cluster_map = {}

        # 遍历infos列表
        for info in self.data["infos"]:
            cluster_id = info["cluster_id"]

            # 首次遇到该cluster_id
            if cluster_id not in cluster_map:
                # 创建新条目（浅拷贝共享相同内存）
                cluster_map[cluster_id] = {
                    "base_info": info,  # 原始信息引用
                    "old_ips": list(info["spider_old_ip_list"]),  # 仅IP列表复制
                    "new_ips": list(info["spider_new_ip_list"]),  # 仅IP列表复制
                }
            else:
                # 添加到已存在的集群分组
                entry = cluster_map[cluster_id]
                entry["old_ips"].extend(info["spider_old_ip_list"])
                entry["new_ips"].extend(info["spider_new_ip_list"])

        # 构建新的infos列表
        new_infos = []
        for entry in cluster_map.values():
            # 创建新条目（复制基础信息）
            new_entry = {
                **entry["base_info"],
                "spider_old_ip_list": entry["old_ips"],
                "spider_new_ip_list": entry["new_ips"],
            }  # 浅拷贝基础字段
            # 更新IP列表（使用合并后的列表）
            new_infos.append(new_entry)

        # 返回更新后的数据
        return {**self.data, "infos": new_infos}

    @staticmethod
    def _build_switch_items(
        cluster: Cluster,
        switch_spider_role: TenDBClusterSpiderRole,
        old_spider_hosts: List[Dict[str, Any]],
        new_spider_hosts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """按调用方持有的 cluster 对象直接装配"spider 替换摘要" items（对齐 :class:`InstanceChangeSummarySerializer`）。

        设计要点 / 怎么做：
          - 调用方（:meth:`switch_nodes_flow_with_cluster`）已持有 :class:`Cluster` model 实例，
            本方法直接复用，**不再重复反查 db_meta**。
          - **必须在 flow 构建阶段调用**：替换流程会在运行时下架旧实例，届时反查端口将失败；
            因此在构建期把端口冻结进 items，交由 pipeline 运行时直落。
          - 端口按"待下架旧实例自身"反查（同角色 + 同 IP 精确定位 ProxyInstance）；
            spider 集群同角色端口一致，一行中 ``instance`` 与 ``related_instance`` 共用同一端口。
          - 每一行：``instance`` = new_ip:port（新实例，作为主键）、``related_instance`` =
            old_ip:port（被替换掉的旧实例）；避免"一次替换拆两行"的冗余。
          - `.value` 显式取字符串，用于 QuerySet 过滤与出参 extra 展示；避免依赖
            :class:`StrStructuredEnum` 的隐式 ``__str__`` 序列化行为。

        :param cluster: 集群 model 实例；调用方已持有，直接复用避免二次反查
        :param switch_spider_role: 替换的 spider 角色枚举
        :param old_spider_hosts: 待下架的旧 spider 机器列表；每项至少含 ``ip``
        :param new_spider_hosts: 顶替的新 spider 机器列表；每项至少含 ``ip``；位置与 old 一一对齐
        :return: 摘要行列表；产出 ``min(len(new), len(old))`` 行，对齐
                 InstanceChangeSummarySerializer 字段契约；老/新任一为空时返回空列表。

        边界 / 异常：
          - ``old_spider_hosts`` 或 ``new_spider_hosts`` 为空 -> 返回空列表；
          - 两列表长度不等 -> 仅处理位置对齐的前 min(len) 行；此处 log_warning 输出提示，
            便于运维定位"摘要少行"的成因；长度校验仍属上游 validator 职责，此处不阻断主流程；
          - 旧 IP 未在 db_meta 找到对应 :class:`ProxyInstance` -> 忽略该对映射行
            （属兜底防御）。
        """
        if not old_spider_hosts or not new_spider_hosts:
            return []

        # 长度不等时不阻断主流程（长度契约属上游 validator 职责），但显式告警避免静默丢失摘要行
        if len(old_spider_hosts) != len(new_spider_hosts):
            logger.warning(
                "spider switch items length mismatch: cluster=%s role=%s old=%d new=%d, "
                "will produce min(old, new) rows and drop the rest",
                cluster.immute_domain,
                switch_spider_role.value,
                len(old_spider_hosts),
                len(new_spider_hosts),
            )

        old_ips: List[str] = [str(h["ip"]) for h in old_spider_hosts]
        # 批量反查旧实例端口；spider 集群同角色端口一致，新实例复用同一端口
        proxy_map: Dict[str, ProxyInstance] = {
            pi.machine.ip: pi
            for pi in cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=switch_spider_role.value,
                machine__ip__in=old_ips,
            )
        }

        # 一对一位置对齐：new_hosts[i] 顶替 old_hosts[i]
        pair_count: int = min(len(old_spider_hosts), len(new_spider_hosts))
        items: List[Dict[str, Any]] = []
        for idx in range(pair_count):
            old_ip: str = str(old_spider_hosts[idx]["ip"])
            new_ip: str = str(new_spider_hosts[idx]["ip"])
            proxy: Optional[ProxyInstance] = proxy_map.get(old_ip)
            if proxy is None:
                # 旧实例在 db_meta 中该角色下不存在；属兜底防御
                continue
            port: int = int(proxy.port)
            items.append(
                {
                    "cluster_domain": cluster.immute_domain,
                    "instance": f"{new_ip}{IP_PORT_DIVIDER}{port}",
                    "action": InstanceChangeAction.SWITCH.value,
                    "status": "success",
                    "related_instance": f"{old_ip}{IP_PORT_DIVIDER}{port}",
                    "message": "",
                    # 扩展信息承载 spider 角色语义，供前端区分 spider_master / spider_slave
                    "extra": _("操作角色{}").format(switch_spider_role.value),
                }
            )
        return items

    def switch_nodes_flow_with_cluster(
        self,
        cluster_id: int,
        spider_role: TenDBClusterSpiderRole,
        old_spider_hosts: list,
        new_spider_hosts: list,
        sub_flow_context: dict,
        disable_manual_confirm: bool = False,
        is_print_summary: bool = False,
    ):
        """
        根据集群维度，并发处理每个集群的替换节点信息
        流程步骤：
        1：给集群先添加新的spider实例
        2：人工确认
        3：给集群指定的spider实例下架

        @param cluster_id: 集群ID
        @param spider_role: 替换的 spider 角色
        @param old_spider_hosts: 待下架的旧 spider 机器列表
        @param new_spider_hosts: 顶替的新 spider 机器列表；位置与 old 一一对齐
        @param sub_flow_context: 子流程上下文
        @param disable_manual_confirm: 是否禁用人工确认，默认False；DB_HA 自愈复用需置 True
        @param is_print_summary: 是否在子流程尾部追加"写入spider变更摘要"act，默认False；
            - True：仅供 "spider 替换顶层入口"（:meth:`switch_spider_nodes`）调用；本方法在
              build_sub_process 之前调用 :meth:`_build_switch_items` **在 flow 构建阶段就地装配**
              SWITCH 语义的 InstanceChangeSummary 行（此时 db_meta 完好，旧实例端口可反查），
              装配好的 items 随 pipeline 打包，运行时直接落库。
            - False：不挂载摘要节点，供衍生 flow（Rebuild / ChangeSpec / Upgrade / DisasterRecover）
              复用时避免误落"替换"语义摘要。
        """
        # 获取对应集群相关对象
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
            spider_count = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=spider_role).count()
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
            )

        # 在做一下容灾级别检查，因为flow validator 只能做前置检验，这是没有申请到机器，所以只能在flow构建时判断
        # spider_slave角色不做容灾检查
        # 计算出剩余spider节点
        if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
            remaining_spiders = cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=spider_role
            ).exclude(machine__ip__in=[i["ip"] for i in old_spider_hosts])

            check_hosts = [
                {"ip": i.machine.ip, "sub_zone_id": i.machine.bk_sub_zone_id, "rack_id": i.machine.bk_rack_id}
                for i in remaining_spiders
            ]
            if len(new_spider_hosts + check_hosts) > 1:
                # 大于1做亲和性检测
                if not BaseValidator.check_disaster_tolerance_level(cluster, new_spider_hosts + check_hosts):
                    raise CheckDisasterToleranceException(
                        message=_(
                            "[{}]集群{}节点不满足容灾要求[{}]，请检查，替换后后预期节点信息:{}".format(
                                cluster.immute_domain,
                                spider_role,
                                cluster.disaster_tolerance_level,
                                new_spider_hosts + check_hosts,
                            )
                        )
                    )

        sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_context)

        # 执行扩容实例
        # 注意：内部调用不透传 is_print_summary，走默认 False——避免在替换语义下额外落
        # "ADD" 摘要行；本方法尾部会统一挂载 SWITCH 摘要（包含 related_instance 表达对端）。
        sub_pipeline.add_sub_pipeline(
            self.add_spider_nodes_with_cluster(
                cluster_id=cluster_id,
                add_spider_role=spider_role,
                add_spider_hosts=new_spider_hosts,
                is_check_disaster_tolerance_level=False,
            )
        )

        # 释放对单据的互斥锁
        # 单据类型：TenDBCLuster的SQL变更/强制变更/模拟执行/授权
        sub_pipeline.add_act(
            act_name=_("释放部分单据互斥锁"),
            act_component_code=AddUnlockTicketTypeConfigComponent.code,
            kwargs=asdict(
                AddUnLockTicketTypeKwargs(
                    cluster_ids=[cluster_id], unlock_ticket_type_list=self.temporary_unlock_ticket_type_list
                )
            ),
        )

        # 人工确认前，解除释放互斥锁，重新互斥
        if not disable_manual_confirm:
            sub_pipeline.add_act(
                act_name=_("人工确认，解除释放，重新判断互斥条件"),
                act_component_code=PauseWithTicketLockCheckComponent.code,
                kwargs=asdict(
                    ReleaseUnLockTicketTypeKwargs(
                        cluster_ids=[cluster_id],
                        release_unlock_ticket_type_list=self.temporary_unlock_ticket_type_list,
                    )
                ),
            )

        # 执行缩容实例
        # 注意：同上，内部调用不透传 is_print_summary，避免额外落 "REDUCE" 摘要行。
        sub_pipeline.add_sub_pipeline(
            self.reduce_spider_nodes_with_cluster(
                cluster_id=cluster_id,
                spider_reduced_hosts=old_spider_hosts,
                reduce_spider_role=spider_role,
                spider_reduced_to_count_snapshot=spider_count - len(old_spider_hosts),
                is_check_min_count=False,
                is_check_disaster_tolerance_level=False,
                is_check_process=self.data.get("is_safe", True),
                disable_manual_confirm=disable_manual_confirm,
            )
        )

        # 尾部（可选）写入spider变更摘要：必须放在 build_sub_process 之前才能追加进 pipeline。
        # items 必须在 flow 构建阶段就地装配完成——运行时 db_meta 里的旧实例会被清理，
        # 届时反查端口将失败。幂等由 InstanceChangeSummarySerializer.table_primary_key = "instance"
        # 保证：同 IP:Port 重复写入 → 后写覆盖前写。
        if is_print_summary:
            # spider_role 可能是枚举成员或枚举 value 字符串（历史调用点异构），统一归一为枚举成员
            role_enum: TenDBClusterSpiderRole = (
                spider_role if isinstance(spider_role, TenDBClusterSpiderRole) else TenDBClusterSpiderRole(spider_role)
            )
            sub_pipeline.add_act(
                act_name=_("写入spider变更摘要"),
                act_component_code=MysqlFlowOutputSummaryComponent.code,
                kwargs={
                    "preset": "instance_change",
                    "items": self._build_switch_items(cluster, role_enum, old_spider_hosts, new_spider_hosts),
                },
            )

        return sub_pipeline.build_sub_process(sub_name=_("[{}]替换spider节点流程".format(cluster.immute_domain)))

    def switch_spider_nodes(self):
        """
        定义TenDB Cluster替换接入层的后端流程
        """
        # 计算每个待加入节点的安装介质包
        self.calc_install_version_for_each_node()

        # 做转换
        global_data = self.trans_ticket_data()
        pipeline = Builder(root_id=self.root_id, data=global_data)

        # DB_HA 自愈复用了这个 flow, 需要禁用人工确认节点才能全自动化
        # 为了不影响已有单据, 增加一个 default = False 的控制变量
        disable_manual_confirm = self.data.get("disable_manual_confirm", False)

        sub_pipelines = []
        for info in global_data["infos"]:
            sub_pipelines.append(
                self.switch_nodes_flow_with_cluster(
                    cluster_id=info["cluster_id"],
                    spider_role=info["switch_spider_role"],
                    old_spider_hosts=info["spider_old_ip_list"],
                    new_spider_hosts=info["spider_new_ip_list"],
                    sub_flow_context={"uid": self.data["uid"]},
                    disable_manual_confirm=disable_manual_confirm,
                    # 仅"替换"单据顶层入口开启摘要写入；衍生 flow（Rebuild / Upgrade /
                    # DisasterRecover）不走此顶层入口，天然不会误落 SWITCH 摘要行。
                    # 变更规格（ChangeSpec）直接调 switch_spider_nodes，会跟着落 SWITCH 摘要——
                    # 属合理副作用："变更规格"本质就是"用新规格机替换旧规格机"。
                    is_print_summary=True,
                )
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # 启动接入单据值守监听
        pipeline.run_pipeline_with_sidecar(
            check_ai_monitor_cluster_list=[int(info["cluster_id"]) for info in self.data["infos"]],
            init_trans_data_class=SystemInfoContext(),
        )

    def revoke_flow(self):
        """
        定义TenDB Cluster替换接入层流程出现异常，终止的流程
        主要逻辑是根据单据终止后，哪些新机器可以进入主机退回流程中
        """
        revoke_pipeline = Builder(root_id=self.root_id, data=self.data)

        acts_list = []
        for info in self.data["infos"]:
            acts_list.append(
                {
                    "act_name": _("集群ID[{}]计算回收主机".format(info["cluster_id"])),
                    "act_component_code": CheckIfNormalSpiderNodeComponent.code,
                    "kwargs": asdict(
                        CheckIfNormalSpiderNodeComponent.kwargs(
                            cluster_id=info["cluster_id"],
                            spider_hosts=info["spider_new_ip_list"],
                            spider_role=info["switch_spider_role"],
                            resource_spec=info["resource_spec"],
                            created_by=self.data["created_by"],
                        )
                    ),
                }
            )

        revoke_pipeline.add_parallel_acts(acts_list=acts_list)
        revoke_pipeline.run_pipeline()
