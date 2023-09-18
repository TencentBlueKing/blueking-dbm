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

from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import reduce_spider_slaves_flow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.spider.drop_spider_ronting import DropSpiderRoutingComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DeleteClusterDnsKwargs
from backend.flow.utils.spider.spider_act_dataclass import DropSpiderRoutingKwargs
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class TenDBSlaveClusterDestroyFlow(object):
    """
    构建TenDB Cluster只读接入层的下架流程抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_slave_cluster_info(cluster_id: int) -> dict:
        """
        根据主机群id获取只读接入层相关信息
        @param cluster_id: 主机群的id
        """
        cluster = Cluster.objects.get(id=cluster_id)
        clusterentry = cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
        ).first()
        proxy_instances = ProxyInstance.objects.filter(bind_entry=clusterentry).all()

        return {
            "cluster_id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "slave_domain": clusterentry.entry,
            "spider_ip_list": list(set([instance.machine.ip for instance in proxy_instances])),
            "port": proxy_instances[0].port,
        }

    def destroy_slave_cluster(self):
        """
        定义spider只读接入层的下架流程
        支持多集群下架
        """
        spider_slave_destroy_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for cluster_id in self.data["cluster_ids"]:
            # 拼接子流程参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("cluster_ids")

            slave_cluster = self.__get_slave_cluster_info(cluster_id)
            sub_flow_context.update(slave_cluster)
            sub_flow_context["force"] = True
            sub_flow_context["reduce_spiders"] = [{"ip": inst} for inst in slave_cluster["spider_ip_list"]]
            # 子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 删除spider路由关系
            sub_pipeline.add_act(
                act_name=_("删除spider路由关系"),
                act_component_code=DropSpiderRoutingComponent.code,
                kwargs=asdict(
                    DropSpiderRoutingKwargs(
                        cluster_id=slave_cluster["cluster_id"],
                        is_safe=sub_flow_context["is_safe"],
                        reduce_spiders=sub_flow_context["reduce_spiders"],
                    )
                ),
            )

            # 删除对应的域名关系
            sub_pipeline.add_act(
                act_name=_("删除集群域名"),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    DeleteClusterDnsKwargs(
                        bk_cloud_id=slave_cluster["bk_cloud_id"],
                        delete_cluster_id=slave_cluster["cluster_id"],
                        is_only_delete_slave_domain=True,
                    ),
                ),
            )

            # 暂停节点，让用户在合适的时间执行下架
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

            # 根据场景执行下架spider子流程
            sub_pipeline.add_sub_pipeline(
                sub_flow=reduce_spider_slaves_flow(
                    cluster=Cluster.objects.get(id=slave_cluster["cluster_id"]),
                    reduce_spiders=sub_flow_context["reduce_spiders"],
                    root_id=self.root_id,
                    parent_global_data=sub_flow_context,
                    spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value,
                )
            )

            sub_pipeline.add_act(
                act_name=_("清理db_meta元信息"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.tendb_cluster_slave_destroy.__name__,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("只读接入层[{}]下架".format(slave_cluster["slave_domain"])))
            )
        spider_slave_destroy_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        spider_slave_destroy_pipeline.run_pipeline()
