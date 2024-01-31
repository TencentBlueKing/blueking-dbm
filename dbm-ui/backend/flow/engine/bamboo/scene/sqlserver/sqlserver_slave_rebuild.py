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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import SqlserverCleanMode, SqlserverSyncModeMaps
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.engine.bamboo.scene.sqlserver.common_sub_flow import (
    install_sqlserver_sub_flow,
    sync_dbs_for_cluster_sub_flow,
)
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_add_slave import SqlserverAddSlaveFlow
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.mysql.mysql_act_dataclass import UpdateDnsRecordKwargs
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import get_dbs_for_drs
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.validate import SqlserverCluster

logger = logging.getLogger("flow")


class SqlserverSlaveRebuildFlow(BaseFlow):
    """
    构建Sqlserver集群从库重建的流程类
    兼容跨云集群的执行
    从库重建的场景分为两种：
    1: 原地重建 rebuild_in_local     (实例行为)
    2: 新记重建 rebuild_in_new_slave (整机行为)
    """

    def slave_rebuild_in_local_flow(self):
        """
        原地重建子流程
        流程逻辑：
        1: 清理slave实例的所有库
        2: 建立数据库级别主从关系
        """

        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            cluster = Cluster.objects.get(id=info["cluster_id"])

            # 拼接子流程全局上下文
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_flow_context["slaves"] = []
            sub_flow_context["sync_mode"] = SqlserverSyncModeMaps[
                SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
            ]
            sub_flow_context["clean_dbs"] = get_dbs_for_drs(cluster_id=cluster.id, db_list=["*"], ignore_db_list=[])
            sub_flow_context["clean_mode"] = SqlserverCleanMode.DROP_DBS.value
            sub_flow_context["clean_tables"] = ["*"]
            sub_flow_context["ignore_clean_tables"] = []

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 下发执行器
            sub_pipeline.add_act(
                act_name=_("下发执行器"),
                act_component_code=TransFileInWindowsComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        target_hosts=[Host(**info["slave_host"])],
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )

            # 在slave清理业务数据库
            sub_pipeline.add_act(
                act_name=_("清理slave实例数据库"),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(**info["slave_host"])],
                        get_payload_func=SqlserverActPayload.get_clean_dbs_payload.__name__,
                    )
                ),
            )

            # 在slave重新建立数据库级别主从关系
            sub_pipeline.add_sub_pipeline(
                sub_flow=sync_dbs_for_cluster_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster,
                    sync_slaves=[Host(**info["slave_host"])],
                    sync_dbs=sub_flow_context["clean_dbs"],
                )
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("{}集群slave[{}:{}]原地重建".format(cluster.name, info["slave_host"]["ip"], info["port"]))
                )
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()

    def slave_rebuild_in_new_slave_flow(self):
        """
        新机重建子流程
        流程逻辑
        1: 安装新实例
        2: 在新实例建立数据库级别同步关系
        3: 域名顶替
        4: 卸载旧实例
        5: 更新元数据
        """

        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:

            # 拼接子流程全局上下文
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)

            # 计算新机器部署端口，以及每个端口和集群的关系
            sub_flow_context["clusters"] = SqlserverAddSlaveFlow.get_clusters_install_info(info["cluster_ids"])
            sub_flow_context["install_ports"] = [i["port"] for i in sub_flow_context["clusters"]]

            # 已第一集群id的db_module_id/db_version 作为本次的安装依据，因为平台上同机相关联的集群的模块id/主版本都是一致的
            sub_flow_context["db_module_id"] = Cluster.objects.get(id=info["cluster_ids"][0]).db_module_id
            sub_flow_context["db_version"] = Cluster.objects.get(id=info["cluster_ids"][0]).major_version

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 根据关联的集群，安装实例
            sub_pipeline.add_sub_pipeline(
                sub_flow=install_sqlserver_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    bk_biz_id=int(self.data["bk_biz_id"]),
                    db_module_id=sub_flow_context["db_module_id"],
                    install_ports=sub_flow_context["install_ports"],
                    clusters=[SqlserverCluster(**i) for i in sub_flow_context["clusters"]],
                    cluster_type=ClusterType.SqlserverHA,
                    target_hosts=[Host(**info["new_slave_host"])],
                    db_version=sub_flow_context["db_version"],
                )
            )

            # 在新实例建立数据库级别同步关系, 替换域名，集群级别并发操作
            cluster_flows = []
            for cluster_id in info["cluster_ids"]:
                cluster = Cluster.objects.get(id=cluster_id)
                old_slave = cluster.storageinstance_set.get(machine__ip=info["old_slave_host"]["ip"])
                cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

                # 数据库建立新的同步关系
                cluster_sub_pipeline.add_sub_pipeline(
                    sub_flow=sync_dbs_for_cluster_sub_flow(
                        uid=self.data["uid"],
                        root_id=self.root_id,
                        cluster=cluster,
                        sync_slaves=[Host(**info["new_slave_host"])],
                        sync_dbs=get_dbs_for_drs(cluster_id=cluster.id, db_list=["*"], ignore_db_list=[]),
                    )
                )

                # 并发替换从域名映射
                entry_list = old_slave.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
                if len(entry_list):
                    acts_list = []
                    for entry in entry_list:
                        acts_list.append(
                            {
                                "act_name": _("替换域名映射[{}]".format(entry.entry)),
                                "act_component_code": MySQLDnsManageComponent.code,
                                "kwargs": asdict(
                                    UpdateDnsRecordKwargs(
                                        bk_cloud_id=cluster.bk_cloud_id,
                                        old_instance=f"{info['old_slave_host']['ip']}#{old_slave.port}",
                                        new_instance=f"{info['new_slave_host']['ip']}#{old_slave.port}",
                                        update_domain_name=entry.entry,
                                    ),
                                ),
                            }
                        )
                    cluster_sub_pipeline.add_parallel_acts(acts_list=acts_list)

                cluster_flows.append(
                    cluster_sub_pipeline.build_sub_process(sub_name=_("[{}]集群与新slave建立关系".format(cluster.name)))
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_flows)

            # 下架机器环节
            # 给旧slave下发执行器
            sub_pipeline.add_act(
                act_name=_("下发执行器在旧slave[{}]".format(info["old_slave_host"]["ip"])),
                act_component_code=TransFileInWindowsComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        target_hosts=[Host(**info["old_slave_host"])],
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )

            # 卸载实例
            sub_pipeline.add_act(
                act_name=_("卸载实例[{}]".format(info["old_slave_host"]["ip"])),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(**info["old_slave_host"])],
                        get_payload_func=SqlserverActPayload.uninstall_sqlserver.__name__,
                        custom_params={"ports": sub_flow_context["install_ports"]},
                    ),
                ),
            )

            # 机器维度变更元数据
            sub_pipeline.add_act(
                act_name=_("变更元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.rebuild_in_new_slave.__name__,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("{}->{}新机重建".format(info["old_slave_host"]["ip"], info["new_slave_host"]["ip"]))
                )
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
