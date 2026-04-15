# TenDBCluster 接入层全毁灾难恢复 —— Spider Slave 角色扩展设计

## 背景

当前 `TENDBCLUSTER_SPIDER_LAYER_DISASTER_RECOVER` 单据 + `TenDBClusterSpiderLayerDisasterRecoverFlow` 仅支持 **Spider Master**（主接入层 + 中控）的全毁冷恢复。生产场景中存在两类全毁，希望复用同一单据：

| 场景 | 现有支持 | 本设计目标 |
|---|---|---|
| Spider Master 接入层全毁 | ✅ | 维持不变 |
| Spider Slave  接入层全毁 | ❌ | **新增** |
| 同集群 Master + Slave 同时全毁 | ❌ | **新增**（同 info 内串行编排） |

## 核心决策

| 决策点 | 方案 | 理由 |
|---|---|---|
| 角色识别 | **不引入 `spider_role` 字段，由 IP 列表非空自动判断** | 参数自描述，最简洁 |
| 字段必填 | 4 个角色 IP 列表全部 `required=False`，由 Validator 按"new 非空 → old 必填且严格"约束 | 灵活，不强迫无关字段 |
| 同时恢复 | **两阶段同步编排**：阶段 1 master/slave **安装段并行** → 阶段 2 master 路由段串行 → 阶段 3 slave 路由段串行 → 阶段 4-5 缩容确认 + 缩容 | 节省 3-5 分钟安装时间，路由阶段保持必要的串行 |
| UX | **1 个起始 Pause（合并路由预览）+ 1 个缩容 Pause（同时确认旧 master/slave 下架）** | 减少人工干预次数 |
| 字段命名 | 硬切，删除旧 `spider_new_ip_list` / `spider_old_ip_list` | master 流程未灰度上线，无兼容负担 |
| 安装并行可行性 | `InstallSpiderWithCopyConfigService` 已自动处理"集群无同角色 RUNNING spider"场景（拉默认配置），冷恢复天然兼容 | 见 `install_spider_with_copy_config.py:173-176` |
| **仅恢复 slave 时的中控正常性校验** | **Validator 单点 L1+L3 双层校验**：① DBMeta `status=RUNNING` ② DRS 在中控 `admin_port` 上 `select @@version` 探活成功。运行时不重复（接受单据排队期间中控失活的风险，由 Stage 3 失败兜底） | 中控失活会导致 Stage 3 `add_spider_slave_routing_payload` 必败，前置校验避免无效流程；运行时再校验成本高、收益低 |

## 与 Master 流程的差异

| 维度 | Spider Master | Spider Slave |
|---|---|---|
| 节点构成 | Spider + TDBCTL 中控（共机） | 仅 Spider Slave，**无中控** |
| 表结构同步 | 必需（mysqldump from Remote shard 0 → 中控 + Spider） | **跳过**，slave 直读 Remote DR |
| 路由初始化 | `get_init_tdbctl_routing_payload`（写入中控） | `add_spider_slave_routing_payload(is_init_slave_cluster=True)`（在主中控登记） |
| 中控依赖 | 自身就是中控 | **依赖主集群中控可用** |
| DBMeta | `add_spider_master_nodes_apply` | `add_spider_slave_nodes_apply` |
| 域名 | MASTER_ENTRY | SLAVE_ENTRY |
| 权限恢复 | 复用 `spider_layer_priv_recover_sub_flow` | 同上（按 `restore_ips + restore_port`） |
| 缩容旧节点 | `reduce_spider_nodes_with_cluster(SPIDER_MASTER)` | `reduce_spider_nodes_with_cluster(SPIDER_SLAVE)` |

## 详细设计

### 1. 单据 Serializer 改造

文件：`backend/ticket/builders/tendbcluster/tendb_spider_layer_disaster_recover.py`

```python
class InfoSerializer(serializers.Serializer):
    cluster_id = IntegerField(...)

    # 4 个 IP 列表全部可选，由"非空"自描述本次恢复哪些角色
    spider_master_new_ip_list = ListSerializer(child=HostInfoSerializer(), required=False, default=list)
    spider_master_old_ip_list = ListSerializer(child=HostInfoSerializer(), required=False, default=list)
    spider_slave_new_ip_list  = ListSerializer(child=HostInfoSerializer(), required=False, default=list)
    spider_slave_old_ip_list  = ListSerializer(child=HostInfoSerializer(), required=False, default=list)

    privilege_recovery_mode  = ChoiceField(...)        # 不变
    spider_priv_backup_id    = CharField(required=False, allow_blank=True)
    strip_dns_before_install = BooleanField(default=True)
    skip_schema_sync         = BooleanField(default=False)   # 仅 master 段生效
    spider_port              = IntegerField(required=False, allow_null=True)
    ctl_port                 = IntegerField(required=False, allow_null=True)  # 仅 master 段生效
```

