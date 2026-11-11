# MongoDB Affinity Error Codes

离线巡检脚本 `check_affinity_standalone.py` 的 `reason` 字段统一以 `code=...` 前缀输出。

> 判定单元为**云可用区**（`Cluster.cloud_zone_list` vs `Machine.bk_cloud_zone`）。错误码名称保持不变以兼容历史报表，
> 但 `zone` / `sub_zone` 字样在当前口径下指「云可用区」；`rack` 相关错误码仍指机架。

## Abnormal Codes

- `region_mismatch`：`cluster.region` 与节点侧 region 集合不一致（节点 region 为 **逻辑城市名**，与 `LogicalCity.name` / 离线 `logical_city_name` 一致）。历史上若出现「昆山 vs 上海」等，多为 IDC 城市名与逻辑城市名**命名不统一**所致，对齐逻辑城市后应按上述口径理解，而非简单视为跨城部署错误。
- `multi_region_violation`：非 `NONE` 场景下节点不在同一个 region
- `zone_list_required_single`：`SAME_SUBZONE*` 场景 `cloud_zone_list` 配置了多个值（>1）；**为空表示随机，不报此错**
- `zone_list_mismatch`：配置了 `cloud_zone_list` 但与实际云可用区集合不一致
- `same_subzone_violation`：`SAME_SUBZONE` 非单可用区
- `same_subzone_cross_zone_violation`：`SAME_SUBZONE_CROSS_SWTICH` 下非 backup 节点非单可用区
- `same_subzone_cross_rack_violation`：`SAME_SUBZONE_CROSS_SWTICH` 未满足跨机架
- `cross_subzone_min_violation`：`CROS_SUBZONE` 少于 2 个可用区
- `strong_zone_constraint_violation`：`CROSS_SUBZONE_STRONG` 可用区数量/容忍度不满足
- `strong_rack_constraint_violation`：`CROSS_SUBZONE_STRONG` rack 条件不满足
- `weak_zone_constraint_violation`：`CROSS_SUBZONE_WEAK` 可用区数量/容忍度不满足
- `weak_rack_constraint_violation`：`CROSS_SUBZONE_WEAK` rack 条件不满足
- `majority_min_zone_violation`：`MAJORITY_ELECTION_DISTRI` 少于 2 个可用区
- `majority_zone_violation`：`MAJORITY_ELECTION_DISTRI` 单可用区节点数超过上限
- `majority_rack_unique_violation`：`MAJORITY_ELECTION_DISTRI` 同机架超过 1 个节点
- `majority_balance_violation`：`MAJORITY_ELECTION_DISTRI` 可用区分布不均衡
- `cross_rack_violation`：`CROSS_RACK` 未跨机架
- `zone_equal_violation`：`MAX_EACH_ZONE_EQUAL` 可用区分布不均衡
- `node_subzone_missing`：节点缺 `bk_cloud_zone`（旧 dump 缺该列时退化为 `bk_sub_zone_id`）
- `node_rack_missing`：节点缺 `bk_rack_id`
- `node_region_mapping_missing`：节点在 `subzones.json` / `cities.json` 中缺少可用的 `logical_city_name`（不再使用 IDC 城市名作为 region）
- `component_missing`：组件节点为空

## Warning Codes

- `cluster_region_empty`：`cluster.region` 为空
- `affinity_empty`：`disaster_tolerance_level` 为空
- `affinity_unsupported`：未知 `disaster_tolerance_level`
