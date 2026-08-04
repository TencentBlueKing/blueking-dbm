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
from typing import List, Optional

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, ClusterType, InstanceRole
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import SqlserverSyncMode, SqlserverSyncModeMaps
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.engine.bamboo.scene.sqlserver.common.exceptions import MigrateFlowException
from backend.flow.engine.bamboo.scene.sqlserver.common_sub_flow import (
    build_always_on_sub_flow,
    clone_configs_sub_flow,
    init_machine_sub_flow,
    install_sqlserver_sub_flow,
    install_surrounding_apps_sub_flow,
    migrate_domain_for_cluster_ha,
    migrate_domain_for_cluster_single,
    switch_cluster_sub_flow,
    switch_domain_sub_flow_for_cluster,
    sync_dbs_for_cluster_sub_flow,
)
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_add_slave import SqlserverAddSlaveFlow
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_slave_rebuild import SqlserverSlaveRebuildFlow
from backend.flow.plugins.components.collections.common.calc_hosts_is_write_recycle_list import (
    CalcHostIsWriteRecycleListComponent,
)
from backend.flow.plugins.components.collections.common.delete_cc_service_instance import DelCCServiceInstComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.sqlserver.copy_app_setting import CopyAppSettingComponent
from backend.flow.plugins.components.collections.sqlserver.create_random_job_user import SqlserverAddJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.drop_random_job_user import SqlserverDropJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.remove_mirroring_config import (
    RemoveMirroringConfigComponent,
)
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DelServiceInstKwargs
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    CreateRandomJobUserKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    DropRandomJobUserKwargs,
    ExecActuatorKwargs,
    SqlserverBackupIDContext,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import (
    create_sqlserver_login_sid,
    get_dbs_for_drs,
    get_group_name,
    get_sync_filter_dbs,
)
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.flow.utils.sqlserver.validate import SqlserverInstance

logger = logging.getLogger("flow")