**删除字段**：`spider_new_ip_list` / `spider_old_ip_list`。

**判断逻辑**（Flow / Validator 共用）：

```python
recover_master = bool(info.get("spider_master_new_ip_list"))
recover_slave  = bool(info.get("spider_slave_new_ip_list"))
```

### 2. Validator 严格模式

文件：`backend/flow/engine/bamboo/scene/spider/validate/spider_layer_disaster_recover_validate.py`

```python
def run_check_for_info(self, info, index):
    # 通用：cluster 存在、cluster_type、can_access、privilege_recovery_mode、spider_port/ctl_port 解析
    ...

    master_new = info.get("spider_master_new_ip_list") or []
    master_old = info.get("spider_master_old_ip_list") or []
    slave_new  = info.get("spider_slave_new_ip_list")  or []
    slave_old  = info.get("spider_slave_old_ip_list")  or []

    # 至少恢复一种角色
    if not master_new and not slave_new:
        error_msg_list.append(_("spider_master_new_ip_list 与 spider_slave_new_ip_list 不能同时为空"))
        return error_msg_list

    # master 段约束
    if master_new:
        # IP 可用
        ...
        # old 必填且严格匹配元数据
        if not master_old:
            error_msg_list.append(_("spider_master_new_ip_list 非空时 spider_master_old_ip_list 必填"))
        else:
            meta_master_ips = set(ProxyInstance.objects.filter(
                cluster=cluster,
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
            ).values_list("machine__ip", flat=True))
            for h in master_old:
                if h["ip"] not in meta_master_ips:
                    error_msg_list.append(_("spider_master_old_ip_list 中 IP {} 不在 SPIDER_MASTER 元数据中").format(h["ip"]))
    else:
        if master_old:
            error_msg_list.append(_("spider_master_new_ip_list 为空时不允许提供 spider_master_old_ip_list"))

    # slave 段约束
    if slave_new:
        # IP 可用
        ...
        # old 必填且严格匹配元数据
        if not slave_old:
            error_msg_list.append(_("spider_slave_new_ip_list 非空时 spider_slave_old_ip_list 必填"))
        else:
            meta_slave_ips = set(ProxyInstance.objects.filter(
                cluster=cluster,
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value,
            ).values_list("machine__ip", flat=True))
            for h in slave_old:
                if h["ip"] not in meta_slave_ips:
                    error_msg_list.append(_("spider_slave_old_ip_list 中 IP {} 不在 SPIDER_SLAVE 元数据中").format(h["ip"]))

        # ──────────────────────────────────────────────────────────────────
        # 【仅恢复 slave】时强制要求中控存活且正常（L1 + L3 双层校验）
        # 同时恢复 master+slave 时跳过：中控会被 master 段重建，无需校验现存中控
        # L1: DBMeta status=RUNNING
        # L3: DRS 在中控 admin_port 上探活（select @@version），用 drs_account 连接
        # ──────────────────────────────────────────────────────────────────
        if not master_new:
            running_ctls = ProxyInstance.objects.filter(
                cluster=cluster,
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
                status=InstanceStatus.RUNNING,
            )
            if not running_ctls:
                error_msg_list.append(_("仅恢复 spider_slave 时 DBMeta 中无 RUNNING 中控（spider_master）"))
            else:
                alive_ctl_ip = self._probe_running_ctl_via_drs(cluster, running_ctls)
                if not alive_ctl_ip:
                    error_msg_list.append(_(
                        "仅恢复 spider_slave 时所有中控（spider_master.admin_port）DRS 探活均失败，"
                        "请确认中控进程与端口正常"
                    ))

        slave_entry_exists = ClusterEntry.objects.filter(
            cluster=cluster, role=ClusterEntryRole.SLAVE_ENTRY.value,
        ).exists()
        if not slave_entry_exists:
            error_msg_list.append(_("集群 {} 不存在 SLAVE_ENTRY 从域名").format(cluster.id))
    else:
        if slave_old:
            error_msg_list.append(_("spider_slave_new_ip_list 为空时不允许提供 spider_slave_old_ip_list"))

    # 同时恢复时：master/slave 新 IP 不允许重叠（同一台机器不能既装 master 又装 slave）
    if master_new and slave_new:
        master_ip_set = {h["ip"] for h in master_new}
        slave_ip_set  = {h["ip"] for h in slave_new}
        overlap = master_ip_set & slave_ip_set
        if overlap:
            error_msg_list.append(
                _("spider_master_new_ip_list 与 spider_slave_new_ip_list 存在重叠 IP: {}").format(sorted(overlap))
            )


def _probe_running_ctl_via_drs(self, cluster, running_ctls):
    """
    探活集群中控（spider_master.admin_port），返回第 1 个能成功响应的中控 IP；全部失败返回 None。

    L3 校验：通过 DRS 用 drs_account 连接中控的 admin_port 执行 `select @@version`。
    drs_account 是 DRS 内置的高权账号，在中控初始化时就已下发，无需用户提供 tdbctl_pass。

    参考 `add_spider_routing.py:80` 中 DRS 直接读 mysql.servers 的现有用法。
    """
    from backend.components import DRSApi
    for ctl in running_ctls:
        ctl_address = "{}:{}".format(ctl.machine.ip, ctl.admin_port)
        try:
            res = DRSApi.rpc({
                "addresses": [ctl_address],
                "cmds": ["select @@version"],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            })
            if res and not res[0].get("error_msg"):
                return ctl.machine.ip
        except Exception:
            continue
    return None
```

