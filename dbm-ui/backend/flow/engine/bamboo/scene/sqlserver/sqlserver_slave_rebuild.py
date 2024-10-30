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
from typing import List

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import SqlserverCleanMode, SqlserverLoginExecMode, SqlserverSyncMode, SqlserverSyncModeMaps
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.engine.bamboo.scene.sqlserver.common_sub_flow import (
    build_always_on_sub_flow,
    clone_configs_sub_flow,
    install_sqlserver_sub_flow,
    install_surrounding_apps_sub_flow,
    sync_dbs_for_cluster_sub_flow,
)
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_add_slave import SqlserverAddSlaveFlow
from backend.flow.plugins.components.collections.common.delete_cc_service_instance import DelCCServiceInstComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.sqlserver.create_random_job_user import SqlserverAddJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.drop_random_job_user import SqlserverDropJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.exec_sqlserver_login import ExecSqlserverLoginComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CreateDnsKwargs,
    DelServiceInstKwargs,
    IpDnsRecordRecycleKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    CreateRandomJobUserKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    DropRandomJobUserKwargs,
    ExecActuatorKwargs,
    ExecLoginKwargs,
    SqlserverBackupIDContext,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import (
    check_always_on_status,
    create_sqlserver_login_sid,
    get_dbs_for_drs,
    get_group_name,
    get_no_sync_dbs,
    get_restoring_dbs,
    get_sync_filter_dbs,
)
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.validate import SqlserverCluster, SqlserverInstance

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
            master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
            cluster_sync_mode = SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
            rebuild_slave = cluster.storageinstance_set.get(machine__ip=info["slave_host"]["ip"])
            sync_dbs = get_no_sync_dbs(cluster_id=cluster.id)

            # 拼接子流程全局上下文
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_flow_context["slaves"] = []
            sub_flow_context["sync_mode"] = SqlserverSyncModeMaps[
                SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
            ]
            sub_flow_context["clean_dbs"] = list(
                set(sync_dbs) | set(get_restoring_dbs(rebuild_slave, cluster.bk_cloud_id))
            )
            sub_flow_context["clean_mode"] = SqlserverCleanMode.DROP_DBS.value
            sub_flow_context["clean_tables"] = ["*"]
            sub_flow_context["ignore_clean_tables"] = []

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 创建随机账号
            sub_pipeline.add_act(
                act_name=_("create job user"),
                act_component_code=SqlserverAddJobUserComponent.code,
                kwargs=asdict(
                    CreateRandomJobUserKwargs(
                        cluster_ids=[cluster.id],
                        sid=create_sqlserver_login_sid(),
                    ),
                ),
            )

            if cluster_sync_mode == SqlserverSyncMode.ALWAYS_ON and not check_always_on_status(cluster, rebuild_slave):
                # 表示这个从实例和可用组端口连接，需要重建可用组关系
                sub_pipeline.add_act(
                    act_name=_("[{}]重建可用组".format(info["slave_host"]["ip"])),
                    act_component_code=SqlserverActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            exec_ips=[Host(ip=master.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                            get_payload_func=SqlserverActPayload.get_build_always_on.__name__,
                            custom_params={
                                "port": master.port,
                                "add_slaves": [{"host": rebuild_slave.machine.ip, "port": rebuild_slave.port}],
                                "group_name": get_group_name(master_instance=master, bk_cloud_id=cluster.bk_cloud_id),
                                "is_first": False,
                                "is_use_sa": False,
                            },
                        )
                    ),
                )
                # 更新清理数据库列表
                sub_flow_context["clean_dbs"] = list(
                    set(get_dbs_for_drs(cluster_id=cluster.id, db_list=["*"], ignore_db_list=[]))
                    | set(get_restoring_dbs(rebuild_slave, cluster.bk_cloud_id))
                )
                sync_dbs = get_dbs_for_drs(cluster_id=cluster.id, db_list=["*"], ignore_db_list=[])

            if len(sync_dbs) > 0:
                # 在slave重新建立数据库级别主从关系
                sub_pipeline.add_sub_pipeline(
                    sub_flow=sync_dbs_for_cluster_sub_flow(
                        uid=self.data["uid"],
                        root_id=self.root_id,
                        cluster=cluster,
                        sync_slaves=[Host(**info["slave_host"])],
                        sync_dbs=sync_dbs,
                        clean_dbs=sub_flow_context["clean_dbs"],
                    )
                )

            # 先做克隆周边配置
            sub_pipeline.add_sub_pipeline(
                sub_flow=clone_configs_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    source_host=Host(ip=master.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                    source_port=master.port,
                    target_host=Host(**info["slave_host"]),
                    target_port=sub_flow_context["port"],
                )
            )

            # 从域名修复的逻辑
            entry_list = rebuild_slave.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
            if len(entry_list) > 0:
                sub_lists = []
                for entry in entry_list:
                    sub_flow = self.fix_slave_dns_sub_flow(
                        domain_name=entry.entry,
                        master_instance=SqlserverInstance(
                            host=master.machine.ip, port=master.port, bk_cloud_id=master.machine.bk_cloud_id
                        ),
                        new_slave_instance=SqlserverInstance(
                            host=rebuild_slave.machine.ip,
                            port=rebuild_slave.port,
                            bk_cloud_id=rebuild_slave.machine.bk_cloud_id,
                        ),
                    )
                    if sub_flow:
                        sub_lists.append(sub_flow)

                if len(sub_lists) > 0:
                    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_lists)

            # 设置从为running状态
            sub_pipeline.add_act(
                act_name=_("实例设置running状态"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.rebuild_local_slave_state.__name__,
                    )
                ),
            )

            # 给slave部署周边程序
            sub_pipeline.add_sub_pipeline(
                sub_flow=install_surrounding_apps_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    bk_biz_id=int(self.data["bk_biz_id"]),
                    bk_cloud_id=int(cluster.bk_cloud_id),
                    master_host=[],
                    slave_host=[Host(**info["slave_host"])],
                    cluster_domain_list=[cluster.immute_domain],
                    is_install_backup_client=False,
                )
            )

            # 删除随机账号
            sub_pipeline.add_act(
                act_name=_("drop job user"),
                act_component_code=SqlserverDropJobUserComponent.code,
                kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id])),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("{}集群slave[{}:{}]原地重建".format(cluster.name, info["slave_host"]["ip"], info["port"]))
                )
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline(init_trans_data_class=SqlserverBackupIDContext())

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
            cluster = Cluster.objects.get(id=info["cluster_ids"][0])
            sub_flow_context["db_module_id"] = cluster.db_module_id
            sub_flow_context["db_version"] = cluster.major_version

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

            # 在新实例建立数据库级别同步关系, 替换域名，集群级别并发操作
            cluster_flows = []
            for cluster_id in info["cluster_ids"]:
                cluster = Cluster.objects.get(id=cluster_id)
                master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
                old_slave = cluster.storageinstance_set.get(machine__ip=info["old_slave_host"]["ip"])
                cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

                # 创建随机账号
                cluster_sub_pipeline.add_act(
                    act_name=_("create job user"),
                    act_component_code=SqlserverAddJobUserComponent.code,
                    kwargs=asdict(
                        CreateRandomJobUserKwargs(
                            cluster_ids=[cluster.id],
                            sid=create_sqlserver_login_sid(),
                            other_instances=[f"{info['new_slave_host']['ip']}:{old_slave.port}"],
                        ),
                    ),
                )

                # 如果是AlwaysOn集群，新机器加入到集群的AlwaysOn可用组
                if (
                    SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
                    == SqlserverSyncMode.ALWAYS_ON
                ):
                    master_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
                    slave_instances = cluster.storageinstance_set.filter(
                        instance_role=InstanceRole.BACKEND_SLAVE
                    ).exclude(machine__ip=info["old_slave_host"]["ip"])

                    # 计算集群slaves信息
                    slaves = [
                        SqlserverInstance(
                            host=s.machine.ip, port=s.port, bk_cloud_id=cluster.bk_cloud_id, is_new=False
                        )
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

                # 先做克隆周边配置
                cluster_sub_pipeline.add_sub_pipeline(
                    sub_flow=clone_configs_sub_flow(
                        uid=self.data["uid"],
                        root_id=self.root_id,
                        source_host=Host(ip=master.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                        source_port=master.port,
                        target_host=Host(**info["new_slave_host"]),
                        target_port=old_slave.port,
                    )
                )

                # 并发替换从域名映射
                entry_list = old_slave.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
                if len(entry_list) > 0:
                    sub_lists = []
                    for entry in entry_list:
                        sub_flow = self.fix_slave_dns_sub_flow(
                            domain_name=entry.entry,
                            master_instance=SqlserverInstance(
                                host=master.machine.ip, port=master.port, bk_cloud_id=master.machine.bk_cloud_id
                            ),
                            new_slave_instance=SqlserverInstance(
                                host=info["new_slave_host"]["ip"],
                                port=old_slave.port,
                                bk_cloud_id=int(info["new_slave_host"]["bk_cloud_id"]),
                            ),
                            old_slave_instance=SqlserverInstance(
                                host=old_slave.machine.ip,
                                port=old_slave.port,
                                bk_cloud_id=old_slave.machine.bk_cloud_id,
                            ),
                        )
                        if sub_flow:
                            sub_lists.append(sub_flow)

                    if len(sub_lists) > 0:
                        cluster_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_lists)

                # slave替换过程处理，移除可用组 disable账号、kill业务进程（Alwayson专属）
                if (
                    SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
                    == SqlserverSyncMode.ALWAYS_ON
                ):
                    cluster_sub_pipeline.add_sub_pipeline(
                        sub_flow=self.remote_slave_in_cluster(
                            cluster=cluster,
                            master_instance=master,
                            old_slave_instances=[old_slave],
                        )
                    )

                # 删除随机账号
                cluster_sub_pipeline.add_act(
                    act_name=_("drop job user"),
                    act_component_code=SqlserverDropJobUserComponent.code,
                    kwargs=asdict(
                        DropRandomJobUserKwargs(
                            cluster_ids=[cluster.id],
                            other_instances=[f"{info['new_slave_host']['ip']}:{old_slave.port}"],
                        ),
                    ),
                )

                cluster_flows.append(
                    cluster_sub_pipeline.build_sub_process(sub_name=_("[{}]集群与新slave建立关系".format(cluster.name)))
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_flows)

            # 添加新实例的维度信息
            sub_pipeline.add_act(
                act_name=_("变更元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.rebuild_in_new_slave.__name__,
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

            # 下架机器环节
            sub_pipeline.add_act(
                act_name=_("人工确认[{}]".format(info["old_slave_host"]["ip"])),
                act_component_code=PauseComponent.code,
                kwargs={},
            )

            # 删除服务实例
            acts_list = []
            for cluster_info in sub_flow_context["clusters"]:
                acts_list.append(
                    {
                        "act_name": _(
                            "删除注册CC系统的服务实例[{}:{}]".format(info["old_slave_host"]["ip"], cluster_info["port"])
                        ),
                        "act_component_code": DelCCServiceInstComponent.code,
                        "kwargs": asdict(
                            DelServiceInstKwargs(
                                cluster_id=cluster_info["cluster_id"],
                                del_instance_list=[{"ip": info["old_slave_host"]["ip"], "port": cluster_info["port"]}],
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

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
                        custom_params={"ports": sub_flow_context["install_ports"], "force": True, "is_use_sa": True},
                    ),
                ),
            )

            # 机器维度变更元数据
            sub_pipeline.add_act(
                act_name=_("回收旧slave的元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.reduce_slave.__name__,
                    )
                ),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("{}->{}新机重建".format(info["old_slave_host"]["ip"], info["new_slave_host"]["ip"]))
                )
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline(init_trans_data_class=SqlserverBackupIDContext())

    def fix_slave_dns_sub_flow(
        self,
        domain_name: str,
        master_instance: SqlserverInstance,
        new_slave_instance: SqlserverInstance,
        old_slave_instance: SqlserverInstance = None,
    ):
        """
        定义从库重建，修复域名的逻辑子流程
        处理逻辑：
        1：回收有可能主节点对域名的映射关系（主故障切换后残留下来）
        2：回收当前slave的域名映射关系（新机重建）
        3：对新的slave的域名关系添加
        """
        # 遍历所有域名映射记录
        acts_list = []
        is_new_slave_exist = False
        dns_manage = DnsManage(bk_biz_id=self.data["bk_biz_id"], bk_cloud_id=master_instance.bk_cloud_id)
        for row in dns_manage.get_domain(domain_name=domain_name):
            if row["ip"] == master_instance.host and row["port"] == master_instance.port:
                acts_list.append(
                    {
                        "act_name": _("回收master[{}]的域名映射".format(master_instance.host)),
                        "act_component_code": MySQLDnsManageComponent.code,
                        "kwargs": asdict(
                            IpDnsRecordRecycleKwargs(
                                instance_list=[f"{master_instance.host}#{master_instance.port}"],
                                bk_cloud_id=master_instance.bk_cloud_id,
                                domain_name=domain_name,
                            )
                        ),
                    },
                )

            if old_slave_instance and row["ip"] == old_slave_instance.host and row["port"] == old_slave_instance.port:
                acts_list.append(
                    {
                        "act_name": _("回收slave[{}]的域名映射".format(old_slave_instance.host)),
                        "act_component_code": MySQLDnsManageComponent.code,
                        "kwargs": asdict(
                            IpDnsRecordRecycleKwargs(
                                instance_list=[f"{old_slave_instance.host}#{old_slave_instance.port}"],
                                bk_cloud_id=old_slave_instance.bk_cloud_id,
                                domain_name=domain_name,
                            )
                        ),
                    },
                )

            if row["ip"] == new_slave_instance.host and row["port"] == new_slave_instance.port:
                is_new_slave_exist = True

        if not is_new_slave_exist:
            acts_list.append(
                {
                    "act_name": _("添加slave[{}]的域名映射".format(new_slave_instance.host)),
                    "act_component_code": MySQLDnsManageComponent.code,
                    "kwargs": asdict(
                        CreateDnsKwargs(
                            dns_op_exec_port=new_slave_instance.port,
                            exec_ip=new_slave_instance.host,
                            bk_cloud_id=new_slave_instance.bk_cloud_id,
                            add_domain_name=domain_name,
                        )
                    ),
                },
            )

        if len(acts_list) == 0:
            return None

        sub_pipeline = SubBuilder(
            root_id=self.root_id, data={"bk_biz_id": self.data["bk_biz_id"], "uid": self.data["uid"]}
        )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

        return sub_pipeline.build_sub_process(sub_name=_("处理[{}]的域名关系".format(domain_name)))

    def remote_slave_in_cluster(
        self,
        cluster: Cluster,
        master_instance: StorageInstance,
        old_slave_instances: List[StorageInstance],
    ):
        """
        移除可用组，Alwayson架构专属
        @param cluster: 集群信息
        @param master_instance: master信息
        @param old_slave_instances: 待移除的slave信息列表
        """

        # 先禁用业务账号
        sub_pipeline = SubBuilder(
            root_id=self.root_id, data={"bk_biz_id": self.data["bk_biz_id"], "uid": self.data["uid"]}
        )
        acts_list = []
        for instance in old_slave_instances:
            acts_list.append(
                {
                    "act_name": _("[{}]禁用业务账号".format(instance.ip_port)),
                    "act_component_code": ExecSqlserverLoginComponent.code,
                    "kwargs": asdict(
                        ExecLoginKwargs(
                            cluster_id=cluster.id,
                            exec_mode=SqlserverLoginExecMode.DISABLE.value,
                            exec_ip=instance.machine.ip,
                        ),
                    ),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

        # 移除出可用组
        sub_pipeline.add_act(
            act_name=_("移除可用组"),
            act_component_code=SqlserverActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                    get_payload_func=SqlserverActPayload.get_remote_dr_payload.__name__,
                    custom_params={
                        "port": master_instance.port,
                        "remotes_slaves": [{"host": i.machine.ip, "port": i.port} for i in old_slave_instances],
                    },
                )
            ),
        )
        return sub_pipeline.build_sub_process(sub_name=_("移除可用组[{}]".format(cluster.immute_domain)))
