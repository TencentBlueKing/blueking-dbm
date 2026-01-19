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
from typing import Any, Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
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
from backend.flow.plugins.components.collections.spider.check_if_normal_for_cluster import (
    CheckIfNormalSpiderNodeComponent,
)
from backend.flow.utils.base.base_dataclass import AddUnLockTicketTypeKwargs, ReleaseUnLockTicketTypeKwargs
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

    def switch_nodes_flow_with_cluster(
        self,
        cluster_id: int,
        spider_role: TenDBClusterSpiderRole,
        old_spider_hosts: list,
        new_spider_hosts: list,
        sub_flow_context: dict,
        disable_manual_confirm: bool = False,
    ):
        """
        根据集群维度，并发处理每个集群的替换节点信息
        流程步骤：
        1：给集群先添加新的spider实例
        2：人工确认
        3：给集群指定的spider实例下架
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
        sub_pipeline.add_sub_pipeline(
            self.reduce_spider_nodes_with_cluster(
                cluster_id=cluster_id,
                spider_reduced_hosts=old_spider_hosts,
                reduce_spider_role=spider_role,
                spider_reduced_to_count_snapshot=spider_count - len(old_spider_hosts),
                is_check_min_count=False,
                is_check_disaster_tolerance_level=False,
                is_check_process=self.data.get("is_check_process", True),
                disable_manual_confirm=disable_manual_confirm,
            )
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
                )
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # pipeline.run_pipeline(init_trans_data_class=SystemInfoContext())
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