### 3. Flow 编排（统一 `_cluster_sub_flow`，五阶段编排）

文件：`backend/flow/engine/bamboo/scene/spider/spider_layer_disaster_recover_flow.py`

`_cluster_sub_flow` 内部按"安装并行 + 路由串行"五阶段组织：

```python
def _cluster_sub_flow(self, info):
    cluster = Cluster.objects.get(id=int(info["cluster_id"]), bk_biz_id=int(self.data["bk_biz_id"]))

    master_new = info.get("spider_master_new_ip_list") or []
    master_old = info.get("spider_master_old_ip_list") or []
    slave_new  = info.get("spider_slave_new_ip_list")  or []
    slave_old  = info.get("spider_slave_old_ip_list")  or []

    recover_master = bool(master_new)
    recover_slave  = bool(slave_new)

    spider_port, ctl_port = resolve_spider_ctl_ports(cluster, info.get("spider_port"), info.get("ctl_port"))
    pkg_id = get_spider_pkg_id_for_layer_disaster_recover(cluster, int(self.data["bk_biz_id"]))
    primary_ctl_ip = master_new[0]["ip"] if recover_master else _resolve_running_ctl_ip(cluster)

    # 构造统一上下文（master 与 slave 共享 spider_port/ctl_port/pkg_id/cluster_ticket）
    cluster_ticket = copy.deepcopy(self.data)
    cluster_ticket.update({...})

    sub_pipeline = SubBuilder(root_id=self.root_id, data=cluster_ticket)

    # ────────────────── Pre-Stage: 合并路由预览 + 起始 Pause + DNS 摘除 ──────────────────
    preview = build_combined_route_preview(
        cluster=cluster,
        new_master_hosts=master_new,
        new_slave_hosts=slave_new,
        spider_port=spider_port, ctl_port=ctl_port,
    )
    sub_pipeline.add_act(act_name=_("路由预览（只读）"), ..., kwargs={"route_preview": preview})

    if not disable_manual_confirm:
        sub_pipeline.add_act(act_name=_("人工确认路由预览"), act_component_code=PauseComponent.code, kwargs={})

    # DNS 摘除（master 走主域名、slave 走从域名；两者无依赖，顺序排放即可）
    if recover_master and strip_dns and master_old:
        sub_pipeline.add_sub_pipeline(BuildEntrysManageSubflow(... entry_role=[MASTER_ENTRY] ...))
    if recover_slave and strip_dns and slave_old:
        sub_pipeline.add_sub_pipeline(BuildEntrysManageSubflow(... entry_role=[SLAVE_ENTRY] ...))

    # ────────────────── Stage 1: 安装段并行（master + slave）──────────────────
    install_segments = []
    if recover_master:
        install_segments.append(self._build_master_install_segment(
            cluster=cluster, new_masters=master_new, pkg_id=pkg_id, cluster_ticket=cluster_ticket,
        ))
    if recover_slave:
        install_segments.append(self._build_slave_install_segment(
            cluster=cluster, new_slaves=slave_new, pkg_id=pkg_id, cluster_ticket=cluster_ticket,
        ))

    if len(install_segments) == 1:
        sub_pipeline.add_sub_pipeline(install_segments[0])
    elif len(install_segments) == 2:
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=install_segments)   # 并行汇聚

    # ────────────────── Stage 2: master 路由段（必须串行）──────────────────
    if recover_master:
        sub_pipeline.add_sub_pipeline(self._build_master_routing_segment(
            cluster=cluster, new_masters=master_new, primary_ctl_ip=primary_ctl_ip,
            spider_port=spider_port, ctl_port=ctl_port, info=info, cluster_ticket=cluster_ticket,
        ))

    # ────────────────── Stage 3: slave 路由段（依赖中控，紧跟 master 之后）──────────────────
    if recover_slave:
        sub_pipeline.add_sub_pipeline(self._build_slave_routing_segment(
            cluster=cluster, new_slaves=slave_new, primary_ctl_ip=primary_ctl_ip,
            spider_port=spider_port, info=info, cluster_ticket=cluster_ticket,
        ))

    # ────────────────── Stage 4: 释放互斥锁 + 缩容确认 Pause ──────────────────
    sub_pipeline.add_act(
        act_name=_("释放部分单据互斥锁"),
        act_component_code=AddUnlockTicketTypeConfigComponent.code,
        kwargs=asdict(AddUnLockTicketTypeKwargs(
            cluster_ids=[cluster.id], unlock_ticket_type_list=self.temporary_unlock_ticket_type_list,
        )),
    )
    if not disable_manual_confirm:
        sub_pipeline.add_act(
            act_name=_("人工确认缩容旧接入层"),
            act_component_code=PauseWithTicketLockCheckComponent.code,
            kwargs=asdict(ReleaseUnLockTicketTypeKwargs(...)),
        )

    # ────────────────── Stage 5: 缩容（master 在前、slave 在后，避免对中控同时操作）──────────────────
    if recover_master:
        sub_pipeline.add_sub_pipeline(self.reduce_spider_nodes_with_cluster(
            ..., reduce_spider_role=SPIDER_MASTER, spider_reduced_hosts=master_old,
        ))
    if recover_slave:
        sub_pipeline.add_sub_pipeline(self.reduce_spider_nodes_with_cluster(
            ..., reduce_spider_role=SPIDER_SLAVE, spider_reduced_hosts=slave_old,
        ))

    return sub_pipeline.build_sub_process(sub_name=_("[{}] 接入层灾难恢复").format(cluster.immute_domain))
```

