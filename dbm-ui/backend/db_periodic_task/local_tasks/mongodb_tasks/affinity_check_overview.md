# MongoDB 亲和性检查说明

本文档是 MongoDB 亲和性巡检的唯一口径文档，覆盖离线脚本与线上周期任务。

> **判定单元：云可用区（cloud zone）**
> 同一云可用区下的多个园区网络等同，因此亲和性按「云可用区」判断是否分散，不再按园区（sub_zone）判断。
> - 期望值：`Cluster.cloud_zone_list`（`cluster.zone_list` 已废弃，后续删除）
> - 实际值：节点所在主机 `Machine.bk_cloud_zone`
> - 机架（rack）维度不变，仍按 `Machine.bk_rack_id` 判断；`bk_sub_zone_id` 仅用于 region 兜底映射与展示

## 1. 规则来源

- 枚举与中文标签：`backend/configuration/constants.py` 中 `AffinityEnum`
- 规则原始注释：`affinity_rule.md`

## 2. 检查对象

- `MongoReplicaSet`
- `MongoShardedCluster`
  - `mongos`
  - `configsvr`
  - `shardsvr`（按机器组聚合，非按 set_name）

## 3. 离线输入数据

- `cluster_defs.json`：`cluster_region`、`disaster_tolerance_level`、`cloud_zone_list` 等（旧 dump 里的 `zone_list` 仍兼容读取）
- `cluster_nodes.json`：`set_name`、`ip:port`、`instance_role`、`bk_cloud_zone`、`bk_rack_id`、`bk_city_id`、`bk_sub_zone_id`（仅 region 兜底用）
- `subzones.json`：每条含 `bk_sub_zone_id`、`bk_sub_zone`；**亲和性 region 仅使用非空的 `logical_city_name`**（与 `Cluster.region` / `LogicalCity.name` 同口径）。可选带 `bk_idc_city_name` 仅供人工核对，不参与 region 解析。
- `cities.json`：每条含 `bk_city_id`；**必选非空 `logical_city_name`** 用于 region 映射。可选 `bk_idc_city_name` 仅供人工核对。

可用 `dbm-ui/.cycscript/dump_affinity_json.sh` 从正式环境 MySQL 导出上述 JSON（仅需 `mysql` 客户端、`python3` 标准库与环境变量 `MYSQL_*`，**不依赖** Django / 本仓库 Python 代码）。

## 4. 通用校验前置

- 节点必须具备 `bk_cloud_zone`（主机所属云可用区）与 `bk_rack_id`
- 非 `NONE` 场景下：
  - 节点必须可解析到 region（**仅**逻辑城市名：线上为 `Machine.bk_city.logical_city.name`，离线为 `cities`/`subzones` 中的 `logical_city_name`）
  - 组件节点必须单 region
  - 组件 region 必须与 `cluster.region` 一致

**命名说明（昆山 / 上海等）：** `cluster.region` 常为逻辑城市名（如「上海」），机器侧 CMDB 城市名可能为 IDC 粒度（如「昆山」）。在业务归属一致的前提下，**歧义纯粹来自命名粒度不统一，并非部署拓扑错误**。比对统一以逻辑城市（`LogicalCity.name` / 离线 `logical_city_name`）与 `cluster.region` 对齐，避免因名不同而误报 `region_mismatch`。

## 5. 成员数检查

- `mongos` 至少 `2` 个成员
- `replicaset / configsvr / shardsvr组` 至少 `3` 个成员
- 集群标签 `single_node:true`（离线 JSON `has_single_node_tag`）时：跳过成员数检查；**同时**在 `check_affinity_rules` 内跳过下列亲和性等级的**最小可用区数**约束（其它规则如 region、cloud_zone_list、可用区容忍度、rack 等仍执行）：
  - `CROS_SUBZONE`：不校验「至少 2 个可用区」
  - `CROSS_SUBZONE_STRONG`：不校验「至少 3 个可用区」的数量下限（`zone_tolerance` 等仍校验）
  - `CROSS_SUBZONE_WEAK`：不校验「至少 2 个可用区」的数量下限（`zone_tolerance` 等仍校验）
  - `MAJORITY_ELECTION_DISTRI`：不校验「至少 2 个可用区」

## 6. cloud_zone_list 规则

- 所有非 `NONE` 等级：`cloud_zone_list` 可为空，**空表示不指定可用区（随机部署），与旧 `zone_list` 为空语义一致**，此时跳过配置一致性校验
- `SAME_SUBZONE` / `SAME_SUBZONE_CROSS_SWTICH`：
  - `cloud_zone_list` 为空 → 不校验配置（是否真的同一可用区仍由实际拓扑判定）
  - `cloud_zone_list` 非空 → 必须仅 1 个值，否则报 `zone_list_required_single`（配置错误码名不变，口径为可用区）
