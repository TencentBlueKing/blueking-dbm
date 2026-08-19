# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging

from django.utils.translation import gettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.components.mysqldtsapi.types import (
    BinlogFilterRuleEntry,
    CreateSourceRequest,
    CreateTaskRequest,
    FullMigrateConfig,
    IncrMigrateConfig,
    MyLoaderConfig,
    RelayConfig,
    Source,
    SourceConfig,
    SourceConfItem,
    SpiderInfo,
    TableMigrateRule,
    TableMigrateSource,
    TableMigrateTarget,
    TargetConfig,
    TargetDBConfig,
    TargetSpiderConfig,
    TargetSpiderShard,
    Task,
    parse_dts_binlog_coord,
)
from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, MysqlDtsCluster, ProxyInstance, StorageInstance
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER
from backend.flow.utils.mysql.dts.constants import FullLoadEngine, MigrateType, get_full_migrate_data_dir
from backend.flow.utils.mysql.dts.migrate_credentials import DtsGrantTarget
from backend.flow.utils.mysql.dts.migrate_plan import (
    DtsMigratePlan,
    DtsTaskConfig,
    DtsTaskSpec,
    MyloaderSpec,
    SourceSpec,
    SyncScope,
    copy_myloader_spec,
)

logger = logging.getLogger("flow")


def resolve_source_endpoint(source_spec: SourceSpec, cluster: Cluster) -> tuple[str, int]:
    if source_spec.source_host:
        if IP_PORT_DIVIDER in source_spec.source_host:
            ip, port = source_spec.source_host.split(IP_PORT_DIVIDER, 1)
            return ip, int(port)
        return source_spec.source_host, 3306
    if source_spec.source_instance_id:
        ins = StorageInstance.objects.get(id=source_spec.source_instance_id, cluster=cluster)
        return ins.machine.ip, ins.port
    if source_spec.source_instance_role:
        ins = cluster.storageinstance_set.get(instance_role=source_spec.source_instance_role)
        return ins.machine.ip, ins.port

    # TenDBCluster：Source 必须落在 Remote 存储节点，不能用 Spider 代理探测/拉 binlog
    if cluster.cluster_type == ClusterType.TenDBCluster.value:
        ins = cluster.storageinstance_set.filter(instance_role=InstanceRole.REMOTE_MASTER).first()
        if not ins:
            raise ValueError(_("集群 {} 未找到可用的 Remote Master 源实例").format(cluster.id))
        return ins.machine.ip, ins.port

    # TenDBSingle：仅 orphan 存储实例
    if cluster.cluster_type == ClusterType.TenDBSingle.value:
        ins = cluster.storageinstance_set.filter(instance_role=InstanceRole.ORPHAN).first()
        if not ins:
            ins = cluster.storageinstance_set.first()
        if not ins:
            raise ValueError(_("集群 {} 未找到可用的源实例").format(cluster.id))
        return ins.machine.ip, ins.port

    ins = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_MASTER).first()
    if not ins:
        raise ValueError(_("集群 {} 未找到可用的 Master 源实例").format(cluster.id))
    return ins.machine.ip, ins.port


def _pick_shard_remote_instance(shard, instance_role=None) -> StorageInstance:
    """分片连接端点：默认 Remote Master（ejector）；指定 remote_slave 时用 receiver。"""
    receiver = shard.storage_instance_tuple.receiver
    ejector = shard.storage_instance_tuple.ejector
    role = getattr(instance_role, "value", instance_role) or ""
    if role == InstanceRole.REMOTE_SLAVE.value:
        if receiver is None:
            raise ValueError(_("分片 {} 未找到 Remote Slave").format(shard.shard_id))
        return receiver
    if ejector is None:
        raise ValueError(_("分片 {} 未找到 Remote Master").format(shard.shard_id))
    return ejector