### 4. 4 个 segment 拆分（安装段 + 路由段 各 2 个）

把原 `_cluster_sub_flow` 拆成 **4 个细粒度 segment**，便于安装段并行编排：

#### 4.1 `_build_master_install_segment`（可与 slave 安装段并行）

```
M1. add_spider_masters_sub_flow(cold_disaster_recover=True)
M2. Remote 与接入层内置账号授权
```

不含表结构同步与路由初始化 —— 这些放在路由段，避免与 slave 安装段并行时的冲突。

#### 4.2 `_build_slave_install_segment`（可与 master 安装段并行）

```
S1. add_spider_slaves_sub_flow(cold_disaster_recover=True)
    ├─ cold 模式：跳过 add_spider_slave_routing 节点（路由由 4.4 步骤 S2 统一登记）
    ├─ cold 模式：跳过权限克隆（强制 is_clone_user=False；冷场景无源 slave 可克隆）
    └─ cold 模式：跳过 BuildEntrysManageSubflow / slave_domain（DNS 由上层 Pre-Stage 处理）
```

**安装并行可行性确认**（来自 `install_spider_with_copy_config.py:173-176`）：
当集群中无 RUNNING 同角色 spider 时，`InstallSpiderWithCopyConfigService` 自动跳过克隆配置，从 bk-config 拉默认配置安装 → 冷恢复场景天然兼容。master/slave 两段安装时互不读取对方实例。

#### 4.3 `_build_master_routing_segment`（必须在安装段之后，slave 路由段之前）

```
M3. (可选) 表结构同步（skip_schema_sync 控制）
M4. (可选) spider_layer_priv_recover_sub_flow（master 权限恢复）
M5. init_tdbctl_routing(only_init_ctl=True)         → 中控可用
M6. init_tdbctl_routing(only_init_ctl=False)         → 刷新 Spider 与分片路由
M7. SpiderDBMeta.add_spider_master_nodes_apply
```

