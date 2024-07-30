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

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.engine.bamboo.scene.sqlserver.common_sub_flow import (
    build_always_on_sub_flow,
    install_sqlserver_sub_flow,
    install_surrounding_apps_sub_flow,
    sync_dbs_for_cluster_sub_flow,
)
from backend.flow.plugins.components.collections.sqlserver.create_random_job_user import SqlserverAddJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.drop_random_job_user import SqlserverDropJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    CreateRandomJobUserKwargs,
    DBMetaOPKwargs,
    DropRandomJobUserKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_db_function import (
    create_sqlserver_login_sid,
    get_dbs_for_drs,
    get_group_name,
    get_sync_filter_dbs,
)
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.validate import SqlserverCluster, SqlserverInstance

logger = logging.getLogger("flow")


class SqlserverAddSlaveFlow(BaseFlow):
    """
    构建sqlserver添加slave的抽象类
    兼容跨云区域的场景支持
    只支持AlwaysOn 集群
    """

    @staticmethod
    def get_clusters_install_info(cluster_ids) -> list:
        """
        根据传入cluster集群id列表，输出每个集群端口、域名信息返回
        @param cluster_ids: 集群id列表
        """
        clusters = []
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            port = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER).port
            # 分配部署port、cluster的关系
            clusters.append({"cluster_id": cluster_id, "port": port, "immutable_domain": cluster.immute_domain})
        return clusters

    def run_flow(self):
        """
        定义添加slave实例流程，支持单机多实例部署模式。
        流程逻辑：
        1: 下发安装包给新的slave
        2: 在新的slave安装对应实例
        3: 加入到AlwaysOn可用组
        4: 新slave同步数据
        5: 变更元数据信息
        """

        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)

            # 计算新机器部署端口，以及每个端口和集群的关系
            sub_flow_context["clusters"] = SqlserverAddSlaveFlow.get_clusters_install_info(info["cluster_ids"])
            sub_flow_context["install_ports"] = [i["port"] for i in sub_flow_context["clusters"]]

            # 已第一集群id的db_module_id/db_version 作为本次的安装依据，因为平台上同机相关联的集群的模块id/主版本都是一致的
            cluster = Cluster.objects.get(id=info["cluster_ids"][0])
            sub_flow_context["db_module_id"] = cluster.db_module_id
            sub_flow_context["db_version"] = cluster.major_version
            sub_flow_context["is_first"] = False

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 根据关联的集群，安装实例
            sub_pipeline.add_sub_pipeline(
                sub_flow=install_sqlserver_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    bk_biz_id=int(self.data["bk_biz_id"]),
                    bk_cloud_id=int(cluster.bk_cloud_id),
                    db_module_id=sub_flow_context["db_module_id"],
                    install_ports=sub_flow_context["install_ports"],
                    clusters=[SqlserverCluster(**i) for i in sub_flow_context["clusters"]],
                    cluster_type=ClusterType.SqlserverHA,
                    target_hosts=[Host(**info["new_slave_host"])],
                    db_version=sub_flow_context["db_version"],
                )
            )

            # 对应的新slave实例加入到集群的AlwaysOn可用组, 并且同步数据
            cluster_flows = []
            for cluster_id in info["cluster_ids"]:
                cluster = Cluster.objects.get(id=cluster_id)
                master_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
                slave_instances = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_SLAVE)
                cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

                # 计算集群slaves信息
                slaves = [
                    SqlserverInstance(host=s.machine.ip, port=s.port, bk_cloud_id=cluster.bk_cloud_id, is_new=False)
                    for s in slave_instances
                ]

                # 添加新slave到slaves信息上
                slaves.append(
                    SqlserverInstance(
                        host=info["new_slave_host"]["ip"],
                        port=master_instance.port,
                        bk_cloud_id=cluster.bk_cloud_id,
                        is_new=True,
                    )
                )

                # 创建随机账号
                cluster_sub_pipeline.add_act(
                    act_name=_("create job user"),
                    act_component_code=SqlserverAddJobUserComponent.code,
                    kwargs=asdict(
                        CreateRandomJobUserKwargs(
                            cluster_ids=[cluster.id],
                            sid=create_sqlserver_login_sid(),
                            other_instances=[f"{info['new_slave_host']['ip']}:{master_instance.port}"],
                        ),
                    ),
                )

                # 加入到集群的AlwaysOn可用组
                cluster_sub_pipeline.add_sub_pipeline(
                    sub_flow=build_always_on_sub_flow(
                        uid=self.data["uid"],
                        root_id=self.root_id,
                        master_instance=SqlserverInstance(
                            host=master_instance.machine.ip,
                            port=master_instance.port,
                            bk_cloud_id=cluster.bk_cloud_id,
                            is_new=False,
                        ),
                        slave_instances=slaves,
                        cluster_name=cluster.name,
                        group_name=get_group_name(master_instance, cluster.bk_cloud_id),
                    )
                )

                # 数据库建立新的同步关系
                sync_dbs = list(
                    set(get_dbs_for_drs(cluster_id=cluster.id, db_list=["*"], ignore_db_list=[]))
                    - set(get_sync_filter_dbs(cluster.id))
                )
                if len(sync_dbs) > 0:
                    cluster_sub_pipeline.add_sub_pipeline(
                        sub_flow=sync_dbs_for_cluster_sub_flow(
                            uid=self.data["uid"],
                            root_id=self.root_id,
                            cluster=cluster,
                            sync_slaves=[Host(**info["new_slave_host"])],
                            sync_dbs=sync_dbs,
                        )
                    )

                # 删除随机账号
                cluster_sub_pipeline.add_act(
                    act_name=_("drop job user"),
                    act_component_code=SqlserverDropJobUserComponent.code,
                    kwargs=asdict(
                        DropRandomJobUserKwargs(
                            cluster_ids=[cluster.id],
                            other_instances=[f"{info['new_slave_host']['ip']}:{master_instance.port}"],
                        ),
                    ),
                )

                cluster_flows.append(
                    cluster_sub_pipeline.build_sub_process(sub_name=_("[{}]集群与新slave建立关系".format(cluster.name)))
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_flows)

            # 变更元数据
            sub_pipeline.add_act(
                act_name=_("变更元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.add_slave.__name__,
                    )
                ),
            )

            # 机器维度，给新机器部署周边程序
            sub_pipeline.add_sub_pipeline(
                sub_flow=install_surrounding_apps_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    bk_biz_id=int(self.data["bk_biz_id"]),
                    bk_cloud_id=int(cluster.bk_cloud_id),
                    master_host=[],
                    slave_host=[Host(**info["new_slave_host"])],
                    cluster_domain_list=[c["immutable_domain"] for c in sub_flow_context["clusters"]],
                )
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("添加slave[{}]".format(info["new_slave_host"]["ip"])))
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