def expand_tendbcluster_source_specs(
    source: SourceSpec,
    task_cfg: DtsTaskConfig | None = None,
) -> list[SourceSpec]:
    """将 TenDBCluster 源展开为 N 个 SourceSpec（一分片一 Source）。

    已带 shard_index 的 source 视为手工展开，原样返回。
    非 TenDBCluster 原样返回。
    """
    if source.shard_index is not None:
        return [source]

    cluster = Cluster.objects.get(id=source.cluster_id)
    if cluster.cluster_type != ClusterType.TenDBCluster.value:
        return [source]

    shards = list(cluster.tendbclusterstorageset_set.all().order_by("shard_id"))
    if not shards:
        raise ValueError(_("TenDBCluster {} 无分片元数据，无法展开 Source").format(cluster.id))

    shard_count = len(shards)
    spider_cluster_id = source.spider_cluster_id or cluster.immute_domain
    base_name = source.source_name or "source"
    use_myloader = False
    if task_cfg and task_cfg.full_load_engine == FullLoadEngine.MYLOADER.value:
        use_myloader = True
    if source.myloader is not None or (task_cfg and task_cfg.myloader is not None):
        use_myloader = True

    expanded: list[SourceSpec] = []
    for shard in shards:
        ins = _pick_shard_remote_instance(shard, source.source_instance_role)
        myloader = copy_myloader_spec(source.myloader)
        if myloader is None and task_cfg:
            myloader = copy_myloader_spec(task_cfg.myloader)
        if use_myloader:
            if myloader is None:
                myloader = MyloaderSpec()
            myloader.shard_id = shard.shard_id
        expanded.append(
            SourceSpec(
                cluster_id=source.cluster_id,
                source_name=f"{base_name}-{shard.shard_id}",
                sync_scope=source.sync_scope,
                source_instance_id=ins.id,
                source_instance_role=None,
                source_host=None,
                myloader=myloader,
                shard_index=shard.shard_id,
                shard_count=shard_count,
                spider_cluster_id=spider_cluster_id,
                worker_name=source.worker_name or "",
            )
        )
    return expanded


def assign_source_workers(
    sources: list[SourceSpec],
    worker_nodes: list[dict],
) -> None:
    """按 shard_index / 顺序为一对一绑定 worker_name 与 dest_worker_ip。"""
    if not sources:
        return
    if len(worker_nodes) < len(sources):
        raise ValueError(
            _("DTS Worker 数量({}) 少于 Source 数量({})，TenDBCluster 源需一分片一 Worker").format(len(worker_nodes), len(sources))
        )
    ordered = sorted(
        enumerate(sources),
        key=lambda item: (
            item[1].shard_index is None,
            item[1].shard_index if item[1].shard_index is not None else item[0],
        ),
    )
    for bind_idx, (unused_orig_idx, src) in enumerate(ordered):
        node = worker_nodes[bind_idx]
        name = node.get("name") or node.get("worker_name") or ""
        ip = node.get("ip") or ""
        if not name:
            raise ValueError(_("Worker 节点缺少 name，无法绑定 Source {}").format(src.source_name))
        src.worker_name = name
        if src.myloader is None:
            continue
        if not src.myloader.dest_worker_ip and ip:
            src.myloader.dest_worker_ip = ip


def _append_grant_target(targets: dict[str, DtsGrantTarget], cluster: Cluster, ip: str, port: int):
    address = "{}{}{}".format(ip, IP_PORT_DIVIDER, port)
    targets[address] = DtsGrantTarget(
        bk_cloud_id=cluster.bk_cloud_id,
        address=address,
        cluster_id=cluster.id,
        major_version=cluster.major_version or "",
    )