#### 4.4 `_build_slave_routing_segment`（必须在 master 路由段之后）

```
S2. 主中控登记新 slave 路由
    ExecuteDBActuatorScriptComponent + MysqlActPayload.add_spider_slave_routing_payload
    exec_ip = primary_ctl_ip   # 同时恢复时为新 master 中控；仅恢复 slave 时为现存 RUNNING 中控
    cluster.is_init_slave_cluster = True
    cluster.add_spider_slaves     = new_slaves
S3. (可选) spider_layer_priv_recover_sub_flow(restore_ips=new_slaves, restore_port=spider_port)
S4. SpiderDBMeta.add_spider_slave_nodes_apply
```

**释放互斥锁的位置**：从原 master segment 末尾移到 `_cluster_sub_flow` 的 Stage 4，与缩容确认 Pause 配对，确保即使只恢复 slave 也会执行。

### 6. `add_spider_slaves_sub_flow` 改造

文件：`backend/flow/engine/bamboo/scene/spider/common/common_sub_flow.py`

新增参数 `cold_disaster_recover: bool = False`，与 `add_spider_masters_sub_flow` 对齐：

```python
def add_spider_slaves_sub_flow(
    uid, cluster, add_spider_slaves, root_id, parent_global_data,
    is_clone_user=True, slave_domain=None, global_pkg_id=0, new_db_module_id=0,
    cold_disaster_recover: bool = False,   # 新增
):
    if cold_disaster_recover:
        spider_port = int(parent_global_data["spider_port"])
        is_clone_user = False
    else:
        # 现有逻辑
        ...

    parent_global_data["spider_ports"] = [spider_port]
    ...

    # cold 模式跳过的 act：
    if not cold_disaster_recover:
        sub_pipeline.add_act(... AddSpiderRoutingComponent ...)   # 路由由上层统一登记
    if is_clone_user:
        ...   # 权限克隆
    if slave_domain:
        sub_pipeline.add_act(... MySQLDnsManageComponent ...)
    elif not cold_disaster_recover:
        sub_pipeline.add_sub_pipeline(BuildEntrysManageSubflow(...))   # cold 模式 DNS 由上层处理
```

### 7. helper 改造

文件：`backend/flow/utils/spider/spider_disaster_recover.py`

- 新增 `build_combined_route_preview(cluster, new_master_hosts, new_slave_hosts, spider_port, ctl_port)` —— 同时支持 master / slave 两组的合并预览。当 `new_slave_hosts` 为空时退化为现有 master 预览。
- `get_spider_pkg_id_for_layer_disaster_recover(cluster, bk_biz_id)` —— 不变（master / slave 共用同一 pkg）。
- 新增 `_resolve_running_ctl_ip(cluster)` —— 仅恢复 slave 时使用，遍历 RUNNING `SPIDER_MASTER` 通过 DRS 在 `admin_port` 上 `select @@version` 探活，返回第 1 个成功的中控 IP；全部失败抛 `FlowParamException`。**与 Validator 中 `_probe_running_ctl_via_drs` 共用同一探活实现**（抽到 `spider_disaster_recover.py`，避免重复）。

## 流程图（同时恢复场景的五阶段编排）

```
                  ┌────────────────────────────────────────────────────┐
                  │           spider_layer_disaster_recover()           │
                  └────────────────────────────────────────────────────┘
                                          │
                              for info in self.data["infos"]
                                          │
                                          ▼
                            ┌─────────────────────────────┐
                            │ Pre-Stage                   │
                            │  1. 合并路由预览(master+slave)│
                            │  2. 人工确认(唯一起始 Pause) │
                            │  3. DNS 摘除                │
                            │     if master:MASTER_ENTRY  │
                            │     if slave :SLAVE_ENTRY   │
                            └─────────────────────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────────────────┐
                            │ Stage 1: 安装段并行                  │
                            │ ┌──────────────────────────────┐    │
                            │ │ master_install_segment       │    │
                            │ │   M1. add_spider_masters     │    │
                            │ │       (cold_disaster_recover)│    │
                            │ │   M2. Remote 内置账号授权    │    │
                            │ └──────────────────────────────┘    │
                            │ ┌──────────────────────────────┐    │
                            │ │ slave_install_segment        │    │
                            │ │   S1. add_spider_slaves      │    │
                            │ │       (cold_disaster_recover)│    │
                            │ └──────────────────────────────┘    │
                            │              ↓                       │
                            │         汇聚同步点                    │
                            └─────────────────────────────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────────┐
                            │ Stage 2: master 路由段(串行) │
                            │   M3. (可选) 表结构同步      │
                            │   M4. (可选) master 权限恢复 │
                            │   M5. init_tdbctl(only_ctl)  │ ← 中控可用
                            │   M6. init_tdbctl(refresh)   │
                            │   M7. add_master DBMeta      │ ← 同步点 2
                            └─────────────────────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────────┐
                            │ Stage 3: slave 路由段(串行)  │
                            │   S2. 中控登记 slave 路由    │ ← 依赖中控+master DBMeta
                            │   S3. (可选) slave 权限恢复  │
                            │   S4. add_slave DBMeta      │
                            └─────────────────────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────────┐
                            │ Stage 4                     │
                            │   释放部分单据互斥锁        │
                            │   人工确认缩容(唯一缩容Pause)│
                            └─────────────────────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────────┐
                            │ Stage 5: 缩容(串行,先M后S)   │
                            │   if master: 缩容旧 master   │
                            │   if slave : 缩容旧 slave    │
                            └─────────────────────────────┘
```

