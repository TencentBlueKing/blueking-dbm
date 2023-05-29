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
import logging
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import reduce_spider_slaves_flow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.spider.drop_spider_ronting import DropSpiderRoutingComponent
from backend.flow.utils.mysql.mysql_act_dataclass import RecycleDnsRecordKwargs
from backend.flow.utils.spider.spider_act_dataclass import DropSpiderRoutingKwargs

logger = logging.getLogger("flow")


class TenDBClusterReduceMNTFlow(object):
    """
    减少运维节点（临时节点下架）
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id: 任务流程定义的root_id
        @param data: 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def reduce_spider_mnt(self):
        """
        定义运维节点下架后端流程
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = [i["cluster_id"] for i in self.data["infos"]]
        pipeline = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids)))

        sub_pipelines = []
        for info in self.data["infos"]:
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)

            # 这里后面看下reduce_spider_nodes怎么改
            sub_flow_context["force"] = True

            cluster = Cluster.objects.get(id=info["cluster_id"])
            reduce_spiders = info["spider_ip_list"]
            sub_flow_context["reduce_spiders"] = reduce_spiders

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
                    spider_role=TenDBClusterSpiderRole.SPIDER_MNT.value,
                )
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]下架spider运维节点流程".format(cluster.name))))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline(is_drop_random_user=True)