def _collect_target_grant_endpoints(cluster: Cluster, migrate_type: str) -> list[tuple[str, int]]:
    endpoints: list[tuple[str, int]] = []
    if migrate_type == MigrateType.HA_TO_CLUSTER.value or cluster.cluster_type == ClusterType.TenDBCluster.value:
        spider_masters = list(
            cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER)
        )
        for proxy in spider_masters:
            endpoints.append((proxy.machine.ip, proxy.port))
        # tdbctl 为中控主从复制，仅对 Primary 授权（勿对所有 spider 的 admin_port / 从中控授权）
        if spider_masters:
            endpoints.append(_resolve_tdbctl_endpoint(cluster, spider_masters[0]))
        for storage in cluster.storageinstance_set.filter(instance_role=InstanceRole.REMOTE_MASTER):
            endpoints.append((storage.machine.ip, storage.port))
        if not endpoints:
            proxy = cluster.proxyinstance_set.first()
            if proxy:
                endpoints.append((proxy.machine.ip, proxy.port))
    elif cluster.cluster_type == ClusterType.TenDBSingle.value:
        orphan = cluster.storageinstance_set.filter(instance_role=InstanceRole.ORPHAN).first()
        if not orphan:
            orphan = cluster.storageinstance_set.first()
        if not orphan:
            raise ValueError(_("集群 {} 未找到可用的目标实例").format(cluster.id))
        endpoints.append((orphan.machine.ip, orphan.port))
    else:
        master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
        endpoints.append((master.machine.ip, master.port))
    return endpoints


def collect_migrate_grant_targets(plan: DtsMigratePlan) -> list[DtsGrantTarget]:
    """收集迁移链路需在哪些 MySQL 实例上创建 DTS 临时账号。"""
    targets: dict[str, DtsGrantTarget] = {}
    for task_spec in plan.task_specs:
        for source_spec in task_spec.sources:
            cluster = Cluster.objects.get(id=source_spec.cluster_id)
            ip, port = resolve_source_endpoint(source_spec, cluster)
            _append_grant_target(targets, cluster, ip, port)
        target_cluster = Cluster.objects.get(id=task_spec.target_cluster_id)
        for ip, port in _collect_target_grant_endpoints(target_cluster, plan.migrate_type):
            _append_grant_target(targets, target_cluster, ip, port)
    return list(targets.values())


def _table_item_schema_table(item) -> tuple[str, str]:
    """兼容 do_tables/ignore_tables 的 dict 或 'db.table' 字符串。"""
    if isinstance(item, dict):
        schema = item.get("db") or item.get("schema") or item.get("dbname") or "*"
        table = item.get("table") or item.get("tablename") or "*"
        return schema, table
    if isinstance(item, str) and "." in item:
        schema, table = item.split(".", 1)
        return schema, table
    if isinstance(item, str):
        return "*", item
    return "*", "*"


def _build_table_migrate_rules(source_name: str, sync_scope: SyncScope) -> list[TableMigrateRule]:
    """将 sync_scope 转为 DTS table_migrate_rule。

    优先使用显式 table_routes；否则由 do_dbs/do_tables 生成白名单规则。
    ignore_dbs/ignore_tables 一期通过不生成对应规则实现（仅白名单模式）。
    """
    rules: list[TableMigrateRule] = []
    for route in sync_scope.table_routes:
        rules.append(
            TableMigrateRule(
                source=TableMigrateSource(
                    source_name=route.source_name or source_name,
                    schema=route.source_schema(),
                    table=route.source_table_name(),
                ),
                target=TableMigrateTarget(
                    schema=route.target_db or None,
                    table=route.target_table or None,
                ),
            )
        )
    if rules:
        return rules

    ignore_db_set = set(sync_scope.ignore_dbs or [])
    ignore_table_set = set()
    for item in sync_scope.ignore_tables or []:
        schema, table = _table_item_schema_table(item)
        ignore_table_set.add((schema, table))

    for db_name in sync_scope.do_dbs or []:
        if db_name in ignore_db_set:
            continue
        if ("*", "*") in ignore_table_set or (db_name, "*") in ignore_table_set:
            continue
        rules.append(
            TableMigrateRule(
                source=TableMigrateSource(source_name=source_name, schema=db_name, table="*"),
            )
        )

    for item in sync_scope.do_tables or []:
        schema, table = _table_item_schema_table(item)
        if schema in ignore_db_set:
            continue
        if (schema, table) in ignore_table_set or (schema, "*") in ignore_table_set:
            continue
        rules.append(
            TableMigrateRule(
                source=TableMigrateSource(source_name=source_name, schema=schema, table=table),
            )
        )
    return rules