**仅恢复 master / 仅恢复 slave 时的退化**：
- Stage 1 退化为单 segment 串行（无并行汇聚开销）
- Stage 2 / Stage 3 缺席的那一段直接跳过
- Stage 5 同理

## 关键时序约束

### 段间依赖关系矩阵

| 段 | 依赖前置段 | 依赖原因 |
|---|---|---|
| Pre-Stage（预览/Pause/DNS） | 无 | - |
| Stage 1 master_install | Pre-Stage | DNS 摘除避免业务旧机器残留 |
| Stage 1 slave_install | Pre-Stage | 同上；与 master_install **可并行**（旧 spider 全毁，无 RUNNING 同角色实例可读） |
| Stage 2 master 路由段 | Stage 1（汇聚） | 表结构同步需 spider 节点已装；init_tdbctl_routing 需 spider 进程已起 |
| Stage 3 slave 路由段 | Stage 2 完成 | ① slave 路由登记需中控可用（M5 之后）② `add_spider_slave_routing_payload` 内部读 DBMeta 取 master spider/ctl 端口（M7 之后） |
| Stage 4 释放锁 + Pause | Stage 3 | 元数据已写入完毕，可释放互斥锁 |
| Stage 5 缩容 master | Stage 4 | 人工确认 |
| Stage 5 缩容 slave | Stage 5 缩容 master | 保守串行；避免 `DropSpiderRoutingComponent` 同时对中控写 mysql.servers |

### 关键参数取值

| 场景 | `primary_ctl_ip` 取值 |
|---|---|
| 同时恢复 master + slave | `master_new[0]["ip"]`（master 段完成后中控已起来，slave 段使用新 master 的中控） |
| 仅恢复 slave | `_resolve_running_ctl_ip(cluster)` —— **复用 Validator 中相同的 L1+L3 探活逻辑**，按 ProxyInstance 顺序找第 1 个 DRS 探活成功的中控 IP（Validator 已保证至少存在一个，但运行时遍历重新探活以应对极端情况下的 DBMeta 漂移） |
| 仅恢复 master | 不需要 slave 段，无 `primary_ctl_ip` 跨段使用 |

### 中控正常性校验时序

```
T0  单据提交
    └─> Validator 跑 L1+L3 双层校验：
        ├─ L1: DBMeta status=RUNNING（≥1 个 spider_master）
        └─ L3: 遍历 RUNNING 中控，DRS select @@version，至少 1 个成功
        失败 → 返回 error_msg 阻断单据提交

T1  单据通过审批，进入 Flow 执行队列
    （此期间不再校验，可能存在中控失活的时间窗）

T2  Flow 执行 Pre-Stage（路由预览/Pause/DNS 摘除）
T3  Flow 执行 Stage 3 slave 路由段
    └─> _resolve_running_ctl_ip(cluster) 取一个 DRS 探活成功的中控
        └─ 全部失败 → 流程在 add_spider_slave_routing_payload 失败
            └─ 用户重试单据时再次走 Validator → L1+L3 → 等中控恢复后通过
```

### 不同 info 之间

- 仍通过 `add_parallel_sub_pipeline` 并行执行（沿用现有逻辑）
- 不同 cluster 之间相互独立，单 cluster 内严格遵循上述五阶段

## 风险与回滚

