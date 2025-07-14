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
from typing import Any, Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.spider_add_nodes import TenDBClusterAddNodesFlow
from backend.flow.engine.bamboo.scene.spider.spider_reduce_nodes import TenDBClusterReduceNodesFlow
from backend.flow.engine.validate.base_validate import BaseValidator
from backend.flow.engine.validate.exceptions import CheckDisasterToleranceException
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext

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
                          {"ip":"x","bk_cloud_id": 0,"bk_host_id":3},
                          {"ip":"x","bk_cloud_id": 0,"bk_host_id":}
                        ],
                        "resource_spec": {"spider":{'id':1,'xxx':'xxx'}}
                      }
                ]

        }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        # 分别初始化父类的init方法
        super().__init__(root_id=root_id, data=data)
        super(TenDBClusterAddNodesFlow, self).__init__(root_id=root_id, data=data)

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
        resource_spec: dict,
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

        # 计算出剩余spider节点
        remaining_spiders = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=spider_role).exclude(
            machine__ip__in=[i["ip"] for i in old_spider_hosts]
        )

        check_hosts = [
            {"ip": i.machine.ip, "sub_zone_id": i.machine.bk_sub_zone_id, "rack_id": i.machine.bk_rack_id}
            for i in remaining_spiders
        ]
        if len(new_spider_hosts + check_hosts) > 1:
            # 大于1做亲和性检测
            if not BaseValidator.check_disaster_tolerance_level(cluster, new_spider_hosts + check_hosts):
                raise CheckDisasterToleranceException(
                    message=_(
                        "[{}]集群spider节点不满足容灾要求[{}]，请检查，替换后后预期节点信息:{}".format(
                            cluster.immute_domain, cluster.disaster_tolerance_level, new_spider_hosts + check_hosts
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
                resource_spec=resource_spec,
                is_check_disaster_tolerance_level=False,
            )
        )

        # 人工确认
        sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

        # 执行缩容实例
        sub_pipeline.add_sub_pipeline(
            self.reduce_spider_nodes_with_cluster(
                cluster_id=cluster_id,
                spider_reduced_hosts=old_spider_hosts,
                reduce_spider_role=spider_role,
                spider_reduced_to_count_snapshot=spider_count - len(old_spider_hosts),
                is_check_min_count=False,
                is_check_disaster_tolerance_level=False,
            )
        )
        return sub_pipeline.build_sub_process(sub_name=_("[{}]替换spider节点流程".format(cluster.immute_domain)))

    def switch_spider_nodes(self):
        """
        定义TenDB Cluster替换接入层的后端流程
        """
        # 做转换
        global_data = self.trans_ticket_data()
        pipeline = Builder(root_id=self.root_id, data=global_data)

        sub_pipelines = []
        for info in global_data["infos"]:
            sub_pipelines.append(
                self.switch_nodes_flow_with_cluster(
                    cluster_id=info["cluster_id"],
                    spider_role=info["switch_spider_role"],
                    old_spider_hosts=info["spider_old_ip_list"],
                    new_spider_hosts=info["spider_new_ip_list"],
                    resource_spec=info.get("resource_spec", {}),
                    sub_flow_context={"uid": self.data["uid"]},
                )
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline(init_trans_data_class=SystemInfoContext())
