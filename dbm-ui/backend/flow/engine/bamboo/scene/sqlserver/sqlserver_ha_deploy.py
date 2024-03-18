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

from backend.db_meta.enums import ClusterType
from backend.flow.consts import SqlserverSyncMode
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.engine.bamboo.scene.sqlserver.common_sub_flow import (
    build_always_on_sub_flow,
    install_sqlserver_sub_flow,
    install_surrounding_apps_sub_flow,
)
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import CreateDnsKwargs
from backend.flow.utils.sqlserver.base_func import calc_install_ports
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.validate import SqlserverCluster, SqlserverInstance

logger = logging.getLogger("flow")


class SqlserverHAApplyFlow(BaseFlow):
    """
    构建sqlserver-ha部署的抽象类
    兼容跨云区域的场景支持
    """

    def run_flow(self):
        """
        定义部署主从实例流程，支持多实例部署，支持多行并行部署，支持多云区域同时部署
        部署逻辑：
        1：机器空闲检测（可选）
        2：下发安装介质包
        3：安装实例
        3.1：部署AlwaysOn 可用组(可选，只有always on 集群部署)
        4：添加域名
        5：录入元数据、联动cmdb
        6：安装周边程序（可选）
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update({"master_ip": info["mssql_master_host"]["ip"]})
            sub_flow_context.update({"slave_ip": info["mssql_slave_host"]["ip"]})

            # 计算机器需要部署的sqlserver的端口列表，集群的依据：映射的cluster集群数量
            sub_flow_context["install_ports"] = calc_install_ports(len(info["clusters"]))

            clusters = []
            for number, cluster in enumerate(info["clusters"]):
                # 分配部署port、ip 、cluster的关系
                cluster["master_ip"] = info["mssql_master_host"]["ip"]
                cluster["slave_ip"] = info["mssql_slave_host"]["ip"]
                cluster["port"] = sub_flow_context["install_ports"][number]
                clusters.append(cluster)
            sub_flow_context["clusters"] = clusters

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 安装实例
            sub_pipeline.add_sub_pipeline(
                sub_flow=install_sqlserver_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    bk_biz_id=int(self.data["bk_biz_id"]),
                    bk_cloud_id=int(self.data["bk_cloud_id"]),
                    db_module_id=int(self.data["db_module_id"]),
                    install_ports=sub_flow_context["install_ports"],
                    clusters=[SqlserverCluster(**i) for i in sub_flow_context["clusters"]],
                    cluster_type=ClusterType.SqlserverHA,
                    target_hosts=[Host(**info["mssql_master_host"]), Host(**info["mssql_slave_host"])],
                    db_version=self.data["db_version"],
                )
            )
            # 集群维度
            # 配置alwaysOn 可用组
            # 添加域名
            act_list = []
            for cluster in sub_flow_context["clusters"]:
                # 以集群维度并发处理 集群内容：比如添加对应的域名
                # 拼接子流程需要全局参数
                cluster_sub_flow_context = copy.deepcopy(self.data)
                cluster_sub_flow_context.pop("infos")

                # 声明子流程
                cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(cluster_sub_flow_context))

                # 判断是否配置alwaysOn可用组
                if self.data["sync_type"] == SqlserverSyncMode.ALWAYS_ON:
                    cluster_sub_pipeline.add_sub_pipeline(
                        sub_flow=build_always_on_sub_flow(
                            uid=self.data["uid"],
                            root_id=self.root_id,
                            master_instance=SqlserverInstance(
                                host=info["mssql_master_host"]["ip"],
                                port=cluster["port"],
                                bk_cloud_id=self.data["bk_cloud_id"],
                                is_new=True,
                            ),
                            slave_instances=[
                                SqlserverInstance(
                                    host=info["mssql_slave_host"]["ip"],
                                    port=cluster["port"],
                                    bk_cloud_id=self.data["bk_cloud_id"],
                                    is_new=True,
                                )
                            ],
                            cluster_name=cluster["name"],
                            group_name=cluster["immutable_domain"],
                        )
                    )

                cluster_sub_pipeline.add_parallel_acts(
                    acts_list=[
                        {
                            "act_name": _("添加集群域名"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=self.data["bk_cloud_id"],
                                    add_domain_name=cluster["immutable_domain"],
                                    dns_op_exec_port=cluster["port"],
                                    exec_ip=info["mssql_master_host"]["ip"],
                                )
                            ),
                        },
                        {
                            "act_name": _("添加从集群域名"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=self.data["bk_cloud_id"],
                                    add_domain_name=cluster["slave_domain"],
                                    dns_op_exec_port=cluster["port"],
                                    exec_ip=info["mssql_slave_host"]["ip"],
                                )
                            ),
                        },
                    ]
                )
                act_list.append(
                    cluster_sub_pipeline.build_sub_process(sub_name=_("部署HA集群[{}]".format(cluster["name"])))
                )

            # 拼接集群维度的子流程
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=act_list)

            # 录入集群元数据，同组机器作为原子任务同时录入
            sub_pipeline.add_act(
                act_name=_("录入db_meta元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.sqlserver_ha_apply.__name__,
                    )
                ),
            )

            # 安装周边程序
            sub_pipeline.add_sub_pipeline(
                sub_flow=install_surrounding_apps_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    bk_biz_id=int(self.data["bk_biz_id"]),
                    bk_cloud_id=int(self.data["bk_cloud_id"]),
                    master_host=[Host(**info["mssql_master_host"])],
                    slave_host=[Host(**info["mssql_slave_host"])],
                )
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("部署主从集群")))

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