| 风险 | 缓解 |
|---|---|
| 仅恢复 slave 时主中控不可用 | **Validator L1+L3 双层校验**：DBMeta RUNNING + DRS `select @@version` 探活成功；同时恢复场景跳过（中控由 master 段重建） |
| 仅恢复 slave 时 Validator 通过后中控失活（DBMeta 漂移 / 单据排队期间） | Stage 3 `_resolve_running_ctl_ip` 再探活，全部失败则流程失败；用户重试单据时再次过 Validator |
| DRS 默认账号无法连接中控 admin_port | 走 DRS 内置 drs_account 高权账号（参考 `add_spider_routing.py:80` 现有用法），无需用户传 tdbctl_pass |
| `is_init_slave_cluster=True` 重建路由时与残留旧 slave 记录冲突 | Stage 5 的 `DropSpiderRoutingComponent`（`reduce_spider_nodes_with_cluster` 内部）按旧 IP 列表幂等清理 |
| 旧 slave 全毁，权限克隆源缺失 | `cold_disaster_recover=True` 强制 `is_clone_user=False`，权限走 `spider_layer_priv_recover_sub_flow` 或 `account_rules_only` |
| SLAVE_ENTRY 不存在但用户仍触发 slave 恢复 | Validator 严格检查 SLAVE_ENTRY 存在 |
| 字段硬切导致历史调用失败 | master 流程目前未灰度上线，PR 描述明确说明，文档同步更新 |
| 同 cluster_id 出现在多个 info | 复用现有 `pre_check_duplicate_cluster_ids` 校验阻断 |
| 同时恢复时 `master_new` / `slave_new` IP 重叠 | Validator 新增重叠校验 |
| **Stage 1 并行段一边失败、另一边已完成 → 半残留** | bamboo 默认行为：失败分支报错后汇聚节点失败，已完成分支保留产物。`add_spider_*_sub_flow` 内已是幂等的初始化操作（机器 sys_init / 装包 / 装实例），重试同一单据可继续；若需手动清理可走"强制销毁机器"工单 |
| **Stage 2 master 路由段失败 → Stage 3 不执行 → slave 实例已装但路由未登记** | 单据可重试：Stage 1 已完成 → 跳过；Stage 2 重做（init_tdbctl_routing 幂等）→ Stage 3 继续。slave 实例装好但未挂中控不影响业务 |
| **Stage 3 slave 路由段失败 → DBMeta 不一致** | 单据可重试：Stage 3 重做。期间业务通过主域名访问不受影响（slave 路由登记是从域名生效的前置） |
| **`add_spider_slave_routing_payload` 内部读 DBMeta 取 master spider/ctl 端口，但 Stage 2 M7 才写 DBMeta** | Stage 3 的串行依赖确保 M7 已完成；Validator 中也确认 `cluster.proxyinstance_set` 取端口路径 |

## 单据样板

### 仅恢复 master（与现有等价，仅字段改名）

```json
{
  "uid": "20260506-000003",
  "bk_biz_id": 100,
  "created_by": "admin",
  "tdbctl_pass": "xxxxxx",
  "disable_manual_confirm": false,
  "is_check_process": true,
  "infos": [
    {
      "cluster_id": 12345,
      "spider_master_new_ip_list": [
        {"bk_cloud_id": 0, "bk_host_id": 100001, "ip": "127.0.0.11"},
        {"bk_cloud_id": 0, "bk_host_id": 100002, "ip": "127.0.0.12"}
      ],
      "spider_master_old_ip_list": [
        {"bk_cloud_id": 0, "bk_host_id": 200001, "ip": "127.0.0.21"},
        {"bk_cloud_id": 0, "bk_host_id": 200002, "ip": "127.0.0.22"}
      ],
      "privilege_recovery_mode": "from_spider_grant_backup",
      "strip_dns_before_install": true
    }
  ]
}
```

### 仅恢复 slave

```json
{
  "uid": "20260506-000004",
  "bk_biz_id": 100,
  "created_by": "admin",
  "infos": [
    {
      "cluster_id": 12345,
      "spider_slave_new_ip_list": [
        {"bk_cloud_id": 0, "bk_host_id": 300001, "ip": "127.0.0.31"},
        {"bk_cloud_id": 0, "bk_host_id": 300002, "ip": "127.0.0.32"}
      ],
      "spider_slave_old_ip_list": [
        {"bk_cloud_id": 0, "bk_host_id": 400001, "ip": "127.0.0.41"},
        {"bk_cloud_id": 0, "bk_host_id": 400002, "ip": "127.0.0.42"}
      ],
      "privilege_recovery_mode": "account_rules_only",
      "strip_dns_before_install": true
    }
  ]
}
```

