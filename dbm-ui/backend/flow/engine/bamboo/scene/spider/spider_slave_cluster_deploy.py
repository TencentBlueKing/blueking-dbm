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

from backend.configuration.constants import DBType
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import add_spider_slaves_sub_flow
from backend.flow.plugins.components.collections.mysql.mysql_cluster_apply_summary import (
    MysqlClusterApplySummaryComponent,
)
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class TenDBSlaveClusterApplyFlow(object):
    """
    构建spider slave 集群添加流程抽象类
    支持不同云区域的db集群合并操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def _build_apply_summary_clusters(self) -> List[Dict[str, Any]]:
        """基于 ticket_data(``self.data``) 拼装 TenDBCluster slave 集群交付摘要的集群定位信息。

        设计要点 / 怎么做：
          - 单据支持多集群并行部署 slave 接入层，本方法遍历 ``self.data["infos"]`` 产出每集群一条
            定位信息：`{bk_biz_id, cluster_domain=Cluster.immute_domain}`。
          - 摘要行的所有字段（access_port / CLB / **只读入口 readonly_domain_and_port** 等）由
            :class:`MysqlClusterApplySummaryComponent` 在运行时从 db_meta 反查装配；本单据的
            用户核心诉求"新增只读入口"由该组件通过 SLAVE_ENTRY 反查自动呈现。
          - ``cluster_domain`` 从 db_meta 反查（``Cluster.immute_domain``），不依赖 SaaS 单据
            额外传入字段，避免与单据契约耦合。

        :return: 与 ``self.data["infos"]`` 长度一致的集群定位信息列表；每项含 ``bk_biz_id`` 与
                 ``cluster_domain``。

        边界 / 异常：
          - 某 ``info["cluster_id"]`` 在 db_meta 不存在 -> 该行跳过，不阻塞主流程摘要写入；
            主流程 ``deploy_slave_cluster`` 循环内的 ``Cluster.objects.get`` 会在此之前抛
            :class:`ClusterNotExistException`，属兜底防御。
        """
        bk_biz_id: int = int(self.data["bk_biz_id"])
        cluster_ids: List[int] = [int(info["cluster_id"]) for info in self.data["infos"]]
        # 一次性反查涉及集群，避免 N+1 查询
        cluster_map: Dict[int, Cluster] = {
            c.id: c for c in Cluster.objects.filter(id__in=cluster_ids, bk_biz_id=bk_biz_id)
        }
        clusters: List[Dict[str, Any]] = []
        for cluster_id in cluster_ids:
            cluster: Optional[Cluster] = cluster_map.get(cluster_id)
            if cluster is None:
                # 主流程更早的 Cluster.objects.get 会先失败；此处纯兜底
                continue
            clusters.append(
                {
                    "bk_biz_id": bk_biz_id,
                    "cluster_domain": str(cluster.immute_domain),
                }
            )
        return clusters

    def deploy_slave_cluster(self):
        """
        定义spider slave集群部署流程
        目前产品形态 spider专属一套集群，所以流程只支持spider单机单实例安装
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        # 机器维度部署spider节点
        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")

            # 拼接子流程的全局参数
            sub_flow_context.update(info)

            # 获取对应集群相关对象
            try:
                cluster = Cluster.objects.get(id=info["cluster_id"], bk_biz_id=int(self.data["bk_biz_id"]))
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=info["cluster_id"], bk_biz_id=int(self.data["bk_biz_id"]), message=_("集群不存在")
                )

            # 根据集群去bk-config获取对应spider版本
            __, spider_major_version = get_spider_version_and_charset(
                bk_biz_id=cluster.bk_biz_id, db_module_id=cluster.db_module_id
            )

            # spider slave 不安装备份程序，只解压
            sub_flow_context["untar_only"] = True

            # 第一次安装，获取db模块的推荐版本，作为这边安装介质包
            sub_flow_context["global_pkg_id"] = Package.get_latest_package(
                version=spider_major_version, pkg_type=MediumEnum.Spider, db_type=DBType.MySQL
            ).id

            # 启动子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 阶段1 按照spider-slave实例
            sub_pipeline.add_sub_pipeline(
                sub_flow=add_spider_slaves_sub_flow(
                    cluster=cluster,
                    add_spider_slaves=info["spider_slave_ip_list"],
                    root_id=self.root_id,
                    uid=self.data["uid"],
                    parent_global_data=copy.deepcopy(sub_flow_context),
                    slave_domain=info["slave_domain"],
                    is_clone_user=False,
                    global_pkg_id=sub_flow_context["global_pkg_id"],
                )
            )

            # 阶段2 添加元数据
            sub_pipeline.add_act(
                act_name=_("更新DBMeta元信息"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=SpiderDBMeta.tendb_cluster_slave_apply.__name__)),
            )

            sub_pipeline.add_sub_pipeline(
                sub_flow=standardize_mysql_cluster_subflow(
                    bk_cloud_id=cluster.bk_cloud_id,
                    bk_biz_id=cluster.bk_biz_id,
                    instances=[
                        "{}:{}".format(spider["ip"], cluster.proxyinstance_set.first().port)
                        for spider in sub_flow_context["spider_slave_ip_list"]
                    ],
                    root_id=self.root_id,
                    data=copy.deepcopy(sub_flow_context),
                    with_actuator=False,
                    with_collect_sysinfo=False,
                    with_instance_standardize=False,
                    with_bk_plugin=False,
                    with_backup_client=True,
                )
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]添加slave集群".format(cluster.name))))

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 写入集群交付摘要：db_meta 已由每个 info 子流程内的"更新DBMeta元信息"节点写入，
        # 本节点位于 add_parallel_sub_pipeline 之后，此时所有涉及集群的只读入口(SLAVE_ENTRY)
        # 元数据均已就绪；只需传集群定位信息，readonly_domain_and_port / CLB 等运行时字段由
        # Component 从 db_meta 反查装配。幂等由
        # ClusterApplySummarySerializer.table_primary_key = "cluster_domain_and_port" 保证。
        pipeline.add_act(
            act_name=_("写入集群交付摘要"),
            act_component_code=MysqlClusterApplySummaryComponent.code,
            kwargs={"clusters": self._build_apply_summary_clusters()},
            is_remote_rewritable=True,
        )

        pipeline.run_pipeline(init_trans_data_class=SystemInfoContext())