class SqlserverClusterMigrateFlow(BaseFlow):
    """
    构建Sqlserver集群迁移的流程类
    兼容跨云集群的执行
    同时支持单节点和主从集群的迁移逻辑
    """

    def remove_old_instance_sub_flow(
        self, cluster_ids: List[int], old_hosts: List[Host], cluster_type: ClusterType
    ) -> Optional[SubProcess]:
        """
        回收集群迁移后的旧实例的子流程
        单节点集群，回收迁移前的orphan角色实例
        主从集群，回收迁移前master实例，和is_stand_by=true的slave实例
        @param cluster_ids: 待处理的集群ID列表
        @param old_hosts: 待回收的旧集群
        @param cluster_type: 集群类型
        """

        # 声明子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

        # 按照集群ID隔离，并发删除服务实例
        acts_list = []
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            sqlserver_port = cluster.storageinstance_set.first().port
            acts_list.append(
                {
                    "act_name": _("删除注册CC系统的服务实例"),
                    "act_component_code": DelCCServiceInstComponent.code,
                    "kwargs": asdict(
                        DelServiceInstKwargs(
                            cluster_id=cluster_id,
                            del_instance_list=[{"ip": i.ip, "port": sqlserver_port} for i in old_hosts],
                        )
                    ),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

        # 下发执行器
        sub_pipeline.add_act(
            act_name=_("下发执行器"),
            act_component_code=TransFileInWindowsComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    target_hosts=old_hosts,
                    file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                ),
            ),
        )

        # 并发卸载实例
        acts_list = []
        # 计算需要下架的端口信息
        sqlserver_ports = []
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            sqlserver_ports.append(cluster.storageinstance_set.first().port)

        for host in old_hosts:
            acts_list.append(
                {
                    "act_name": _("卸载实例[{}]".format(host.ip)),
                    "act_component_code": SqlserverActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            exec_ips=[Host(ip=host.ip, bk_cloud_id=host.bk_cloud_id)],
                            get_payload_func=SqlserverActPayload.uninstall_sqlserver.__name__,
                            custom_params={"ports": sqlserver_ports, "force": True, "is_use_sa": True},
                        )
                    ),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

        # 清理实例级别的元数据
        sub_pipeline.add_act(
            act_name=_("清理实例元数据"),
            act_component_code=SqlserverDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SqlserverDBMeta.remove_instance_for_migrate.__name__,
                    component_kwargs={
                        "instances": [
                            {"ip": y.ip, "bk_cloud_id": y.bk_cloud_id, "port": x}
                            for x in sqlserver_ports
                            for y in old_hosts
                        ],
                        "cluster_type": cluster_type,
                        "bk_biz_id": self.data["bk_biz_id"],
                    },
                )
            ),
        )

        # 计算退回主机列表
        sub_pipeline.add_act(
            act_name=_("计算退回主机列表"),
            act_component_code=CalcHostIsWriteRecycleListComponent.code,
            kwargs=asdict(
                CalcHostIsWriteRecycleListComponent.kwargs(
                    ticket_id=self.data["uid"],
                    calc_host_list=old_hosts,
                )
            ),
        )

        return sub_pipeline.build_sub_process(sub_name=_("旧实例下架"))

    def add_slave_in_always_on_cluster_sub_flow(
        self,
        cluster: Cluster,
        master_instance: StorageInstance,
        new_master_host: Host,
        new_stand_by_host: Host,
    ) -> Optional[SubProcess]:
        """
        always_on集群添加slave节点的子流程
        """
        # 获取集群stand_by节点
        stand_by_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_SLAVE, is_stand_by=True)

        # 待替换的新机器，作为slave加入到集群的AlwaysOn可用组
        slaves = [
            SqlserverInstance(host=s.machine.ip, port=s.port, bk_cloud_id=cluster.bk_cloud_id, is_new=False)
            for s in cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_SLAVE)
        ] + [
            SqlserverInstance(host=n.ip, port=master_instance.port, bk_cloud_id=cluster.bk_cloud_id, is_new=True)
            for n in [new_master_host, new_stand_by_host]
        ]

        # 声明子流程
        add_nodes_sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

        # 创建随机账号
        add_nodes_sub_pipeline.add_act(
            act_name=_("create temp job account"),
            act_component_code=SqlserverAddJobUserComponent.code,
            kwargs=asdict(
                CreateRandomJobUserKwargs(
                    cluster_ids=[cluster.id],
                    sid=create_sqlserver_login_sid(),
                    other_instances=[f"{i.ip}:{master_instance.port}" for i in [new_master_host, new_stand_by_host]],
                ),
            ),
        )

        # 加入到集群的AlwaysOn可用组
        add_nodes_sub_pipeline.add_sub_pipeline(
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
            add_nodes_sub_pipeline.add_sub_pipeline(
                sub_flow=sync_dbs_for_cluster_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster,
                    sync_slaves=[new_master_host, new_stand_by_host],
                    sync_dbs=sync_dbs,
                    master_host=Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                    port=master_instance.port,
                )
            )

        # 克隆app_setting表配置
        add_nodes_sub_pipeline.add_parallel_acts(
            acts_list=[
                {
                    "act_name": _("新master克隆app_setting表配置"),
                    "act_component_code": CopyAppSettingComponent.code,
                    "kwargs": asdict(
                        CopyAppSettingComponent.kwargs(
                            cluster_id=cluster.id,
                            source_host=Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                            target_host=new_master_host,
                            target_port=master_instance.port,
                            target_role=InstanceRole.BACKEND_SLAVE,
                        )
                    ),
                },
                {
                    "act_name": _("新standby克隆app_setting表配置"),
                    "act_component_code": CopyAppSettingComponent.code,
                    "kwargs": asdict(
                        CopyAppSettingComponent.kwargs(
                            cluster_id=cluster.id,
                            source_host=Host(ip=stand_by_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                            target_host=new_stand_by_host,
                            target_port=stand_by_instance.port,
                            target_role=InstanceRole.BACKEND_SLAVE,
                        )
                    ),
                },
            ]
        )

        return add_nodes_sub_pipeline.build_sub_process(sub_name=_("{}添加节点到集群可用区".format(cluster.immute_domain)))

    def switch_in_always_on_cluster_sub_flow(
        self,
        cluster: Cluster,
        master_instance: StorageInstance,
        new_master_host: Host,
        new_stand_by_host: Host,
    ) -> Optional[SubProcess]:
        """
        always_on集群切换的子流程
        """
        stand_by_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_SLAVE, is_stand_by=True)

        switch_sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

        # 切换过程
        switch_sub_pipeline.add_sub_pipeline(
            sub_flow=switch_cluster_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                cluster=cluster,
                old_master_host=Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                new_master_host=new_master_host,
                port=master_instance.port,
                sync_mode_number=SqlserverSyncModeMaps[SqlserverSyncMode.ALWAYS_ON],
                force=False,
                sub_name=_("{}主从互切".format(cluster.immute_domain)),
                other_slaves=[
                    asdict(
                        SqlserverInstance(
                            host=new_stand_by_host.ip,
                            port=master_instance.port,
                            bk_cloud_id=new_stand_by_host.bk_cloud_id,
                            is_new=True,
                        )
                    )
                ]
                + [
                    asdict(
                        SqlserverInstance(
                            host=i.machine.ip,
                            port=i.port,
                            bk_cloud_id=cluster.bk_cloud_id,
                            is_new=False,
                        )
                    )
                    for i in cluster.storageinstance_set.filter(is_stand_by=False)
                ],
            )
        )

        # 变更集群域名映射
        switch_sub_pipeline.add_sub_pipeline(
            sub_flow=migrate_domain_for_cluster_ha(
                uid=self.data["uid"],
                root_id=self.root_id,
                cluster=cluster,
                old_master=master_instance,
                old_stand_by=stand_by_instance,
                new_master_host=new_master_host,
                new_stand_by_host=new_stand_by_host,
            )
        )

        # 旧实例移除可用组
        switch_sub_pipeline.add_sub_pipeline(
            sub_flow=SqlserverSlaveRebuildFlow.remote_slave_in_cluster(
                root_id=self.root_id,
                bk_biz_id=self.data["bk_biz_id"],
                uid=self.data["uid"],
                cluster=cluster,
                master_host=new_master_host,
                master_port=master_instance.port,
                old_slave_instances=[master_instance, stand_by_instance],
            )
        )

        # 删除随机账号
        switch_sub_pipeline.add_act(
            act_name=_("remove temp job account"),
            act_component_code=SqlserverDropJobUserComponent.code,
            kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id])),
        )

        return switch_sub_pipeline.build_sub_process(sub_name=_("{}切换新节点作为主从".format(cluster.immute_domain)))

    def switch_slave_mirroring_sub_flow(
        self, cluster: Cluster, master_host: Host, old_stand_by_host: Host, new_stand_by_host: Host, port: int
    ) -> Optional[SubProcess]:
        """
        主从集群迁移，切换新stand_by节点，mirroring模式专属
        @param cluster: 集群
        @param master_host: 主节点
        @param old_stand_by_host: 旧stand_by节点
        @param new_stand_by_host: 新stand_by节点
        @param port: cluster port
        """

        slave_entry_list = ClusterEntry.objects.filter(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, role=ClusterEntryRole.SLAVE_ENTRY
        )

        # 声明子流程
        cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

        # 创建随机账号
        cluster_sub_pipeline.add_act(
            act_name=_("create temp job account"),
            act_component_code=SqlserverAddJobUserComponent.code,
            kwargs=asdict(
                CreateRandomJobUserKwargs(
                    cluster_ids=[cluster.id],
                    sid=create_sqlserver_login_sid(),
                    other_instances=[f"{new_stand_by_host.ip}:{port}"],
                ),
            ),
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
                    sync_slaves=[new_stand_by_host],
                    sync_dbs=sync_dbs,
                    master_host=master_host,
                    port=port,
                )
            )

        # 克隆app_setting表配置
        cluster_sub_pipeline.add_act(
            act_name=_("克隆app_setting表配置"),
            act_component_code=CopyAppSettingComponent.code,
            kwargs=asdict(
                CopyAppSettingComponent.kwargs(
                    cluster_id=cluster.id,
                    source_host=old_stand_by_host,
                    target_host=new_stand_by_host,
                    target_port=port,
                    target_role=InstanceRole.BACKEND_SLAVE,
                ),
            ),
        )

        # 先做克隆周边配置
        cluster_sub_pipeline.add_sub_pipeline(
            sub_flow=clone_configs_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=cluster.bk_biz_id,
                source_host=master_host,
                source_port=port,
                target_host=new_stand_by_host,
                target_port=port,
            )
        )

        # 切换从域名
        sub_lists = []
        for entry in slave_entry_list:
            sub_flow = SqlserverSlaveRebuildFlow.fix_slave_dns_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=self.data["bk_biz_id"],
                domain_name=entry.entry,
                master_instance=SqlserverInstance(host=master_host.ip, port=port, bk_cloud_id=cluster.bk_cloud_id),
                new_slave_instance=SqlserverInstance(
                    host=new_stand_by_host.ip, port=port, bk_cloud_id=cluster.bk_cloud_id
                ),
                old_slave_instance=SqlserverInstance(
                    host=old_stand_by_host.ip, port=port, bk_cloud_id=cluster.bk_cloud_id
                ),
            )
            if sub_flow:
                sub_lists.append(sub_flow)

        if len(sub_lists) > 0:
            cluster_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_lists)

        # 删除随机账号
        cluster_sub_pipeline.add_act(
            act_name=_("remove temp job account"),
            act_component_code=SqlserverDropJobUserComponent.code,
            kwargs=asdict(
                DropRandomJobUserKwargs(
                    cluster_ids=[cluster.id],
                    other_instances=[f"{new_stand_by_host.ip}:{port}"],
                ),
            ),
        )

        return cluster_sub_pipeline.build_sub_process(sub_name=_("主从集群切换standby slave"))

    def switch_master_mirroring_sub_flow(
        self,
        cluster: Cluster,
        old_master_host: Host,
        new_master_host: Host,
        port: int,
        old_master_dns_list: List[ClusterEntry],
        new_master_dns_list: List[ClusterEntry],
    ) -> Optional[SubProcess]:
        """
        switch master
        """
        # 声明子流程
        cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

        # 创建随机账号
        cluster_sub_pipeline.add_act(
            act_name=_("create temp job account"),
            act_component_code=SqlserverAddJobUserComponent.code,
            kwargs=asdict(
                CreateRandomJobUserKwargs(
                    cluster_ids=[cluster.id],
                    sid=create_sqlserver_login_sid(),
                ),
            ),
        )

        cluster_sub_pipeline.add_sub_pipeline(
            sub_flow=switch_cluster_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                cluster=cluster,
                old_master_host=old_master_host,
                new_master_host=new_master_host,
                port=port,
                sync_mode_number=SqlserverSyncModeMaps[SqlserverSyncMode.MIRRORING],
                force=False,
                sub_name=_("{}主从互切".format(cluster.immute_domain)),
                other_slaves=[],
            )
        )

        cluster_sub_pipeline.add_sub_pipeline(
            sub_flow=switch_domain_sub_flow_for_cluster(
                uid=self.data["uid"],
                root_id=self.root_id,
                cluster=cluster,
                old_master_host=old_master_host,
                old_master_port=port,
                old_master_dns_list=old_master_dns_list,
                new_master_host=new_master_host,
                new_master_port=port,
                new_master_dns_list=new_master_dns_list,
                is_force=False,
            )
        )

        # 删除随机账号
        cluster_sub_pipeline.add_act(
            act_name=_("remove temp job account"),
            act_component_code=SqlserverDropJobUserComponent.code,
            kwargs=asdict(
                DropRandomJobUserKwargs(
                    cluster_ids=[cluster.id],
                ),
            ),
        )

        return cluster_sub_pipeline.build_sub_process(sub_name=_("主从集群切换standby master"))

    def migrate_by_always_on_sub_flow(
        self,
        cluster_ids: List[int],
        new_master_host: Host,
        new_stand_by_host: Host,
    ) -> Optional[SubProcess]:
        """
        always_on模式下处理主从迁移的流程
            1：备份文件同时传送新机器上面
            2：新机器都进行恢复
            3：新的实例加入到可用组
            4：人工确认切换
            5：预检测
            6：克隆账号/linkServer
            7：互切
            8：克隆job
            9：变更域名映射
        """

        cluster_add_nodes_sub_flows = []
        cluster_switch_sub_flows = []
        cluster_domain_list = []

        # 遍历集群，分别创建两个子流程列表
        # 一个用于添加节点列表，一个用于切换节点列表
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            master_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
            cluster_domain_list.append(cluster.immute_domain)

            # 构建添加节点子流程，并加入到cluster_add_nodes_sub_flows
            cluster_add_nodes_sub_flows.append(
                self.add_slave_in_always_on_cluster_sub_flow(
                    cluster=cluster,
                    master_instance=master_instance,
                    new_master_host=new_master_host,
                    new_stand_by_host=new_stand_by_host,
                )
            )

            # 构建切换子流程，并加入到cluster_switch_sub_flows
            cluster_switch_sub_flows.append(
                self.switch_in_always_on_cluster_sub_flow(
                    cluster=cluster,
                    master_instance=master_instance,
                    new_master_host=new_master_host,
                    new_stand_by_host=new_stand_by_host,
                )
            )

        # 构建返回子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

        # 阶段1：每个集群添加节点
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_add_nodes_sub_flows)

        # 人工确认
        sub_pipeline.add_act(act_name=_("人工确认切换"), act_component_code=PauseComponent.code, kwargs={})

        # 阶段2：每个集群切换节点
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_switch_sub_flows)

        # 阶段3：写入元数据
        sub_pipeline.add_act(
            act_name=_("变更元信息"),
            act_component_code=SqlserverDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SqlserverDBMeta.migrate_cluster_always_on.__name__,
                    component_kwargs={
                        "bk_biz_id": self.data["bk_biz_id"],
                        "cluster_ids": cluster_ids,
                        "new_master_host": new_master_host,
                        "new_stand_by_host": new_stand_by_host,
                        "creator": self.data["created_by"],
                    },
                )
            ),
        )

        return sub_pipeline.build_sub_process(
            sub_name=_("[{},{}]AlwaysOn主从集群迁移".format(new_master_host.ip, new_stand_by_host.ip))
        )

    def migrate_by_mirroring_sub_flow(
        self,
        cluster_ids: List[int],
        new_master_host: Host,
        new_stand_by_host: Host,
        old_master_host: Host,
        old_stand_by_host: Host,
    ) -> Optional[SubProcess]:
        """
        mirroring模式下处理主从迁移的流程，主要分为几个大步骤：
            1：新master作为临时standby节点，替换旧master（集群新机重建过程）
            2：执行互切 （集群互切过程）
            3：新standby替换旧master节点 （集群新机重建过程）
            4：回收旧master和旧standby实例 （实例级别回收）
            5：回收旧实例元数据
        """

        # 声明子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

        # 遍历集群
        switch_slave_step_one_list = []
        switch_master_step_two_list = []
        switch_slave_step_three_list = []
        cluster_domain_list = []
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            master_instance = cluster.storageinstance_set.get(machine__ip=old_master_host.ip)
            stand_by_instance = cluster.storageinstance_set.get(machine__ip=old_stand_by_host.ip)
            cluster_domain_list.append(cluster.immute_domain)

            # 阶段1 新的master先当做临时stand_by, 替换当前的stand_by节点
            switch_slave_step_one_list.append(
                self.switch_slave_mirroring_sub_flow(
                    cluster=cluster,
                    master_host=Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                    old_stand_by_host=Host(ip=stand_by_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                    new_stand_by_host=new_master_host,
                    port=stand_by_instance.port,
                )
            )
            # 阶段2 新的master和旧的master做互切
            switch_master_step_two_list.append(
                self.switch_master_mirroring_sub_flow(
                    cluster=cluster,
                    old_master_host=Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                    new_master_host=new_master_host,
                    port=master_instance.port,
                    old_master_dns_list=list(
                        master_instance.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
                    ),
                    new_master_dns_list=list(
                        stand_by_instance.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value).all()
                    ),
                )
            )

            # 阶段3 新的stand_by, 替换当前的stand_by节点
            switch_slave_step_three_list.append(
                self.switch_slave_mirroring_sub_flow(
                    cluster=cluster,
                    master_host=new_master_host,
                    old_stand_by_host=Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                    new_stand_by_host=new_stand_by_host,
                    port=master_instance.port,
                )
            )

        # 用new_master_host替换old_stand_by_host的并发子流程，每个子流程集群维度并发处理
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_slave_step_one_list)
        # 添加新实例的维度信息
        sub_pipeline.add_act(
            act_name=_("变更元信息"),
            act_component_code=SqlserverDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SqlserverDBMeta.switch_slave_for_migrate.__name__,
                    component_kwargs={
                        "bk_biz_id": int(self.data["bk_biz_id"]),
                        "cluster_ids": cluster_ids,
                        "old_slave_host": old_stand_by_host,
                        "new_slave_host": new_master_host,
                        "creator": self.data["created_by"],
                    },
                )
            ),
        )

        # 机器维度，给新机器部署周边程序
        sub_pipeline.add_sub_pipeline(
            sub_flow=install_surrounding_apps_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=int(self.data["bk_biz_id"]),
                bk_cloud_id=int(new_master_host.bk_cloud_id),
                master_host=[],
                slave_host=[new_master_host],
                cluster_domain_list=cluster_domain_list,
            )
        )
        sub_pipeline.add_act(act_name=_("人工确认切换主节点"), act_component_code=PauseComponent.code, kwargs={})

        # 切换主节点，new_master_host 作为新主的并发子流程，每个子流程集群维度并发处理
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_master_step_two_list)
        # 安装机器维度变更元数据
        sub_pipeline.add_act(
            act_name=_("变更元信息"),
            act_component_code=SqlserverDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SqlserverDBMeta.sqlserver_ha_switch.__name__,
                    component_kwargs={
                        "cluster_ids": cluster_ids,
                        "old_master_host": old_master_host,
                        "new_master_host": new_master_host,
                        "is_force": False,
                    },
                )
            ),
        )

        # 重新配置源数据, 不需要安装备份client
        sub_pipeline.add_sub_pipeline(
            sub_flow=install_surrounding_apps_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=int(self.data["bk_biz_id"]),
                bk_cloud_id=int(new_master_host.bk_cloud_id),
                master_host=[new_master_host],
                slave_host=[old_master_host],
                cluster_domain_list=cluster_domain_list,
                is_install_backup_client=False,
            )
        )
        sub_pipeline.add_act(act_name=_("人工确认切换从节点"), act_component_code=PauseComponent.code, kwargs={})

        # 用new_stand_by_host替换old_master_host的并发子流程，每个子流程集群维度并发处理
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=switch_slave_step_three_list)
        sub_pipeline.add_act(
            act_name=_("变更元信息"),
            act_component_code=SqlserverDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SqlserverDBMeta.switch_slave_for_migrate.__name__,
                    component_kwargs={
                        "bk_biz_id": int(self.data["bk_biz_id"]),
                        "cluster_ids": cluster_ids,
                        "old_slave_host": old_master_host,
                        "new_slave_host": new_stand_by_host,
                        "creator": self.data["created_by"],
                    },
                )
            ),
        )

        # 机器维度，给新机器部署周边程序
        sub_pipeline.add_sub_pipeline(
            sub_flow=install_surrounding_apps_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=int(self.data["bk_biz_id"]),
                bk_cloud_id=int(new_stand_by_host.bk_cloud_id),
                master_host=[],
                slave_host=[new_stand_by_host],
                cluster_domain_list=cluster_domain_list,
            )
        )

        return sub_pipeline.build_sub_process(
            sub_name=_("[{},{}]Mirroring主从集群迁移".format(new_master_host.ip, new_stand_by_host.ip))
        )

    def cluster_single_migrate_sub_flow(self, cluster_ids: List[int], new_host: Host) -> Optional[SubProcess]:
        """
        定义单节点集群类型迁移的子流程。流程步骤：
            1：初始化新机器
            2：安装新机器
            3：源集群发起备份
            4: 下载备份文件到你目标机器
            5：恢复备份文件
            6：建立mirroring模式的数据同步
            7：恢复周边配置：账号、job、LinkServer等相关的周边配置
            8：人工确认切换
            9：切换集群配置：预检测，mirroring互切，域名映射切换，切换元数据
            10：人工确认下架
            11：下架旧实例
            12：判断是否下架机器

        @param cluster_ids: 同机关联的集群id列表
        @param new_host: 新机器列表
        @return SubProcess: 子流程
        """
        # 计算需要关联的集群信息
        associated_clusters = SqlserverAddSlaveFlow.get_clusters_install_info(cluster_ids)

        # 已第一集群id的db_module_id/db_version 作为本次的安装依据，因为平台上同机相关联的集群的模块id/主版本都是一致的
        cluster = Cluster.objects.get(id=cluster_ids[0])

        # 当前单节点的原信息, 有且只有一个机器
        old_orphan_machine = cluster.storageinstance_set.get().machine

        # 声明子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

        # 初始化机器
        sub_pipeline.add_sub_pipeline(
            sub_flow=init_machine_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=int(self.data["bk_biz_id"]),
                bk_cloud_id=new_host.bk_cloud_id,
                target_hosts=[new_host],
            )
        )

        # 根据关联的集群，安装实例
        sub_pipeline.add_sub_pipeline(
            sub_flow=install_sqlserver_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=int(self.data["bk_biz_id"]),
                bk_cloud_id=cluster.bk_cloud_id,
                db_module_id=cluster.db_module_id,
                install_ports=[i.port for i in associated_clusters],
                clusters=associated_clusters,
                cluster_type=ClusterType.SqlserverSingle,
                target_hosts=[new_host],
                db_version=cluster.major_version,
            )
        )

        # 安装周边程序, 先安装备份程序
        sub_pipeline.add_sub_pipeline(
            sub_flow=install_surrounding_apps_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=int(self.data["bk_biz_id"]),
                bk_cloud_id=new_host.bk_cloud_id,
                master_host=[new_host],
                slave_host=[],
                cluster_domain_list=[],
                is_init_app_setting=False,
            )
        )

        # 集群级别操作
        cluster_sub_flows = []
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            old_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.ORPHAN)
            cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

            # 创建随机账号
            cluster_sub_pipeline.add_act(
                act_name=_("create temp job account"),
                act_component_code=SqlserverAddJobUserComponent.code,
                kwargs=asdict(
                    CreateRandomJobUserKwargs(
                        cluster_ids=[cluster.id],
                        sid=create_sqlserver_login_sid(),
                        other_instances=[f"{new_host.ip}:{old_instance.port}"],
                    ),
                ),
            )

            # 数据库建立新的同步关系
            sync_dbs = list(set(get_dbs_for_drs(cluster_id=cluster.id, db_list=["*"], ignore_db_list=[])))
            if len(sync_dbs) > 0:
                cluster_sub_pipeline.add_sub_pipeline(
                    sub_flow=sync_dbs_for_cluster_sub_flow(
                        uid=self.data["uid"],
                        root_id=self.root_id,
                        cluster=cluster,
                        sync_slaves=[new_host],
                        sync_dbs=sync_dbs,
                        master_host=Host(ip=old_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                        port=old_instance.port,
                        sync_mode=SqlserverSyncMode.MIRRORING,
                    )
                )
            # 克隆app_setting表配置
            cluster_sub_pipeline.add_act(
                act_name=_("克隆app_setting表配置"),
                act_component_code=CopyAppSettingComponent.code,
                kwargs=asdict(
                    CopyAppSettingComponent.kwargs(
                        cluster_id=cluster.id,
                        source_host=Host(ip=old_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                        target_host=new_host,
                        target_port=old_instance.port,
                        target_role=InstanceRole.ORPHAN,
                    ),
                ),
            )

            # 人工确认切换
            cluster_sub_pipeline.add_act(
                act_name=_("人工确认切换"),
                act_component_code=PauseComponent.code,
                kwargs={},
            )

            cluster_sub_pipeline.add_sub_pipeline(
                sub_flow=switch_cluster_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster,
                    old_master_host=Host(ip=old_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                    new_master_host=new_host,
                    port=old_instance.port,
                    sync_mode_number=SqlserverSyncModeMaps[SqlserverSyncMode.MIRRORING],
                    force=False,
                    sub_name=_("{}节点互切".format(cluster.immute_domain)),
                    other_slaves=[],
                )
            )

            # 变更集群域名映射
            cluster_sub_pipeline.add_sub_pipeline(
                sub_flow=migrate_domain_for_cluster_single(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster,
                    old_instance=old_instance,
                    new_host=new_host,
                )
            )

            cluster_sub_pipeline.add_act(
                act_name=_("移除mirroring配置"),
                act_component_code=RemoveMirroringConfigComponent.code,
                kwargs=asdict(RemoveMirroringConfigComponent.kwargs(cluster_id=cluster.id, target_hosts=[new_host])),
            )

            # 删除随机账号
            cluster_sub_pipeline.add_act(
                act_name=_("remove temp job account"),
                act_component_code=SqlserverDropJobUserComponent.code,
                kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id])),
            )

            cluster_sub_flows.append(
                cluster_sub_pipeline.build_sub_process(sub_name=_("{}-单节点切换".format(cluster.immute_domain)))
            )

        # 拼接集群维度的子流程
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_sub_flows)

        # 安装机器维度变更元数据
        sub_pipeline.add_act(
            act_name=_("变更元信息"),
            act_component_code=SqlserverDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SqlserverDBMeta.migrate_cluster_single.__name__,
                    component_kwargs={
                        "bk_biz_id": self.data["bk_biz_id"],
                        "cluster_ids": cluster_ids,
                        "new_host": new_host,
                        "creator": self.data["created_by"],
                    },
                )
            ),
        )

        # 人工确认下架
        sub_pipeline.add_act(
            act_name=_("人工确认下架"),
            act_component_code=PauseComponent.code,
            kwargs={},
        )

        # 回收相关实例信息
        sub_pipeline.add_sub_pipeline(
            sub_flow=self.remove_old_instance_sub_flow(
                cluster_ids=cluster_ids,
                old_hosts=[
                    Host(
                        ip=old_orphan_machine.ip,
                        bk_cloud_id=old_orphan_machine.bk_cloud_id,
                        bk_host_id=old_orphan_machine.bk_host_id,
                    )
                ],
                cluster_type=ClusterType.SqlserverSingle,
            )
        )

        return sub_pipeline.build_sub_process(
            sub_name=_("[{}]单节点集群迁移".format([i.immutable_domain for i in associated_clusters]))
        )

    def cluster_ha_migrate_sub_flow(self, cluster_ids: List[int], new_hosts: List[Host]) -> Optional[SubProcess]:
        """
        定义主从集群类型的迁移子流程。流程步骤：
            1：初始化新机器
            2：安装新机器/ 源集群发起备份
            3: 这里根据不同集群同步模式，选择不同处理方式
                A: always_on模式
                B: mirroring模式
            4： 清理机器（如果可以）
        """
        # 计算需要关联的集群信息
        associated_clusters = SqlserverAddSlaveFlow.get_clusters_install_info(cluster_ids)

        # 根据同机关联的集群中的集群类型，判断使用哪种迁移流程
        # 因为是同机关联集群，所以只需要取一个集群即可
        template_cluster = Cluster.objects.get(id=cluster_ids[0])

        # 声明子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

        # 获取主从集群的master机器和 is_stand_by = True 的 slave机器
        # 因为传进来cluster_ids是同机关联的集群，所以只需要取一个集群即可
        master_machine = template_cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER).machine
        stand_by_machine = template_cluster.storageinstance_set.get(
            is_stand_by=True, instance_role=InstanceRole.BACKEND_SLAVE
        ).machine

        # 计算好谁是新的master和新stand_by_slave节点
        new_master_host = new_hosts[0]
        new_stand_by_host = new_hosts[1]

        # 初始化机器
        sub_pipeline.add_sub_pipeline(
            sub_flow=init_machine_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=int(self.data["bk_biz_id"]),
                bk_cloud_id=template_cluster.bk_cloud_id,
                target_hosts=new_hosts,
            )
        )

        # 根据关联的集群，安装实例
        sub_pipeline.add_sub_pipeline(
            sub_flow=install_sqlserver_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=int(self.data["bk_biz_id"]),
                bk_cloud_id=template_cluster.bk_cloud_id,
                db_module_id=template_cluster.db_module_id,
                install_ports=[i.port for i in associated_clusters],
                clusters=associated_clusters,
                cluster_type=ClusterType.SqlserverHA,
                target_hosts=new_hosts,
                db_version=template_cluster.major_version,
            )
        )

        # 安装周边程序, 先安装备份程序
        sub_pipeline.add_sub_pipeline(
            sub_flow=install_surrounding_apps_sub_flow(
                uid=self.data["uid"],
                root_id=self.root_id,
                bk_biz_id=int(self.data["bk_biz_id"]),
                bk_cloud_id=template_cluster.bk_cloud_id,
                master_host=new_hosts,
                slave_host=[],
                cluster_domain_list=[],
                is_init_app_setting=False,
            )
        )

        if (
            SqlserverClusterSyncMode.objects.get(cluster_id=template_cluster.id).sync_mode
            == SqlserverSyncMode.ALWAYS_ON
        ):
            # always_on模式下处理主从迁移的流程
            sub_pipeline.add_sub_pipeline(
                self.migrate_by_always_on_sub_flow(
                    cluster_ids=cluster_ids, new_master_host=new_master_host, new_stand_by_host=new_stand_by_host
                )
            )
        else:
            # mirroring模式下处理主从迁移的流程
            sub_pipeline.add_sub_pipeline(
                self.migrate_by_mirroring_sub_flow(
                    cluster_ids=cluster_ids,
                    new_master_host=new_master_host,
                    new_stand_by_host=new_stand_by_host,
                    old_master_host=Host(ip=master_machine.ip, bk_cloud_id=master_machine.bk_cloud_id),
                    old_stand_by_host=Host(ip=stand_by_machine.ip, bk_cloud_id=stand_by_machine.bk_cloud_id),
                )
            )

        # 人工确认下架
        sub_pipeline.add_act(
            act_name=_("人工确认下架"),
            act_component_code=PauseComponent.code,
            kwargs={},
        )

        # 回收相关实例信息
        sub_pipeline.add_sub_pipeline(
            sub_flow=self.remove_old_instance_sub_flow(
                cluster_ids=cluster_ids,
                old_hosts=[
                    Host(
                        ip=master_machine.ip,
                        bk_cloud_id=master_machine.bk_cloud_id,
                        bk_host_id=master_machine.bk_host_id,
                    ),
                    Host(
                        ip=stand_by_machine.ip,
                        bk_cloud_id=stand_by_machine.bk_cloud_id,
                        bk_host_id=stand_by_machine.bk_host_id,
                    ),
                ],
                cluster_type=ClusterType.SqlserverHA,
            )
        )
        return sub_pipeline.build_sub_process(
            sub_name=_("[{}]主从集群迁移".format([i.immutable_domain for i in associated_clusters]))
        )

    def run_flow(self):
        """
        集群迁移流程定义
        同时支持单节点集群和主从集群在同一单据处理
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 判断每一行处理的集群类型是什么，进入对应的子流程
            # cluster_ids 代表的是一组同组关联集群， 那么它们的集群类型必定是相等的
            # 所以判断时，拿其中一个集群作为判断即可
            cluster = Cluster.objects.get(id=info["cluster_ids"][0])
            if cluster.cluster_type == ClusterType.SqlserverHA:
                sub_pipelines.append(
                    self.cluster_ha_migrate_sub_flow(
                        cluster_ids=info["cluster_ids"], new_hosts=[Host(**i) for i in info["new_hosts"]]
                    )
                )
            elif cluster.cluster_type == ClusterType.SqlserverSingle:
                sub_pipelines.append(
                    self.cluster_single_migrate_sub_flow(
                        cluster_ids=info["cluster_ids"], new_host=Host(**info["new_hosts"][0])
                    )
                )
            else:
                # 其他集群类型不支持
                raise MigrateFlowException(f"not support cluster_type{cluster.cluster_type}")

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline(init_trans_data_class=SqlserverBackupIDContext())