### 同时恢复 master + slave

```json
{
  "uid": "20260506-000005",
  "bk_biz_id": 100,
  "created_by": "admin",
  "tdbctl_pass": "xxxxxx",
  "infos": [
    {
      "cluster_id": 12345,
      "spider_master_new_ip_list": [
        {"bk_cloud_id": 0, "bk_host_id": 100001, "ip": "127.0.0.11"},
        {"bk_cloud_id": 0, "bk_host_id": 100002, "ip": "127.0.0.12"}
      ],
      "spider_master_old_ip_list": [
        {"bk_cloud_id": 0, "bk_host_id": 200001, "ip": "127.0.0.21"},
        {"bk_cloud_id": 0, "bk_host_id": 200002, "ip": "127.0.0.22"}
      ],
      "spider_slave_new_ip_list": [
        {"bk_cloud_id": 0, "bk_host_id": 300001, "ip": "127.0.0.31"},
        {"bk_cloud_id": 0, "bk_host_id": 300002, "ip": "127.0.0.32"}
      ],
      "spider_slave_old_ip_list": [
        {"bk_cloud_id": 0, "bk_host_id": 400001, "ip": "127.0.0.41"},
        {"bk_cloud_id": 0, "bk_host_id": 400002, "ip": "127.0.0.42"}
      ],
      "privilege_recovery_mode": "from_spider_grant_backup",
      "strip_dns_before_install": true
    }
  ]
}
```

## 文件改动清单

| # | 文件 | 改动类型 |
|---|---|---|
| 1 | `backend/ticket/builders/tendbcluster/tendb_spider_layer_disaster_recover.py` | 修改：InfoSerializer 重构（4 个 IP 列表均可选，删旧字段） |
| 2 | `backend/flow/engine/bamboo/scene/spider/validate/spider_layer_disaster_recover_validate.py` | 修改：按 IP 列表非空分支严格校验，含 SLAVE_ENTRY/中控存活/IP 重叠检查 |
| 3 | `backend/flow/engine/bamboo/scene/spider/spider_layer_disaster_recover_flow.py` | 修改：`_cluster_sub_flow` 重构为五阶段编排；新增 `_build_master_install_segment` / `_build_master_routing_segment` / `_build_slave_install_segment` / `_build_slave_routing_segment`；docstring 更新 |
| 4 | `backend/flow/engine/bamboo/scene/spider/common/common_sub_flow.py` | 修改：`add_spider_slaves_sub_flow` 增加 `cold_disaster_recover` 参数 |
| 5 | `backend/flow/utils/spider/spider_disaster_recover.py` | 修改：新增 `build_combined_route_preview` / `_resolve_running_ctl_ip` / `probe_running_ctl_via_drs`（Validator 与 Flow 运行时共用） |

## 验收

参考 `docs/plans/tendbcluster_spider_layer_dr_acceptance.md`，本次扩展新增以下场景验收：

### 仅恢复 slave
- **前置**：单据提交时 Validator 已通过 L1+L3 双层校验，确认中控存活且能响应 `select @@version`
- 从域名（slave_entry）解析指向新 Spider Slave IP，元数据仅保留新 Slave 行
- 主中控 `mysql.servers` 中 SPIDER_SLAVE 路由记录与新 IP 一致，旧记录被清理
- 新 Spider Slave 端口可读取业务表数据
- 缩容旧 Slave 后，旧机器进入回收流程

### 仅恢复 slave 的负向验收
- 模拟所有中控（spider_master）`admin_port` 不可连：单据提交时 Validator 阻断，提示"DRS 探活均失败"
- 模拟 DBMeta 显示 RUNNING 但实际进程已挂：Validator 阻断（L3 兜底 L1 漂移）
- 模拟 Validator 通过后中控立即挂掉：Flow 在 Stage 3 失败，重试单据时 Validator 再次拦截

### 同时恢复 master + slave
- master 段完成（含中控就绪）→ slave 段才开始执行（日志验证时序）
- 缩容时一次 Pause 同时确认旧 master + 旧 slave 下架
- 完成后主域名指向新 Master IP、从域名指向新 Slave IP
- 元数据中 SPIDER_MASTER / SPIDER_SLAVE 均仅保留新节点
- 单据失败时停在最近成功子阶段，可重试同一单据
