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
from backend.db_meta.enums import ClusterEntryRole, ClusterType, TenDBClusterSpiderRole
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
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.add_system_user_in_cluster import (
    AddSystemUserInClusterComponent,
)
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.plugins.components.collections.spider.spider_layer_disaster_recover_route_preview import (
    SpiderLayerDisasterRecoverRoutePreviewComponent,
)
from backend.flow.utils.base.base_dataclass import AddUnLockTicketTypeKwargs, ReleaseUnLockTicketTypeKwargs
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSpiderSystemUserKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.flow.utils.spider.spider_disaster_recover import (
    build_append_deploy_style_routing_extend,
    build_combined_route_preview,
    build_mysql_ip_list_and_ports,
    get_shard_zero_remote_master,
    get_spider_pkg_id_for_layer_disaster_recover,
    resolve_running_ctl_ip_strict,
    resolve_spider_ctl_ports,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class TenDBClusterSpiderLayerDisasterRecoverFlow(TenDBClusterAddNodesFlow, TenDBClusterReduceNodesFlow):
    """
    ticket_data 与 TENDBCLUSTER_SPIDER_LAYER_DR 对齐 infos 列表，字段见单据 Serializer。

    支持三种恢复场景（由 info 中 spider_master_new_ip_list / spider_slave_new_ip_list 是否非空自动判定）：
      1. 仅恢复 spider_master：spider_master_new_ip_list 非空，spider_slave_new_ip_list 为空
      2. 仅恢复 spider_slave：spider_slave_new_ip_list 非空，spider_master_new_ip_list 为空
                              （要求中控 RUNNING 且 DRS 探活通过，由 Validator 与 Flow 双层校验）
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
        Stage 2 - master 路由段：DBMeta 写入 → 表结构同步 → 权限恢复 → init_tdbctl_routing(×2)。
        必须在 Stage 1 安装段完成后串行执行；slave 路由段必须等本段完成。

        DBMeta 写入提前到表结构同步之前：表结构同步内的"安装临时备份程序"会通过 ORM 查 Machine 表
        （get_install_tmp_db_backup_payload 取 machine_type / cluster_type），新机器必须先在 DBMeta 中。
        add_spiders 用 api.machine.create 写入，对重复 IP 幂等（重试单据安全）。
        """
        seg = SubBuilder(root_id=self.root_id, data=cluster_ticket)

        # 提前写入 DBMeta：让后续表结构同步 act 能从 Machine 表查到新机器
        seg.add_act(
            act_name=_("更新 DBMeta（新增 Spider Master）"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=SpiderDBMeta.add_spider_master_nodes_apply.__name__)),
        )

        if not info.get("skip_schema_sync", False):
            self._add_schema_sync_acts(
                seg=seg,
                cluster=cluster,
                new_masters=new_masters,
                primary_ctl_ip=primary_ctl_ip,
                spider_port=spider_port,
                ctl_port=ctl_port,
                cluster_ticket=cluster_ticket,
            )

        # master 段权限恢复（仅在 from_spider_grant_backup 模式下生效）
        self._maybe_add_priv_recover(
            seg=seg,
            cluster=cluster,
            info=info,
            target_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
            restore_ips=[h["ip"] for h in new_masters],
            spider_port=spider_port,
            ctl_port=ctl_port,
        )

        # 由 master 安装段写入；slave-only 场景不会进入本段
        tdbctl_pass = cluster_ticket["tdbctl_pass"]
        routing_extend = build_append_deploy_style_routing_extend(
            cluster=cluster,
            new_spider_hosts=new_masters,
            spider_port=spider_port,
            ctl_port=ctl_port,
            tdbctl_user=TDBCTL_USER,
            tdbctl_pass=tdbctl_pass,
        )
        routing_extend["only_init_ctl"] = True
        seg.add_act(
            act_name=_("初始化中控路由（仅中控）"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=primary_ctl_ip,
                    bk_cloud_id=cluster.bk_cloud_id,
                    cluster_type=ClusterType.TenDBCluster.value,
                    run_as_system_user=DBA_ROOT_USER,
                    get_mysql_payload_func=MysqlActPayload.get_init_tdbctl_routing_payload.__name__,
                    cluster=routing_extend,
                )
            ),
        )
        routing_extend["only_init_ctl"] = False
        seg.add_act(
            act_name=_("刷新 Spider 与分片路由"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=primary_ctl_ip,
                    bk_cloud_id=cluster.bk_cloud_id,
                    cluster_type=ClusterType.TenDBCluster.value,
                    run_as_system_user=DBA_ROOT_USER,
                    get_mysql_payload_func=MysqlActPayload.get_init_tdbctl_routing_payload.__name__,
                    cluster=routing_extend,
                )
            ),
        )
        return seg.build_sub_process(sub_name=_("[{}] master 路由段").format(cluster.immute_domain))

    def _build_slave_routing_segment(
        self,
        *,
        cluster: Cluster,
        new_slaves: List[dict],
        primary_ctl_ip: str,
        spider_port: int,
        ctl_port: int,
        info: dict,
        cluster_ticket: dict,
    ) -> Any:
        """
        Stage 3 - slave 路由段：主中控登记 slave 路由 + slave 权限恢复 + DBMeta。
        必须在 master 路由段完成后串行执行（依赖中控可用 + master DBMeta 已写入）。
        """
        seg = SubBuilder(root_id=self.root_id, data=cluster_ticket)
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
                    cluster={
                        "cluster_id": cluster.id,
                        "is_init_slave_cluster": True,
                        "add_spider_slaves": new_slaves,
                    },
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

    # ─────────────────────────────────────────────────────────────────────────
    # 段内复用的小辅助
    # ─────────────────────────────────────────────────────────────────────────
    def _add_schema_sync_acts(
        self,
        *,
        seg: SubBuilder,
        cluster: Cluster,
        new_masters: List[dict],
        primary_ctl_ip: str,
        spider_port: int,
        ctl_port: int,
        cluster_ticket: dict,
    ) -> None:
        """主中控机上 mysqldump 表结构 + 推送至 peer Spider。"""
        shard_host, shard_port = get_shard_zero_remote_master(cluster)
        spider_master_ips = [h["ip"] for h in new_masters]
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

        # 表结构同步只在 master 路由段调用，前置 master 安装段已写入 tdbctl_pass
        tdbctl_pass = cluster_ticket["tdbctl_pass"]
        # 上架 Spider 多于 1：主节点 mysqldump 一次后由 mysql 客户端推送到其它 Spider（spider_master_ips[1:] 可为空时仅灌主 Spider）
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
            "also_import_to_spider": True,
            "spider_peer_push_hosts": spider_master_ips[1:],
        }
        seg.add_act(
            act_name=_("从 Remote 同步表结构至中控、本机 Spider 并推送至其它 Spider（主）"),
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
            return
        handler = MySQLBackupHandler(cluster_id=cluster.id, deadlines_days=7)
        backup_info = handler.get_tendbcluster_spider_layer_grant_priv_backup_info(
            spider_priv_backup_id=info.get("spider_priv_backup_id") or None,
        )
        if not backup_info:
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

    # ─────────────────────────────────────────────────────────────────────────
    # 单集群编排：五阶段
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
        pkg_id = get_spider_pkg_id_for_layer_disaster_recover(cluster, int(self.data["bk_biz_id"]))
        for h in master_new:
            h["pkg_id"] = pkg_id
        for h in slave_new:
            h["pkg_id"] = pkg_id

        # 同时恢复时 primary_ctl_ip 取新 master 第 1 台；仅恢复 slave 时探活取现存中控
        if recover_master:
            primary_ctl_ip = master_new[0]["ip"]
        else:
            primary_ctl_ip = resolve_running_ctl_ip_strict(cluster)

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

        # ────── Stage 3：slave 路由段 ──────
        if recover_slave:
            sub_pipeline.add_sub_pipeline(
                sub_flow=self._build_slave_routing_segment(
                    cluster=cluster,
                    new_slaves=slave_new,
                    primary_ctl_ip=primary_ctl_ip,
                    spider_port=spider_port,
                    ctl_port=ctl_port,
                    info=info,
                    cluster_ticket=cluster_ticket,
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
        # 不再做路由清理 —— 新中控已被 init_tdbctl_routing 全量重建，旧节点路由已不存在；
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
        pipeline = Builder(
            root_id=self.root_id,
            data=self.data,
        )
        sub_list = [self._cluster_sub_flow(info) for info in self.data["infos"]]
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_list)
        pipeline.run_pipeline_with_sidecar(
            check_ai_monitor_cluster_list=[int(i["cluster_id"]) for i in self.data["infos"]],
            init_trans_data_class=SystemInfoContext(),
        )