def _build_binlog_filter_rules(sync_scope: SyncScope) -> dict[str, BinlogFilterRuleEntry]:
    rules = {}
    for item in sync_scope.binlog_filters:
        name = item.get("name", "")
        if not name:
            continue
        rules[name] = BinlogFilterRuleEntry(
            ignore_event=item.get("ignore_events", []),
            ignore_sql=item.get("ignore_sql", []),
        )
    return rules


def probe_instance_gtid_enabled(*, host: str, port: int, bk_cloud_id: int) -> bool:
    """探测单个 MySQL 实例 gtid_mode 是否为 ON。

    低版本无该变量 / DRS 失败 → False。
    """
    address = "{}{}{}".format(host, IP_PORT_DIVIDER, port)
    try:
        resp = DRSApi.rpc(
            {
                "addresses": [address],
                "cmds": ["SHOW GLOBAL VARIABLES LIKE 'gtid_mode';"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(_("探测实例 {} GTID 失败: {}").format(address, exc))
        return False

    if not resp:
        logger.warning(_("探测实例 {} GTID 返回为空").format(address))
        return False

    top_err = resp[0].get("error_msg") or ""
    cmd_results = resp[0].get("cmd_results") or []
    if top_err or not cmd_results:
        logger.warning(_("探测实例 {} GTID 失败: {}").format(address, top_err or _("无结果")))
        return False

    cmd_err = cmd_results[0].get("error_msg") or ""
    if cmd_err:
        logger.warning(_("探测实例 {} GTID 失败: {}").format(address, cmd_err))
        return False

    gtid_mode = ""
    for row in cmd_results[0].get("table_data") or []:
        if str(row.get("Variable_name", "")).lower() == "gtid_mode":
            gtid_mode = str(row.get("Value") or "").strip()
            break

    enabled = gtid_mode.upper() == "ON"
    logger.info(_("实例 {} gtid_mode={}").format(address, gtid_mode or _("无")))
    return enabled


def _collect_target_gtid_probe_endpoints(cluster: Cluster, migrate_type: str) -> list[tuple[str, int, int]]:
    """收集目标侧用于 GTID 探测的真实 MySQL 存储端点。

    TenDBCluster 不探测 Spider（代理上 gtid_mode 不可靠），只探测 RemoteDB。
    TenDBSingle 探测 ORPHAN；TenDBHA 探测 BACKEND_MASTER。
    """
    bk_cloud_id = cluster.bk_cloud_id
    endpoints: list[tuple[str, int, int]] = []
    if migrate_type == MigrateType.HA_TO_CLUSTER.value or cluster.cluster_type == ClusterType.TenDBCluster.value:
        for storage in cluster.storageinstance_set.filter(instance_role=InstanceRole.REMOTE_MASTER):
            endpoints.append((storage.machine.ip, storage.port, bk_cloud_id))
        if not endpoints:
            logger.warning(_("目标集群 {} 未找到 Remote Master，跳过目标 GTID 探测").format(cluster.id))
        return endpoints

    if cluster.cluster_type == ClusterType.TenDBSingle.value:
        orphan = cluster.storageinstance_set.filter(instance_role=InstanceRole.ORPHAN).first()
        if not orphan:
            orphan = cluster.storageinstance_set.first()
        if orphan:
            endpoints.append((orphan.machine.ip, orphan.port, bk_cloud_id))
        else:
            logger.warning(_("目标集群 {} 未找到可用实例，跳过目标 GTID 探测").format(cluster.id))
        return endpoints

    master = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_MASTER).first()
    if master:
        endpoints.append((master.machine.ip, master.port, bk_cloud_id))
    return endpoints


def decide_enable_gtid(
    *,
    source_host: str,
    source_port: int,
    source_cluster: Cluster,
    target_cluster: Cluster | None,
    migrate_type: str = "",
) -> bool:
    """跨版本/跨架构迁移时决定 Source.enable_gtid。

    DTS 的 enable_gtid 作用在读源 binlog；但跨版本场景下若目标无 GTID、源开 GTID，
    仍建议走 binlog 位点，避免后续运维/校验假设不一致。

    规则：源端 + 目标侧所有探测点均为 gtid_mode=ON 才返回 True；任一端 OFF/探测失败 → False。
    """
    source_ok = probe_instance_gtid_enabled(host=source_host, port=source_port, bk_cloud_id=source_cluster.bk_cloud_id)
    if not source_ok:
        logger.info(_("源端 {}:{} 未开启 GTID，enable_gtid=False").format(source_host, source_port))
        return False

    if not target_cluster:
        logger.warning(_("未传入目标集群，仅源端开启 GTID，为安全起见 enable_gtid=False"))
        return False

    target_eps = _collect_target_gtid_probe_endpoints(target_cluster, migrate_type)
    if not target_eps:
        logger.warning(_("目标集群 {} 无可用 GTID 探测点，enable_gtid=False").format(target_cluster.id))
        return False

    for host, port, bk_cloud_id in target_eps:
        if not probe_instance_gtid_enabled(host=host, port=port, bk_cloud_id=bk_cloud_id):
            logger.info(_("目标端 {}:{} 未开启 GTID（跨版本/混部），enable_gtid=False").format(host, port))
            return False

    logger.info(_("源/目标均已开启 GTID（目标探测点 {} 个），enable_gtid=True").format(len(target_eps)))
    return True


def task_mode_runs_incremental(task_mode: str | None) -> bool:
    """单据/plan 的 task_mode：仅纯 full 不会进 Sync。空默认按 all。"""
    return (task_mode or "").strip().lower() != "full"


def resolve_source_relay_enabled(source_resp) -> bool:
    """从 get_source 结果判断 Source 是否启用 relay。

    ``get_source_status.relay_status.master_binlog`` 未启用 relay 时也会返回上游位点，不能当判据；
    只有 ``relay_config.enable_relay`` 能区分。字段缺失按未启用处理。
    """
    relay_config = getattr(source_resp, "relay_config", None)
    if relay_config is None and isinstance(source_resp, dict):
        relay_config = source_resp.get("relay_config")
    if relay_config is None:
        return False
    enabled = getattr(relay_config, "enable_relay", None)
    if enabled is None and isinstance(relay_config, dict):
        enabled = relay_config.get("enable_relay")
    return bool(enabled)


def is_relay_not_enabled_error(exc: Exception) -> bool:
    """DTS 49001：source 无 relay worker，需先 enable-relay。relay 未启用不是清理失败。"""
    text = str(exc)
    return "49001" in text or "enable-relay" in text


def resolve_purge_relay_binlog_name(status_resp) -> str | None:
    """从 get_source_status 结果解析 purge_relay 所需文件名。

    ``relay_status.master_binlog`` 是位点串如 ``(mysql-bin.000005, 4)``，不能原样当文件名。
    解析失败返回 None，调用方跳过该 Source 的 purge。
    """
    data = getattr(status_resp, "data", None)
    if data is None and isinstance(status_resp, dict):
        data = status_resp.get("data")
    for item in data or []:
        relay_status = getattr(item, "relay_status", None)
        if relay_status is None and isinstance(item, dict):
            relay_status = item.get("relay_status")
        if relay_status is None:
            continue
        raw = getattr(relay_status, "master_binlog", None)
        if raw is None and isinstance(relay_status, dict):
            raw = relay_status.get("master_binlog")
        coord = parse_dts_binlog_coord(raw)
        if coord and coord.file:
            return coord.file
    return None


def build_create_source_request(
    source_spec: SourceSpec,
    cluster: Cluster,
    *,
    user: str,
    password: str,
    worker_name: str | None = None,
    target_cluster: Cluster | None = None,
    migrate_type: str = "",
    task_mode: str = "all",
) -> CreateSourceRequest:
    host, port = resolve_source_endpoint(source_spec, cluster)
    cluster_type = "mysql"
    spider: SpiderInfo | None = None
    # TenDBCluster：仅在已填分片元数据时下发 spider-shard + SpiderInfo（由 expand helper 填充）
    # 未展开时保持兼容：cluster_type=spider、无 SpiderInfo（现网 HA 单据不会走 Cluster 源）
    if cluster.cluster_type == ClusterType.TenDBCluster.value:
        if source_spec.shard_index is not None and source_spec.shard_count is not None:
            cluster_type = "spider-shard"
            spider = SpiderInfo(
                cluster_id=source_spec.spider_cluster_id or cluster.immute_domain,
                shard_index=int(source_spec.shard_index),
                shard_count=int(source_spec.shard_count),
            )
        else:
            cluster_type = "spider"
    enable_gtid = decide_enable_gtid(
        source_host=host,
        source_port=port,
        source_cluster=cluster,
        target_cluster=target_cluster,
        migrate_type=migrate_type,
    )
    bind_worker = worker_name or source_spec.worker_name or None
    relay_config = None
    if task_mode_runs_incremental(task_mode):
        relay_config = RelayConfig(enable_relay=True)
    source = Source(
        source_name=source_spec.source_name,
        host=host,
        port=port,
        user=user,
        password=password,
        enable_gtid=enable_gtid,
        enable=True,
        cluster_type=cluster_type,
        spider=spider,
        relay_config=relay_config,
    )
    return CreateSourceRequest(source=source, worker_name=bind_worker)


def _build_mysql_target_config(cluster: Cluster, user: str, password: str) -> TargetConfig:
    """TenDBHA / TenDBSingle 目标配置。"""
    if cluster.cluster_type == ClusterType.TenDBSingle.value:
        ins = cluster.storageinstance_set.filter(instance_role=InstanceRole.ORPHAN).first()
        if not ins:
            ins = cluster.storageinstance_set.first()
        if not ins:
            raise ValueError(_("集群 {} 未找到可用的目标实例").format(cluster.id))
    else:
        ins = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
    return TargetConfig(
        host=ins.machine.ip,
        port=ins.port,
        user=user,
        password=password,
        cluster_type="mysql",
    )


def _resolve_spider_master(cluster: Cluster) -> ProxyInstance:
    spider_master = cluster.proxyinstance_set.filter(
        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
    ).first()
    if not spider_master:
        spider_master = cluster.proxyinstance_set.first()
    if not spider_master:
        raise ValueError(_("集群 {} 未找到 Spider Master").format(cluster.id))
    return spider_master


def resolve_cluster_target_spider_endpoint(cluster: Cluster, target_spider: str | None = None) -> tuple[str, int]:
    """解析 TenDBCluster 目标 Spider 的 host/port，与 CreateTask 顶层地址一致。"""
    raw = (target_spider or "").strip()
    if raw:
        if IP_PORT_DIVIDER not in raw:
            raise ValueError(_("target_spider 格式必须为 ip:port"))
        ip, port_str = raw.split(IP_PORT_DIVIDER, 1)
        return ip.strip(), int(port_str.strip())
    spider_master = _resolve_spider_master(cluster)
    return spider_master.machine.ip, spider_master.port


def _resolve_tdbctl_endpoint(cluster: Cluster, spider_master: ProxyInstance) -> tuple[str, int]:
    """解析 tdbctl Primary 连接点。

    tdbctl 为中控主从复制，只应连接/授权 Primary。优先通过 tendbcluster_ctl_primary_address 探测；
    失败时再回退到 SPIDER_CTL 或 spider_master.admin_port / port+1000。
    """
    try:
        address = cluster.tendbcluster_ctl_primary_address()
        ip, port = address.split(IP_PORT_DIVIDER, 1)
        return ip, int(port)
    except Exception:  # pylint: disable=broad-except
        logger.warning(_("集群 {} 获取 tdbctl Primary 失败，使用元数据回退").format(cluster.id))

    ctl = cluster.proxyinstance_set.filter(
        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_CTL
    ).first()
    if ctl:
        port = ctl.admin_port or ctl.port
        return ctl.machine.ip, port

    port = spider_master.admin_port or (spider_master.port + 1000)
    return spider_master.machine.ip, port


def _build_cluster_target_config(
    cluster: Cluster, user: str, password: str, target_spider: str | None = None
) -> TargetConfig:
    # spider_master 仅作 tdbctl 回退锚点；顶层 host/port 优先用单据已校验的 target_spider
    spider_master = _resolve_spider_master(cluster)
    host, port = resolve_cluster_target_spider_endpoint(cluster, target_spider)
    tdbctl_host, tdbctl_port = _resolve_tdbctl_endpoint(cluster, spider_master)
    remote_masters = cluster.storageinstance_set.filter(instance_role=InstanceRole.REMOTE_MASTER)
    shards = [
        TargetSpiderShard(host=ins.machine.ip, port=ins.port, user=user, password=password) for ins in remote_masters
    ]
    spider_cfg = TargetSpiderConfig(
        tdbctl=TargetDBConfig(
            host=tdbctl_host,
            port=tdbctl_port,
            user=user,
            password=password,
        ),
        mode="proxy",
        shards=shards,
    )
    return TargetConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        cluster_type="spider",
        spider=spider_cfg,
    )


def build_target_config(
    target_cluster_id: int,
    migrate_type: str,
    user: str,
    password: str,
    target_spider: str | None = None,
) -> TargetConfig:
    cluster = Cluster.objects.get(id=target_cluster_id)
    if migrate_type == MigrateType.HA_TO_CLUSTER.value or cluster.cluster_type == ClusterType.TenDBCluster.value:
        return _build_cluster_target_config(cluster, user, password, target_spider=target_spider)
    return _build_mysql_target_config(cluster, user, password)


def apply_myloader_dirs_to_sources(task_spec: DtsTaskSpec, dirs: dict[str, str]) -> None:
    """将下发后的 myloader_dir 写回各 SourceSpec.myloader。"""
    for src in task_spec.sources:
        path = dirs.get(src.source_name)
        if not path:
            continue
        if src.myloader is None:
            from backend.flow.utils.mysql.dts.migrate_plan import MyloaderSpec

            src.myloader = MyloaderSpec()
        src.myloader.myloader_dir = path


def _resolve_myloader_task_mode(cfg_task_mode: str) -> str:
    mode = (cfg_task_mode or "").strip()
    if mode in ("myloader", "myloader&sync"):
        return mode
    if mode == "full":
        return "myloader"
    # all / incremental / 空 → 默认全量+增量
    return "myloader&sync"


def _build_myloader_config_for_source(src, cfg) -> MyLoaderConfig:
    from backend.flow.utils.mysql.dts.constants import DEFAULT_MYLOADER_PATH

    ml = src.myloader
    if ml is None:
        raise ValueError(_("source {} 使用 myloader 时必须提供 myloader 配置").format(src.source_name))
    if not ml.myloader_dir:
        raise ValueError(_("source {} 的 myloader_dir 为空，请先完成全备下发").format(src.source_name))
    path = ml.myloader_path or DEFAULT_MYLOADER_PATH
    return MyLoaderConfig(
        myloader_path=path,
        myloader_dir=ml.myloader_dir,
        myloader_threads=ml.threads or 16,
        myloader_regex=ml.regex or "",
        myloader_sourcedb=ml.sourcedb or "",
        myloader_tablelist=ml.tablelist or "",
        myloader_setnames=ml.setnames or "",
        myloader_defaultsfile=ml.defaultsfile or "",
        myloader_extraargs=ml.extraargs or "",
    )


def resolve_dts_cluster_id(plan, migrate_context) -> int | None:
    for obj in (plan, migrate_context):
        if obj is None:
            continue
        cid = getattr(obj, "dts_cluster_id", None)
        if cid:
            return int(cid)
    return None


def load_dts_cluster_name(dts_cluster_id: int) -> str | None:
    cluster = MysqlDtsCluster.objects.filter(id=dts_cluster_id).first()
    if not cluster or not cluster.name:
        return None
    return cluster.name


def build_full_migrate_config(cluster_name: str, task_name: str, user_full_migrate: dict | None) -> FullMigrateConfig:
    payload = dict(user_full_migrate or {})
    payload.pop("data_dir", None)
    payload["data_dir"] = get_full_migrate_data_dir(cluster_name, task_name)
    payload["disk_quota"] = "0"
    return FullMigrateConfig(**payload)


def build_dts_task_request(
    plan: DtsMigratePlan,
    task_spec: DtsTaskSpec,
    *,
    user: str,
    password: str,
    cluster_name: str | None = None,
) -> CreateTaskRequest:
    table_rules: list[TableMigrateRule] = []
    binlog_filters: dict[str, BinlogFilterRuleEntry] = {}
    for src in task_spec.sources:
        table_rules.extend(_build_table_migrate_rules(src.source_name, src.sync_scope))
        binlog_filters.update(_build_binlog_filter_rules(src.sync_scope))

    if not table_rules:
        # 引擎侧空 table_migrate_rule 等价于全库迁移，与「空 sync_scope=不同步」语义冲突，必须拦截
        raise ValueError(_("同步范围为空，拒绝创建 DTS 任务（空 table_migrate_rule 在引擎侧等价于全库迁移）"))

    target_cfg = task_spec.target_config
    if not target_cfg or not target_cfg.host:
        target_cfg = build_target_config(
            task_spec.target_cluster_id,
            plan.migrate_type,
            user,
            password,
            target_spider=task_spec.target_spider,
        )

    cfg = task_spec.dts_task_config
    use_myloader = cfg.full_load_engine == FullLoadEngine.MYLOADER.value

    if use_myloader:
        myloaders: dict[str, MyLoaderConfig] = {}
        source_conf: list[SourceConfItem] = []
        for src in task_spec.sources:
            conf_name = f"myloader-{src.source_name}"
            myloaders[conf_name] = _build_myloader_config_for_source(src, cfg)
            source_conf.append(SourceConfItem(source_name=src.source_name, myloader_config_name=conf_name))
        task_mode = _resolve_myloader_task_mode(cfg.task_mode)
        source_config = SourceConfig(
            source_conf=source_conf,
            full_migrate_conf=None,
            incr_migrate_conf=IncrMigrateConfig(**cfg.incr_migrate) if cfg.incr_migrate else None,
            myloaders=myloaders,
        )
    else:
        if not cluster_name:
            raise ValueError(_("builtin 全量缺少 DTS 集群名，无法生成 dump data_dir"))
        source_conf = [SourceConfItem(source_name=src.source_name) for src in task_spec.sources]
        task_mode = cfg.task_mode
        source_config = SourceConfig(
            source_conf=source_conf,
            full_migrate_conf=build_full_migrate_config(cluster_name, task_spec.task_name, cfg.full_migrate),
            incr_migrate_conf=IncrMigrateConfig(**cfg.incr_migrate) if cfg.incr_migrate else None,
        )

    task = Task(
        name=task_spec.task_name,
        task_mode=task_mode,
        shard_mode=cfg.shard_mode or "",
        on_duplicate=cfg.on_duplicate,
        meta_schema=cfg.meta_schema,
        ignore_checking_items=cfg.ignore_checking_items,
        target_config=target_cfg,
        source_config=source_config,
        table_migrate_rule=table_rules,
        binlog_filter_rule=binlog_filters,
    )
    return CreateTaskRequest(task=task)


def build_ticket_dts_clean_names(migrate_plan: DtsMigratePlan) -> tuple[list[str], list[str]]:
    """从建流期 migrate_plan 收集本单 task_name / source_name（去重保序）。

    用于成功路径 dts-task-clean；**不**调用 Master list_tasks / list_sources。
    名称语义与 MysqlDtsInfo.dts_task_id / dts_source_names 对齐（register/create 通常回写同源名）。
    """
    task_names: list[str] = []
    source_names: list[str] = []
    seen_tasks: set[str] = set()
    seen_sources: set[str] = set()
    for spec in migrate_plan.task_specs or []:
        task_name = (getattr(spec, "task_name", None) or "").strip()
        if task_name and task_name not in seen_tasks:
            seen_tasks.add(task_name)
            task_names.append(task_name)
        for src in getattr(spec, "sources", None) or []:
            source_name = (getattr(src, "source_name", None) or "").strip()
            if source_name and source_name not in seen_sources:
                seen_sources.add(source_name)
                source_names.append(source_name)
    return task_names, source_names
