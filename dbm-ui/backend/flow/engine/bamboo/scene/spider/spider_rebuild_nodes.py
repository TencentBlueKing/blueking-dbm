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
from typing import Dict

from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.spider_switch_nodes import TenDBClusterSwitchNodesFlow
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class TenDBClusterRebuildNodesFlow(TenDBClusterSwitchNodesFlow):
    """
    基于扩容spider实例和缩容spider实例的flow的基类，定义spider节点重建的flow

    重建场景说明：
        所谓“重建 spider 节点”，是指在不改变集群元数据（DB_META、DNS、路由关系等）
        的前提下，对指定 spider 实例所在机器进行重新部署。常见用于机器异常后在原机
        器或等价机器上原地恢复 spider 进程与配置。

    重建流程的整体步骤：
        1：检查业务链接（CheckClientConnComponent），确认待重建节点上没有活跃连接
        2：下架 spider 节点（只做物理卸载，不处理元数据 / DNS / 路由）
        3：上架 spider 节点（在原机器上复装 spider，不处理元数据）

    ticket_data参数（与 switch 单据风格对齐）：
        {
          "uid": "1",
          "created_by": "xxx",
          "bk_biz_id": "1",
          "ticket_type": "TENDBCLUSTER_SPIDER_REBUILD_NODES",
          "infos": [
                      {
                        "cluster_id": 1,
                        "rebuild_spider_role": "spider_master",
                        "spider_ip_list":  [
                          {"ip":"x","bk_cloud_id": 0,"bk_host_id":1},
                          {"ip":"x","bk_cloud_id": 0,"bk_host_id":2}
                        ]
                      }
                ]
        }
    """

    def calc_install_version_for_each_node(self):
        """
        计算每个待重建的spider节点，需要安装的版本介质包信息
        """
        for info in self.data["infos"]:
            for index, rebuild_spider in enumerate(info["spider_ip_list"]):
                rebuild_spider["pkg_id"] = self.get_spider_pkg_id_for_tmp_spider_ip(
                    cluster_id=info["cluster_id"], tmp_spider_ip=info["spider_ip_list"][index]["ip"]
                )

    def trans_ticket_data(self) -> Dict:
        """
        根据SaaS传入ticket_data进行转换，按cluster_id聚合重建节点，避免单个集群产生多个子流程
        """
        cluster_map = {}
        for info in self.data["infos"]:
            cluster_id = info["cluster_id"]
            if cluster_id not in cluster_map:
                cluster_map[cluster_id] = {
                    "base_info": info,
                    "spider_ip_list": list(info["spider_ip_list"]),
                }
            else:
                cluster_map[cluster_id]["spider_ip_list"].extend(info["spider_ip_list"])

        new_infos = []
        for entry in cluster_map.values():
            new_entry = {
                **entry["base_info"],
                "spider_ip_list": entry["spider_ip_list"],
            }
            new_infos.append(new_entry)

        return {**self.data, "infos": new_infos}

    def rebuild_nodes_flow_with_cluster(
        self,
        cluster_id: int,
        spider_role: TenDBClusterSpiderRole,
        rebuild_spider_hosts: list,
    ):
        """
        根据集群维度，串行处理每个集群的 spider 重建流程
        步骤：
            1. 更改重建实例的状态为restoring
            2. 下架 spider 节点（不处理元数据）
            3. 上架 spider 节点（不处理元数据）
            4. 更改重建实例的状态为running
        """
        # 获取集群对象
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))
            spider_count = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=spider_role).count()
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
            )

        # 生成子流程
        sub_pipeline = SubBuilder(
            root_id=self.root_id,
            data={
                "uid": self.data["uid"],
                "bk_biz_id": self.data["bk_biz_id"],
                "created_by": self.data["created_by"],
                "ticket_type": self.data["ticket_type"],
            },
        )

        # 修改实例状态为restoring
        sub_pipeline.add_act(
            act_name=_("更新实例状态为restoring"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SpiderDBMeta.modify_spider_nodes_meta.__name__,
                    component_kwargs={
                        "cluster_id": cluster_id,
                        "spiders": rebuild_spider_hosts,
                        "op_status": InstanceStatus.RESTORING,
                    },
                )
            ),
        )

        # 先给待重建的spider节点做下架，不处理元数据
        sub_pipeline.add_sub_pipeline(
            self.reduce_spider_nodes_with_cluster(
                cluster_id=cluster_id,
                spider_reduced_hosts=rebuild_spider_hosts,
                reduce_spider_role=spider_role,
                spider_reduced_to_count_snapshot=spider_count - len(rebuild_spider_hosts),
                is_check_min_count=False,
                is_check_disaster_tolerance_level=False,
                is_check_process=self.data.get("is_check_process", True),
                is_rebuild=True,
            )
        )

        # 执行扩容实例, 不处理元数据
        sub_pipeline.add_sub_pipeline(
            self.add_spider_nodes_with_cluster(
                cluster_id=cluster_id,
                add_spider_role=spider_role,
                add_spider_hosts=rebuild_spider_hosts,
                is_check_disaster_tolerance_level=False,
                is_rebuild=True,
            )
        )

        # 修改实例状态为running
        sub_pipeline.add_act(
            act_name=_("更新实例状态为running"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SpiderDBMeta.modify_spider_nodes_meta.__name__,
                    component_kwargs={
                        "cluster_id": cluster_id,
                        "spiders": rebuild_spider_hosts,
                        "op_status": InstanceStatus.RUNNING,
                    },
                )
            ),
        )

        return sub_pipeline.build_sub_process(sub_name=_("[{}]重建spider节点流程".format(cluster.immute_domain)))

    def rebuild_spider_nodes(self):
        """
        定义 TenDB Cluster 重建接入层 spider 的后端主流程
        """
        # 计算每个spider的pkg_id
        self.calc_install_version_for_each_node()

        # 按 cluster_id 聚合 infos
        global_data = self.trans_ticket_data()

        pipeline = Builder(root_id=self.root_id, data=global_data)

        sub_pipelines = []
        for info in global_data["infos"]:
            sub_pipelines.append(
                self.rebuild_nodes_flow_with_cluster(
                    cluster_id=info["cluster_id"],
                    spider_role=info["rebuild_spider_role"],
                    rebuild_spider_hosts=info["spider_ip_list"],
                )
            )

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 暂时不启动接入单据值守监听
        pipeline.run_pipeline(init_trans_data_class=SystemInfoContext())