- 其他非 `NONE`：
  - 若不为空，需与实际云可用区集合一致

## 7. 各亲和性等级口径

### SAME_SUBZONE

- 单一云可用区

### SAME_SUBZONE_CROSS_SWTICH

- 仅非 backup 节点参与核心校验
- 非 backup 必须单一云可用区
- 非 backup 至少跨 `2` 个 `rack`
- backup 可在 `cloud_zone_list` 指定可用区之外

### CROS_SUBZONE

- 至少 `2` 个云可用区

### CROSS_SUBZONE_STRONG

- 至少 `3` 个云可用区
- 可用区容忍度：任一可用区节点数不超过 `ceil(n/3)`
- rack 校验按组件整体计算（合并所有可用区）：
  - 至少 `2` 个 rack
  - 任一 rack 节点数不超过 `ceil(n/2)`

### CROSS_SUBZONE_WEAK

- 至少 `2` 个云可用区
- 可用区容忍度：任一可用区节点数不超过 `ceil(n/2)`
- rack 校验按组件整体计算（合并所有可用区）：
  - 至少 `2` 个 rack
  - 任一 rack 节点数不超过 `ceil(n/2)`

### MAJORITY_ELECTION_DISTRI

- 至少 `2` 个云可用区
- 任一可用区节点数不超过 `ceil(n/2)`
- 同一 rack 不超过 `1` 节点
- 可用区分布近似均衡（`max-min <= 1`）

### CROSS_RACK

- 至少 `2` 个 `rack`

### MAX_EACH_ZONE_EQUAL

- 可用区分布近似均衡（`max-min <= 1`）

### NONE

- 不做亲和性约束

## 8. ShardedCluster 聚合与输出

- `shardsvr` 按机器组聚合：
  - 组 key：`shardsvr_group:<bk_cloud_id:ip|...>`
  - 聚合后按机器维度去重（同机多分片不重复计数）
- 离线输出中，若仅 `mongos` 异常，仅打印 `mongos` 组件详情

## 9. 输出内容

- 集群总览：`total/success/warning/abnormal`
- 异常/预警明细：
  - 集群级：`cluster_id`、`domain`、`affinity`、`cluster_region`
  - 组件级：`cloud_zone_list`、`actual_cloud_zones`、`actual_regions`、`actual_racks`
  - 节点级：`instance(addr)`、`actual_cloud_zone`、`actual_sub_zone`、`actual_rack`、`instance_role`
- `reason` 带 `code=...`，离线包含 `domain`
- 离线支持 `--summary-by-code`

## 10. 错误码

- 详见 `error_code_reference.md`

## 11. 最近变更历史

- **亲和性判定单元由「园区」改为「云可用区」**：
  - 期望值读取 `Cluster.cloud_zone_list`，实际值读取 `Machine.bk_cloud_zone`
  - 同一可用区不同园区的主机不再被视为已分散（修复跨园区误判为已分散的问题）
  - `bk_sub_zone_id` 不再参与分散判断，仅用于 region 兜底映射与展示
  - rack 判断逻辑不变（维度与取值均未调整）
  - 错误码保持不变，仅文案与展示字段改为 `cloud_zone` 口径
- `SAME_SUBZONE_CROSS_SWTICH` 增加 backup 例外：
  - `instance_role=backup/MONGO_BACKUP` 的节点允许在 `cloud_zone_list` 指定可用区之外
  - 该等级核心约束（单可用区、跨 2 rack）仅对非 backup 节点生效
- `MongoShardedCluster` 的 `shardsvr` 从“按 set_name 检查”调整为“按机器组检查”：
  - 组 key 使用 `shardsvr_group:<bk_cloud_id:ip|...>`
  - 同机多分片场景下，组内按机器维度去重，避免重复计数放大告警
- `CROSS_SUBZONE_WEAK/STRONG` 的 rack 校验从“按 zone 分别计算”调整为“全组件汇总计算”：
  - 将所有可用区的节点合并后统一校验 rack 数量与 rack 容忍度
  - 与实际“跨 rack”语义保持一致，减少局部 zone 误判
- 地域（region）与 `cluster.region` 对齐：**仅**使用 `BKCity.logical_city.name`（线上巡检与离线 JSON 的 `logical_city_name`），不再用 IDC 城市名参与比对；逻辑城市名为空时记为数据缺失。
