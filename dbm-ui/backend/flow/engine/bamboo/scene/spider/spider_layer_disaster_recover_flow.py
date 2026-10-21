# -*- coding: utf-8 -*-
"""
TenDBCluster 接入层全毁灾难恢复：冷安装 Spider/tdbctl → Remote 授权 → 表结构 → 权限 → 路由 → 元数据切换。
支持 spider_master / spider_slave 角色独立或同时恢复（同时恢复时严格按 master → slave 串行编排）。
"""
import copy
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryRole, ClusterType, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_report.mysql_backup.handers import MySQLBackupHandler
from backend.flow.consts import DBA_ROOT_USER, TDBCTL_USER, DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildEntrysManageSubflow
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import (
    add_spider_masters_sub_flow,
    add_spider_slaves_sub_flow,
    reduce_spiders_flow,
)
from backend.flow.engine.bamboo.scene.spider.common.spider_layer_priv_recover_sub_flow import (
    spider_layer_priv_recover_sub_flow,
)
from backend.flow.engine.bamboo.scene.spider.spider_add_nodes import TenDBClusterAddNodesFlow
from backend.flow.engine.bamboo.scene.spider.spider_reduce_nodes import TenDBClusterReduceNodesFlow
from backend.flow.plugins.components.collections.common.add_unlock_ticket_type_config import (
    AddUnlockTicketTypeConfigComponent,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.common.pause_with_ticket_lock_check import (
    PauseWithTicketLockCheckComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.flow_output_summary import MysqlFlowOutputSummaryComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.add_system_user_in_cluster import (
    AddSystemUserInClusterComponent,
)
from backend.flow.plugins.components.collections.spider.drop_spider_ronting import DropSpiderRoutingComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.plugins.components.collections.spider.spider_dr_retain_routing import SpiderDRRetainRoutingComponent
from backend.flow.plugins.components.collections.spider.spider_dr_routing_init import SpiderDRRoutingInitComponent
from backend.flow.plugins.components.collections.spider.spider_layer_disaster_recover_route_preview import (
    SpiderLayerDisasterRecoverRoutePreviewComponent,
)
from backend.flow.utils.base.base_dataclass import AddUnLockTicketTypeKwargs, ReleaseUnLockTicketTypeKwargs
from backend.flow.utils.mysql.flow_output_presets.instance_change import InstanceChangeAction
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSpiderSystemUserKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
from backend.flow.utils.spider.spider_act_dataclass import DropSpiderRoutingKwargs
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.flow.utils.spider.spider_disaster_recover import (
    build_append_deploy_style_routing_extend,
    build_combined_route_preview,
    build_mysql_ip_list_and_ports,
    get_shard_zero_remote_master,
    get_spider_pkg_id_for_layer_disaster_recover,
    resolve_ctl_primary_ip,
    resolve_spider_ctl_ports,
    slave_only_recover_cluster_ids,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class TenDBClusterSpiderLayerDisasterRecoverFlow(TenDBClusterAddNodesFlow, TenDBClusterReduceNodesFlow):
    """
    ticket_data 与 TENDBCLUSTER_SPIDER_LAYER_DR 对齐 infos 列表，字段见单据 Serializer。

    支持三种恢复场景（由 info 中 spider_master_new_ip_list / spider_slave_new_ip_list 是否非空自动判定）：
      1. 仅恢复 spider_master：spider_master_new_ip_list 非空，spider_slave_new_ip_list 为空
      2. 仅恢复 spider_slave：spider_slave_new_ip_list 非空，spider_master_new_ip_list 为空
                              （路由连 tdbctl primary，并在该中控创建临时账号）
      3. 同时恢复 master + slave：两者都非空，按"安装并行 + 路由串行（master 先 / slave 后）"五阶段编排

    调用参数样板（与 ticket_data 同形，可直接 POST 至 /apis/v1/flow/scene/spider_layer_disaster_recover）：
    {
        "uid": "20260506-000001",                # 单据/调用唯一 ID
        "bk_biz_id": 100,                        # 业务 ID
        "created_by": "admin",                   # 操作人
        "disable_manual_confirm": false,         # 可选，关闭路由预览/缩容旧接入层的人工确认（顶层读取）
        "infos": [
            {
                "cluster_id": 12345,             # 必填，TenDBCluster 集群 ID

                # ── master 段 IP 列表（非空时本次恢复 spider_master）──────────────
                # 注意：new 列表每台机器必须带 spec（含 id 字段），DBMeta add_spiders 强制要求
                "spider_master_new_ip_list": [   # 非空时必填；第 1 台作为主中控（primary_ctl_ip）
                    {"bk_cloud_id": 0, "bk_host_id": 100001, "ip": "127.0.0.11",
                     "spec": {"id": 1, "cpu": {...}, "mem": {...}, "storage_spec": [...]}}
                ],
                "spider_master_old_ip_list": [   # master_new 非空时必填，须与元数据 SPIDER_MASTER 严格一致
                    {"bk_cloud_id": 0, "bk_host_id": 200001, "ip": "127.0.0.21"}
                ],

                # ── slave 段 IP 列表（非空时本次恢复 spider_slave）───────────────
                # 注意：new 列表每台机器必须带 spec（含 id 字段），DBMeta add_spiders 强制要求
                "spider_slave_new_ip_list": [    # 非空时必填
                    {"bk_cloud_id": 0, "bk_host_id": 300001, "ip": "127.0.0.31",
                     "spec": {"id": 1, "cpu": {...}, "mem": {...}, "storage_spec": [...]}}
                ],
                "spider_slave_old_ip_list": [    # slave_new 非空时必填，须与元数据 SPIDER_SLAVE 严格一致
                    {"bk_cloud_id": 0, "bk_host_id": 400001, "ip": "127.0.0.41"}
                ],

                "privilege_recovery_mode": "from_spider_grant_backup",
                                                 # 可选，from_spider_grant_backup / account_rules_only；
                                                 # 默认 from_spider_grant_backup
                "spider_priv_backup_id": "",     # 可选，指定 grant 备份 backup_id；不传取最近 7 天内最新
                "strip_dns_before_install": true,# 可选，安装前对应域名（主/从）摘除旧 IP
                "skip_schema_sync": false,       # 可选，跳过表结构从 Remote 同步至中控/Spider（仅 master 段生效）
                "spider_port": null,             # 可选，Spider 端口覆盖；留空取集群当前端口
                "ctl_port": null                 # 可选，TDBCTL 端口覆盖；留空 = spider_port + 1000（仅 master 段生效）
            }
        ]
    }

    备注：
    - pkg_id 无需传入，流程内通过 get_spider_pkg_id_for_layer_disaster_recover 自动解析。
    - master_new 与 slave_new 不可有重叠 IP（同一台机器不能既装 master 又装 slave），由 Validator 阻断。
    - 仅恢复 slave 时 Validator 已通过 L1+L3 双层校验中控（DBMeta RUNNING + DRS 探活）。
    - 直调 FlowTestView 不会触发 Validator，需自行确保参数合法。
    """

    temporary_unlock_ticket_type_list = [
        TicketType.TENDBCLUSTER_IMPORT_SQLFILE,
        TicketType.TENDBCLUSTER_FORCE_IMPORT_SQLFILE,
        TicketType.TENDBCLUSTER_SEMANTIC_CHECK,
        TicketType.TENDBCLUSTER_AUTHORIZE_RULES,
    ]

    def __init__(self, root_id: str, data: Optional[Dict]):
        super().__init__(root_id=root_id, data=data)
        super(TenDBClusterAddNodesFlow, self).__init__(root_id=root_id, data=data)

    # ─────────────────────────────────────────────────────────────────────────
    # 旧 IP 列表解析（直调 FlowTestView 时的 fallback；走单据时 Validator 已保证非空）
    # ─────────────────────────────────────────────────────────────────────────
    def _resolve_old_master_hosts(self, cluster: Cluster, info: dict) -> List[dict]:
        explicit = info.get("spider_master_old_ip_list")
        if explicit:
            return explicit
        return [
            {"ip": p.machine.ip, "bk_cloud_id": cluster.bk_cloud_id, "bk_host_id": p.machine.bk_host_id}
            for p in cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
            )
        ]

    def _resolve_old_slave_hosts(self, cluster: Cluster, info: dict) -> List[dict]:
        explicit = info.get("spider_slave_old_ip_list")
        if explicit:
            return explicit
        return [
            {"ip": p.machine.ip, "bk_cloud_id": cluster.bk_cloud_id, "bk_host_id": p.machine.bk_host_id}
            for p in cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value,
            )
        ]

    @staticmethod
    def _collect_retained_nodes(cluster: Cluster, exclude_ips: Optional[List[str]] = None) -> List[dict]:
        """收集存活的保留接入层节点（RUNNING 的 spider_slave / spider_mnt / spider_slave_mnt）。

        重建 master 时调用：这些节点上已有业务表结构，重建后需"仅路由登记"方式重新纳入新中控，
        不能以 with database 重新导入。运维节点 wrapper 与 Go 侧 getSpiderRouterSqls 的映射保持一致。
        exclude_ips：本次同时被替换的旧 slave（master+slave 同时重建场景），它们会下架，不能再登记。
        """
        excluded = set(exclude_ips or [])
        role_wrapper_map = {
            TenDBClusterSpiderRole.SPIDER_SLAVE.value: "SPIDER_SLAVE",
            TenDBClusterSpiderRole.SPIDER_MNT.value: "SPIDER",
            TenDBClusterSpiderRole.SPIDER_SLAVE_MNT.value: "SPIDER_SLAVE",
        }
        nodes: List[dict] = []
        for role, wrapper in role_wrapper_map.items():
            for p in cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=role, status=InstanceStatus.RUNNING.value
            ):
                if p.machine.ip in excluded:
                    continue
                nodes.append({"ip": p.machine.ip, "port": p.port, "wrapper": wrapper})
        return nodes

    # ─────────────────────────────────────────────────────────────────────────
    # 各 segment 子流程
    # ─────────────────────────────────────────────────────────────────────────
    def _build_master_install_segment(
        self,
        *,
        cluster: Cluster,
        new_masters: List[dict],
        pkg_id: int,
        primary_ctl_ip: str,
        cluster_ticket: dict,
    ) -> Any:
        """
        Stage 1 - master 安装段：装机 + 装 spider master + 装中控 + Remote 内置账号授权。
        与 slave 安装段可并行（旧 spider 全毁场景下 InstallSpiderWithCopyConfigService 自动跳过克隆配置）。
        """
        seg = SubBuilder(root_id=self.root_id, data=cluster_ticket)
        seg.add_sub_pipeline(
            sub_flow=add_spider_masters_sub_flow(
                cluster=cluster,
                add_spider_masters=new_masters,
                root_id=self.root_id,
                uid=str(self.data["uid"]),
                parent_global_data=cluster_ticket,
                is_add_spider_mnt=False,
                global_pkg_id=pkg_id,
                cold_disaster_recover=True,
            )
        )
        # add_spider_masters_sub_flow 已在 parent_global_data 中写入随机化的 tdbctl_pass，此处必有值
        tdbctl_pass = cluster_ticket["tdbctl_pass"]
        seg.add_act(
            act_name=_("Remote 与接入层内置账号授权"),
            act_component_code=AddSystemUserInClusterComponent.code,
            kwargs=asdict(
                AddSpiderSystemUserKwargs(ctl_master_ip=primary_ctl_ip, user=TDBCTL_USER, passwd=tdbctl_pass)
            ),
        )
        return seg.build_sub_process(sub_name=_("[{}] master 安装段").format(cluster.immute_domain))

    def _build_slave_install_segment(
        self,
        *,
        cluster: Cluster,
        new_slaves: List[dict],
        pkg_id: int,
        cluster_ticket: dict,
    ) -> Any:
        """
        Stage 1 - slave 安装段：装机 + 装 spider slave。
        cold 模式下跳过路由登记 / 权限克隆 / DNS（由上层统一处理或 Stage 3 路由段处理）。
        """
        seg = SubBuilder(root_id=self.root_id, data=cluster_ticket)
        seg.add_sub_pipeline(
            sub_flow=add_spider_slaves_sub_flow(
                cluster=cluster,
                add_spider_slaves=new_slaves,
                root_id=self.root_id,
                uid=str(self.data["uid"]),
                parent_global_data=cluster_ticket,
                global_pkg_id=pkg_id,
                cold_disaster_recover=True,
            )
        )
        return seg.build_sub_process(sub_name=_("[{}] slave 安装段").format(cluster.immute_domain))

    def _build_master_routing_segment(
        self,
        *,
        cluster: Cluster,
        new_masters: List[dict],
        primary_ctl_ip: str,
        spider_port: int,
        ctl_port: int,
        info: dict,
        cluster_ticket: dict,
    ) -> Any:
        """
        Stage 2 - master 路由段：DBMeta 写入 → 初始化并下发接入层路由（三步合一）→ 表结构同步 → 权限恢复。
        必须在 Stage 1 安装段完成后串行执行；slave 路由段必须等本段完成。

        路由初始化合并为一个节点（SpiderDRRoutingInitComponent）：中控/分片/Spider 登记 + enable primary
        + TDBCTL FLUSH ROUTING，幂等（无 truncate、无 with database），末尾核对路由表。
        必须在表结构导入前完成下发：中控以 tc_admin=1 导入表结构时 DDL 会转发到 Spider 建表，
        SPIDER 表引用的 foreign server（SPT0 等分片名）必须已存在于 Spider 本地 mysql.servers，
        否则报 Error 1477: The foreign server name you are trying to reference does not exist. Data source error: SPT0。
        DBMeta 仍先于安装临时备份程序：该步骤通过 ORM 查 Machine 表。
        主域名绑定统一延后到「域名恢复段」：保留节点/新 slave 全部登记完成后才恢复解析。
        """
        seg = SubBuilder(root_id=self.root_id, data=cluster_ticket)

        seg.add_act(
            act_name=_("更新 DBMeta（新增 Spider Master）"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=SpiderDBMeta.add_spider_master_nodes_apply.__name__)),
        )

        tdbctl_pass = cluster_ticket["tdbctl_pass"]
        routing_extend = build_append_deploy_style_routing_extend(
            cluster=cluster,
            new_spider_hosts=new_masters,
            spider_port=spider_port,
            ctl_port=ctl_port,
            tdbctl_user=TDBCTL_USER,
            tdbctl_pass=tdbctl_pass,
        )
        # 三步合一：中控/分片/Spider 路由登记 + enable primary + TDBCTL FLUSH ROUTING + 核对
        seg.add_act(
            act_name=_("初始化并下发接入层路由"),
            act_component_code=SpiderDRRoutingInitComponent.code,
            kwargs={
                "cluster_id": cluster.id,
                "ctl_primary": f"{primary_ctl_ip}{IP_PORT_DIVIDER}{ctl_port}",
                "spider_port": spider_port,
                "ctl_port": ctl_port,
                "tdbctl_user": TDBCTL_USER,
                "tdbctl_pass": tdbctl_pass,
                "new_master_ips": [h["ip"] for h in new_masters],
                "remote_tuples": routing_extend["mysql_instance_tuples"],
            },
        )

        if not info.get("skip_schema_sync", False):
            self._add_schema_sync_acts(
                seg=seg,
                cluster=cluster,
                primary_ctl_ip=primary_ctl_ip,
                spider_port=spider_port,
                ctl_port=ctl_port,
                cluster_ticket=cluster_ticket,
            )

        self._maybe_add_priv_recover(
            seg=seg,
            cluster=cluster,
            info=info,
            target_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
            restore_ips=[h["ip"] for h in new_masters],
            spider_port=spider_port,
            ctl_port=ctl_port,
        )
        return seg.build_sub_process(sub_name=_("[{}] master 路由段").format(cluster.immute_domain))

    def _build_slave_routing_segment(
        self,
        *,
        cluster: Cluster,
        new_slaves: List[dict],
        old_slaves: List[dict],
        recover_master: bool,
        primary_ctl_ip: str,
        spider_port: int,
        ctl_port: int,
        info: dict,
        cluster_ticket: dict,
    ) -> Any:
        """
        Stage 3 - slave 路由段：（仅重建 slave：先定向清理旧 slave 路由）→ 主中控登记 slave 路由
        → slave 权限恢复 → DBMeta。
        必须在 master 路由段完成后串行执行（依赖中控可用 + master DBMeta 已写入）。

        上下文隔离：slave 段使用 slave 专属 spider_ip_list（DBMeta 的 add_spider_nodes 读取该字段），
        避免 master+slave 同时重建时误用 master 主机列表。
        从域名绑定统一延后到「域名恢复段」。
        """
        # slave 段专属上下文：spider_ip_list 指向新 slave
        slave_ctx = copy.deepcopy(cluster_ticket)
        slave_ctx["spider_ip_list"] = copy.deepcopy(new_slaves)
        seg = SubBuilder(root_id=self.root_id, data=slave_ctx)

        if not recover_master:
            # 仅重建 slave：现有中控里仍保留旧 slave 路由，先按单据旧节点清单定向清理
            # （master+slave 同时重建时新中控为空表重建，不存在旧 slave 条目，无需清理）
            seg.add_act(
                act_name=_("清理被替换 Spider Slave 的旧路由"),
                act_component_code=DropSpiderRoutingComponent.code,
                kwargs=asdict(
                    DropSpiderRoutingKwargs(
                        cluster_id=cluster.id,
                        reduce_spiders=[{"ip": h["ip"]} for h in old_slaves],
                        is_reduce_tdbctl=False,
                    )
                ),
            )

        slave_routing_cluster = {
            "cluster_id": cluster.id,
            "is_init_slave_cluster": True,
            "add_spider_slaves": new_slaves,
        }
        if recover_master:
            # combined：新中控密码由安装段生成，显式透传（payload 会合并进 runtime_account）
            slave_routing_cluster["tdbctl_user"] = TDBCTL_USER
            slave_routing_cluster["tdbctl_pass"] = cluster_ticket["tdbctl_pass"]
        seg.add_act(
            act_name=_("主中控登记新 spider_slave 路由"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=primary_ctl_ip,
                    bk_cloud_id=cluster.bk_cloud_id,
                    cluster_type=ClusterType.TenDBCluster.value,
                    run_as_system_user=DBA_ROOT_USER,
                    get_mysql_payload_func=MysqlActPayload.add_spider_slave_routing_payload.__name__,
                    cluster=slave_routing_cluster,
                )
            ),
        )

        # slave 段权限恢复（与 master 段独立，由同一备份策略驱动；TDBCTL 角色备份会被自动跳过）
        self._maybe_add_priv_recover(
            seg=seg,
            cluster=cluster,
            info=info,
            target_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value,
            restore_ips=[h["ip"] for h in new_slaves],
            spider_port=spider_port,
            ctl_port=ctl_port,
        )

        seg.add_act(
            act_name=_("更新 DBMeta（新增 Spider Slave）"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=SpiderDBMeta.add_spider_slave_nodes_apply.__name__)),
        )
        return seg.build_sub_process(sub_name=_("[{}] slave 路由段").format(cluster.immute_domain))

    def _build_retained_nodes_segment(
        self,
        *,
        cluster: Cluster,
        retained_nodes: List[dict],
        primary_ctl_ip: str,
        spider_port: int,
        ctl_port: int,
        cluster_ticket: dict,
    ) -> Any:
        """
        Stage 2.5 - 保留节点段（重建 master 且存在存活的、未被本次替换的 spider_slave/运维节点时执行）：
        更新保留节点内置账号（新中控新密码）→ 仅路由登记（不带 with database，不重导业务表）
        → TDBCTL FLUSH ROUTING → 核对 + 表结构粗略一致性校验。

        保留节点已有业务表结构，绝不能以 with database 方式重新导入；本段失败会阻断后续域名恢复。
        """
        seg = SubBuilder(root_id=self.root_id, data=cluster_ticket)
        seg.add_act(
            act_name=_("登记保留 Spider 节点路由并更新内置账号"),
            act_component_code=SpiderDRRetainRoutingComponent.code,
            kwargs={
                "cluster_id": cluster.id,
                "bk_biz_id": cluster.bk_biz_id,
                "operator": self.data["created_by"],
                "ctl_primary": f"{primary_ctl_ip}{IP_PORT_DIVIDER}{ctl_port}",
                "tdbctl_user": TDBCTL_USER,
                "tdbctl_pass": cluster_ticket["tdbctl_pass"],
                "retain_nodes": retained_nodes,
            },
        )
        return seg.build_sub_process(sub_name=_("[{}] 保留节点路由段").format(cluster.immute_domain))

    def _build_dns_restore_segment(
        self,
        *,
        cluster: Cluster,
        master_new: List[dict],
        slave_new: List[dict],
        recover_master: bool,
        recover_slave: bool,
        spider_port: int,
    ) -> Any:
        """
        域名恢复段：本次恢复的目标拓扑（新节点 + 保留节点）全部登记并核对后，统一恢复域名解析。
        master 重建恢复主域名，slave 重建恢复从域名；在 Stage 4 人工确认之前完成。
        """
        seg = SubBuilder(root_id=self.root_id, data=self.data)
        if recover_master:
            master_entry_sub = BuildEntrysManageSubflow(
                root_id=self.root_id,
                ticket_data=self.data,
                op_type=DnsOpType.CREATE,
                param={
                    "cluster_id": cluster.id,
                    "port": spider_port,
                    "add_ips": [h["ip"] for h in master_new],
                    "entry_role": [ClusterEntryRole.MASTER_ENTRY.value],
                },
            )
            if master_entry_sub:
                seg.add_sub_pipeline(sub_flow=master_entry_sub)
        if recover_slave:
            slave_entry_sub = BuildEntrysManageSubflow(
                root_id=self.root_id,
                ticket_data=self.data,
                op_type=DnsOpType.CREATE,
                param={
                    "cluster_id": cluster.id,
                    "port": spider_port,
                    "add_ips": [h["ip"] for h in slave_new],
                    "entry_role": [ClusterEntryRole.SLAVE_ENTRY.value],
                },
            )
            if slave_entry_sub:
                seg.add_sub_pipeline(sub_flow=slave_entry_sub)
        return seg.build_sub_process(sub_name=_("[{}] 域名恢复段").format(cluster.immute_domain))

    # ─────────────────────────────────────────────────────────────────────────
    # 段内复用的小辅助
    # ─────────────────────────────────────────────────────────────────────────
    def _add_schema_sync_acts(
        self,
        *,
        seg: SubBuilder,
        cluster: Cluster,
        primary_ctl_ip: str,
        spider_port: int,
        ctl_port: int,
        cluster_ticket: dict,
    ) -> None:
        """主中控机上 mysqldump 表结构，并由中控以 tc_admin=1 分发。"""
        shard_host, shard_port = get_shard_zero_remote_master(cluster)
        media_getter = GetFileList(db_type=DBType.MySQL)
        schema_media_list = media_getter.get_db_actuator_package() + media_getter.get_mysql_surrounding_apps_package(
            is_install_backup=True,
            is_install_monitor=False,
        )
        # 表结构任务仅在主中控机跑 dbactuator（mysqldump + mysql 客户端推 peer），其它 Spider 节点无需本机介质与临时备份工具
        seg.add_act(
            act_name=_("下发 actuator 与备份工具介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    exec_ip=[primary_ctl_ip],
                    file_list=schema_media_list,
                )
            ),
        )
        seg.add_act(
            act_name=_("安装临时备份程序[{}]").format(primary_ctl_ip),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    cluster={},
                    exec_ip=primary_ctl_ip,
                    bk_cloud_id=cluster.bk_cloud_id,
                    cluster_type=ClusterType.TenDBCluster.value,
                    run_as_system_user=DBA_ROOT_USER,
                    get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
                )
            ),
        )

        tdbctl_pass = cluster_ticket["tdbctl_pass"]
        schema_cluster_base = {
            "ctl_port": ctl_port,
            "spider_port": spider_port,
            "stream": False,
            "use_mydumper": False,
            "drop_before": False,
            "threads": 4,
            "shard_0_host": shard_host,
            "shard_0_port": shard_port,
            "tdbctl_user": TDBCTL_USER,
            "tdbctl_pass": tdbctl_pass,
            "is_spider_layer_disaster_recover": True,
        }
        seg.add_act(
            act_name=_("从 Remote 同步表结构至中控"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=primary_ctl_ip,
                    bk_cloud_id=cluster.bk_cloud_id,
                    cluster_type=ClusterType.TenDBCluster.value,
                    run_as_system_user=DBA_ROOT_USER,
                    get_mysql_payload_func=MysqlActPayload.get_import_schema_to_tdbctl_payload.__name__,
                    cluster=schema_cluster_base,
                )
            ),
        )

    def _maybe_add_priv_recover(
        self,
        *,
        seg: SubBuilder,
        cluster: Cluster,
        info: dict,
        target_role: str,
        restore_ips: List[str],
        spider_port: int,
        ctl_port: int,
    ) -> None:
        """从 spider/tdbctl grant 备份按 mysql_role 选择 restore_port，挂在指定 segment 上。

        @param target_role: 当前 segment 恢复的目标 spider 角色，用于过滤不兼容的备份角色。
                            slave 节点不部署中控，故 TDBCTL 角色备份对 slave 段无意义，应跳过。
        """
        # 缺省视为 from_spider_grant_backup，与 Serializer/Validator 默认值保持一致（兼容直调 FlowTestView）
        mode = info.get("privilege_recovery_mode") or "from_spider_grant_backup"
        if mode != "from_spider_grant_backup":
            logger.warning(
                _("集群 {} 的 {} 段跳过权限恢复：privilege_recovery_mode={} 非 from_spider_grant_backup").format(
                    cluster.id, target_role, mode
                )
            )
            return
        handler = MySQLBackupHandler(cluster_id=cluster.id, deadlines_days=7)
        backup_info = handler.get_tendbcluster_spider_layer_grant_priv_backup_info(
            spider_priv_backup_id=info.get("spider_priv_backup_id") or None,
        )
        if not backup_info:
            logger.warning(
                _(
                    "集群 {} 的 {} 段跳过权限恢复：{} 天内未找到 spider/tdbctl 的 grant 备份记录"
                    "（mysql_role in [spider_master, TDBCTL] 且 data_schema_grant=grant），"
                    "可先触发接入层 grant 备份或改用 account_rules_only 模式"
                ).format(cluster.id, target_role, handler.deadlines_days)
            )
            return
        role = (backup_info or {}).get("mysql_role") or ""
        # slave 节点无中控实例，TDBCTL 角色备份的 grant 文件按 ctl_port 恢复在 slave 上必然失败，跳过
        if target_role == TenDBClusterSpiderRole.SPIDER_SLAVE.value and str(role).upper() == "TDBCTL":
            logger.warning(_("集群 {} 的 spider_slave 段跳过 TDBCTL 角色 grant 备份恢复（slave 节点无中控实例）").format(cluster.id))
            return
        restore_port = ctl_port if str(role).upper() == "TDBCTL" else spider_port
        priv_sub = spider_layer_priv_recover_sub_flow(
            root_id=self.root_id,
            uid=str(self.data["uid"]),
            ticket_data=self.data,
            cluster_model=cluster,
            restore_ips=restore_ips,
            backup_info=backup_info,
            restore_port=int(restore_port),
        )
        if priv_sub:
            seg.add_sub_pipeline(sub_flow=priv_sub)

    @staticmethod
    def _build_role_summary_items(
        cluster: Cluster, spider_port: int, new_hosts: List[dict], old_hosts: List[dict]
    ) -> List[dict]:
        """按角色装配「实例变更明细」摘要行，对齐 InstanceChangeSummarySerializer 字段契约。

        新旧 IP 位置配对为 switch 行（related_instance=被替换旧实例）；数量不等时：
        多出的新机为 add 行、多出的旧机为 reduce 行。
        """
        items = []
        pair_count = min(len(new_hosts), len(old_hosts))
        for new_host, old_host in zip(new_hosts[:pair_count], old_hosts[:pair_count]):
            items.append(
                {
                    "cluster_domain": cluster.immute_domain,
                    "instance": f"{new_host['ip']}:{spider_port}",
                    "action": InstanceChangeAction.SWITCH.value,
                    "status": "success",
                    "related_instance": f"{old_host['ip']}:{spider_port}",
                }
            )
        for new_host in new_hosts[pair_count:]:
            items.append(
                {
                    "cluster_domain": cluster.immute_domain,
                    "instance": f"{new_host['ip']}:{spider_port}",
                    "action": InstanceChangeAction.ADD.value,
                    "status": "success",
                }
            )
        for old_host in old_hosts[pair_count:]:
            items.append(
                {
                    "cluster_domain": cluster.immute_domain,
                    "instance": f"{old_host['ip']}:{spider_port}",
                    "action": InstanceChangeAction.REDUCE.value,
                    "status": "success",
                }
            )
        return items

    @staticmethod
    def _build_dr_summary_items(
        cluster: Cluster,
        spider_port: int,
        master_new: List[dict],
        master_old: List[dict],
        slave_new: List[dict],
        slave_old: List[dict],
    ) -> List[dict]:
        """构建期装配执行摘要行（master + slave 合并）。

        必须在 flow 构建阶段调用：运行时 Stage 5 会清理旧实例的 db_meta 记录；
        master/slave 同集群同端口（spider 单机单实例），直接用 spider_port 拼 IP:Port。
        """
        return TenDBClusterSpiderLayerDisasterRecoverFlow._build_role_summary_items(
            cluster, spider_port, new_hosts=master_new, old_hosts=master_old
        ) + TenDBClusterSpiderLayerDisasterRecoverFlow._build_role_summary_items(
            cluster, spider_port, new_hosts=slave_new, old_hosts=slave_old
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 单集群编排：Pre-Stage + Stage 1-6（末段写入执行摘要：实例变更明细，新 IP ↔ 被替换旧 IP）
    # ─────────────────────────────────────────────────────────────────────────
    def _cluster_sub_flow(self, info: dict) -> Any:
        cluster = Cluster.objects.get(id=int(info["cluster_id"]), bk_biz_id=int(self.data["bk_biz_id"]))
        spider_port, ctl_port = resolve_spider_ctl_ports(cluster, info.get("spider_port"), info.get("ctl_port"))
        info = {**info, "spider_port": spider_port, "ctl_port": ctl_port}

        master_new = info.get("spider_master_new_ip_list") or []
        slave_new = info.get("spider_slave_new_ip_list") or []
        recover_master = bool(master_new)
        recover_slave = bool(slave_new)
        if not recover_master and not recover_slave:
            raise ValueError(
                _("集群 {} 的 info 未指定恢复目标：spider_master_new_ip_list 与 spider_slave_new_ip_list 均为空").format(cluster.id)
            )

        master_old = self._resolve_old_master_hosts(cluster, info) if recover_master else []
        slave_old = self._resolve_old_slave_hosts(cluster, info) if recover_slave else []

        # 构建期校验：新 master 至少 2 台不同机器（中控与 master 同机部署，不允许单点中控）
        if recover_master and len({h["ip"] for h in master_new}) < 2:
            raise ValueError(_("集群 {} 的 Spider Master 重建数量少于 2 台（不允许单点中控）").format(cluster.id))

        # 构建期校验：master 重建按"整层替换"处理，DBMeta 存量 master 必须全部在替换清单内
        if recover_master:
            dbmeta_master_ips = {
                p.machine.ip
                for p in cluster.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
                )
            }
            not_replaced = dbmeta_master_ips - {h["ip"] for h in master_old}
            if not_replaced:
                raise ValueError(
                    _("集群 {} 存在未纳入重建的 Spider Master（{}），请整层重建或改用节点替换单据").format(cluster.id, sorted(not_replaced))
                )

        # 重建 master 时，收集存活的保留节点（spider_slave/运维节点），Stage 2.5 重新纳入新中控；
        # master+slave 同时重建时，被替换的旧 slave 会下架，需排除（其新 slave 由 Stage 3 登记）
        retained_nodes: List[dict] = []
        if recover_master:
            retained_nodes = self._collect_retained_nodes(cluster, exclude_ips=[h["ip"] for h in slave_old])
        pkg_id = get_spider_pkg_id_for_layer_disaster_recover(cluster, int(self.data["bk_biz_id"]))
        for h in master_new:
            h["pkg_id"] = pkg_id
        for h in slave_new:
            h["pkg_id"] = pkg_id

        # 同时恢复时 primary_ctl_ip 取新 master 第 1 台；仅恢复 slave 时取 tdbctl primary
        if recover_master:
            primary_ctl_ip = master_new[0]["ip"]
        else:
            primary_ctl_ip = resolve_ctl_primary_ip(cluster)

        cluster_ticket = self._build_cluster_ticket(
            cluster=cluster,
            spider_port=spider_port,
            ctl_port=ctl_port,
            pkg_id=pkg_id,
            master_new=master_new,
            slave_new=slave_new,
        )

        sub_pipeline = SubBuilder(root_id=self.root_id, data=cluster_ticket)
        disable_manual_confirm = self.data.get("disable_manual_confirm", False)

        # ────── Pre-Stage：合并路由预览 + 起始 Pause + DNS 摘除 ──────
        self._add_pre_stage(
            sub_pipeline=sub_pipeline,
            cluster=cluster,
            master_new=master_new,
            slave_new=slave_new,
            master_old=master_old,
            slave_old=slave_old,
            spider_port=spider_port,
            ctl_port=ctl_port,
            info=info,
            disable_manual_confirm=disable_manual_confirm,
        )

        # ────── Stage 1：安装段（master / slave 并行） ──────
        install_segments = []
        if recover_master:
            install_segments.append(
                self._build_master_install_segment(
                    cluster=cluster,
                    new_masters=master_new,
                    pkg_id=pkg_id,
                    primary_ctl_ip=primary_ctl_ip,
                    cluster_ticket=cluster_ticket,
                )
            )
        if recover_slave:
            install_segments.append(
                self._build_slave_install_segment(
                    cluster=cluster,
                    new_slaves=slave_new,
                    pkg_id=pkg_id,
                    cluster_ticket=cluster_ticket,
                )
            )
        if len(install_segments) == 1:
            sub_pipeline.add_sub_pipeline(sub_flow=install_segments[0])
        else:
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=install_segments)

        # ────── Stage 2：master 路由段 ──────
        if recover_master:
            sub_pipeline.add_sub_pipeline(
                sub_flow=self._build_master_routing_segment(
                    cluster=cluster,
                    new_masters=master_new,
                    primary_ctl_ip=primary_ctl_ip,
                    spider_port=spider_port,
                    ctl_port=ctl_port,
                    info=info,
                    cluster_ticket=cluster_ticket,
                )
            )

        # ────── Stage 2.5：保留节点路由段（重建 master 且存在存活保留节点） ──────
        if retained_nodes:
            sub_pipeline.add_sub_pipeline(
                sub_flow=self._build_retained_nodes_segment(
                    cluster=cluster,
                    retained_nodes=retained_nodes,
                    primary_ctl_ip=primary_ctl_ip,
                    spider_port=spider_port,
                    ctl_port=ctl_port,
                    cluster_ticket=cluster_ticket,
                )
            )

        # ────── Stage 3：slave 路由段 ──────
        if recover_slave:
            sub_pipeline.add_sub_pipeline(
                sub_flow=self._build_slave_routing_segment(
                    cluster=cluster,
                    new_slaves=slave_new,
                    old_slaves=slave_old,
                    recover_master=recover_master,
                    primary_ctl_ip=primary_ctl_ip,
                    spider_port=spider_port,
                    ctl_port=ctl_port,
                    info=info,
                    cluster_ticket=cluster_ticket,
                )
            )

        # ────── 域名恢复段：目标拓扑（新节点 + 保留节点）全部登记并核对后，统一恢复域名解析 ──────
        sub_pipeline.add_sub_pipeline(
            sub_flow=self._build_dns_restore_segment(
                cluster=cluster,
                master_new=master_new,
                slave_new=slave_new,
                recover_master=recover_master,
                recover_slave=recover_slave,
                spider_port=spider_port,
            )
        )

        # ────── Stage 4：释放互斥锁 + 缩容确认 Pause ──────
        sub_pipeline.add_act(
            act_name=_("释放部分单据互斥锁"),
            act_component_code=AddUnlockTicketTypeConfigComponent.code,
            kwargs=asdict(
                AddUnLockTicketTypeKwargs(
                    cluster_ids=[cluster.id], unlock_ticket_type_list=self.temporary_unlock_ticket_type_list
                )
            ),
        )
        if not disable_manual_confirm:
            sub_pipeline.add_act(
                act_name=_("人工确认缩容旧接入层"),
                act_component_code=PauseWithTicketLockCheckComponent.code,
                kwargs=asdict(
                    ReleaseUnLockTicketTypeKwargs(
                        cluster_ids=[cluster.id],
                        release_unlock_ticket_type_list=self.temporary_unlock_ticket_type_list,
                    )
                ),
            )

        # ────── Stage 5：直接卸载旧节点（master 在前 / slave 在后） ──────
        # 不再做路由清理：重建 master 时新中控由 SpiderDRRoutingInitComponent 重新登记，路由表里不含旧节点；
        # 仅重建 slave 时，旧 slave 路由已在 Stage 3 由 DropSpiderRoutingComponent 定向清理；
        # DNS 摘除已在 Pre-Stage 做过；缩容确认 Pause 已在 Stage 4 做过；
        # 因此直接调底层 reduce_spiders_flow，只做：CC 服务实例清理 + 卸载 spider/ctl 进程 + 清理 DBMeta
        if recover_master:
            master_reduce_spiders = [{"ip": h["ip"]} for h in master_old]
            # reduce_spiders_flow 内 SpiderDBMeta.reduce_spider_nodes_apply 从 global_data["reduce_spiders"] 读取
            master_reduce_ctx = {**cluster_ticket, "reduce_spiders": master_reduce_spiders}
            sub_pipeline.add_sub_pipeline(
                sub_flow=reduce_spiders_flow(
                    cluster=cluster,
                    reduce_spiders=master_reduce_spiders,
                    root_id=self.root_id,
                    parent_global_data=master_reduce_ctx,
                    spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
                    is_disaster_recover=True,
                )
            )
        if recover_slave:
            slave_reduce_spiders = [{"ip": h["ip"]} for h in slave_old]
            slave_reduce_ctx = {**cluster_ticket, "reduce_spiders": slave_reduce_spiders}
            sub_pipeline.add_sub_pipeline(
                sub_flow=reduce_spiders_flow(
                    cluster=cluster,
                    reduce_spiders=slave_reduce_spiders,
                    root_id=self.root_id,
                    parent_global_data=slave_reduce_ctx,
                    spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value,
                    is_disaster_recover=True,
                )
            )

        # ────── Stage 6：写入执行摘要（实例变更明细：新 IP ↔ 被替换旧 IP） ──────
        # items 必须在构建期装配：运行时 Stage 5 已清理旧实例的 db_meta，届时反查端口必失败；
        # 同 instance 主键重复写入由 FlowOutputHandler 后写覆盖，天然幂等
        summary_items = self._build_dr_summary_items(
            cluster=cluster,
            spider_port=spider_port,
            master_new=master_new,
            master_old=master_old,
            slave_new=slave_new,
            slave_old=slave_old,
        )
        if summary_items:
            sub_pipeline.add_act(
                act_name=_("写入接入层重建摘要"),
                act_component_code=MysqlFlowOutputSummaryComponent.code,
                kwargs={"preset": "instance_change", "items": summary_items},
            )

        return sub_pipeline.build_sub_process(sub_name=_("[{}] 接入层灾难恢复").format(cluster.immute_domain))

    # ─────────────────────────────────────────────────────────────────────────
    # _cluster_sub_flow 内部小辅助
    # ─────────────────────────────────────────────────────────────────────────
    def _build_cluster_ticket(
        self,
        *,
        cluster: Cluster,
        spider_port: int,
        ctl_port: int,
        pkg_id: int,
        master_new: List[dict],
        slave_new: List[dict],
    ) -> dict:
        """构造统一上下文：master / slave 段共享 spider_port/ctl_port/pkg_id 等基础字段。"""
        cluster_ticket = copy.deepcopy(self.data)
        # spider_ip_list 历史字段：此处兼容指向 master_new（部分原子节点会读取）
        cluster_ticket.update(
            {
                "cluster_id": cluster.id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "spider_ip_list": master_new or slave_new,
                "global_pkg_id": pkg_id,
                "spider_port": spider_port,
                "ctl_port": ctl_port,
            }
        )
        mysql_ip_list, mysql_ports = build_mysql_ip_list_and_ports(cluster)
        cluster_ticket["mysql_ip_list"] = mysql_ip_list
        cluster_ticket["mysql_ports"] = mysql_ports
        return cluster_ticket

    def _add_pre_stage(
        self,
        *,
        sub_pipeline: SubBuilder,
        cluster: Cluster,
        master_new: List[dict],
        slave_new: List[dict],
        master_old: List[dict],
        slave_old: List[dict],
        spider_port: int,
        ctl_port: int,
        info: dict,
        disable_manual_confirm: bool,
    ) -> None:
        """合并路由预览 + 起始 Pause + 按角色摘除 DNS 旧 IP。"""
        preview = build_combined_route_preview(
            cluster=cluster,
            new_master_hosts=master_new,
            new_slave_hosts=slave_new,
            spider_port=spider_port,
            ctl_port=ctl_port,
            old_master_hosts=master_old,
            old_slave_hosts=slave_old,
        )
        sub_pipeline.add_act(
            act_name=_("路由预览（只读）"),
            act_component_code=SpiderLayerDisasterRecoverRoutePreviewComponent.code,
            kwargs={"route_preview": preview},
        )
        if not disable_manual_confirm:
            sub_pipeline.add_act(act_name=_("人工确认路由预览"), act_component_code=PauseComponent.code, kwargs={})

        if info.get("strip_dns_before_install", True):
            if master_new and master_old:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=BuildEntrysManageSubflow(
                        root_id=self.root_id,
                        ticket_data=self.data,
                        op_type=DnsOpType.RECYCLE_RECORD,
                        param={
                            "cluster_id": cluster.id,
                            "port": spider_port,
                            "del_ips": [h["ip"] for h in master_old],
                            "entry_role": [ClusterEntryRole.MASTER_ENTRY.value],
                        },
                    )
                )
            if slave_new and slave_old:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=BuildEntrysManageSubflow(
                        root_id=self.root_id,
                        ticket_data=self.data,
                        op_type=DnsOpType.RECYCLE_RECORD,
                        param={
                            "cluster_id": cluster.id,
                            "port": spider_port,
                            "del_ips": [h["ip"] for h in slave_old],
                            "entry_role": [ClusterEntryRole.SLAVE_ENTRY.value],
                        },
                    )
                )

    # ─────────────────────────────────────────────────────────────────────────
    # 入口
    # ─────────────────────────────────────────────────────────────────────────
    def spider_layer_disaster_recover(self):
        cluster_ids = slave_only_recover_cluster_ids(self.data["infos"])
        pipeline = Builder(
            root_id=self.root_id,
            data=self.data,
            need_random_pass_cluster_ids=cluster_ids or None,
        )
        sub_list = [self._cluster_sub_flow(info) for info in self.data["infos"]]
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_list)
        pipeline.run_pipeline_with_sidecar(
            check_ai_monitor_cluster_list=[int(i["cluster_id"]) for i in self.data["infos"]],
            init_trans_data_class=SystemInfoContext(),
        )
