# 需求范围：全部 / 一类 / 某一个

DB 之间的差异是设定，不是债。**没有某项能力，默认不要补**；要补必须有产品 / 后端明确说「这些 DB 都要」。

给集群管理面加需求时，先定范围再选落地层。范围没说清就列解释问，不要默默按 mysql 的能力名单或「同形态都要」做。

## 抄代码选哪个 DB

需要打开一个现有 DB 当样本时，**先定形态，只在同形态里选**，再按这个顺序取最靠前的：

mysql → tendb-cluster → es → kafka → redis → sqlserver → mongodb → oracle

| 形态 | 按顺序取 | 说明 |
| --- | --- | --- |
| 关系型 | mysql → tendb-cluster → sqlserver → mongodb → oracle | mysql 骨架最全（申请页、启停删、双入口都有）。oracle 没有申请页、列表没有启停删，排最后 |
| 大数据 | es → kafka | 不要再默认 riak |
| Redis | redis | 集群版与主从版两套都要看；key 分叉见 [registry-map.md](registry-map.md) |
| K8s | 名单里没有。双架构抄 surrealdb，单 HA 抄 qdrant | |
| InfluxDB | 只抄 influxdb | 不用三套公共骨架 |

抄的是骨架、登记方式和同形态标配。样本有、但下表「已记录的能力」里新 DB 不在名单上的（webconsole、分区、Dumper、CLB、Polaris…）**不要一起抄**。

「不要按 mysql 扩」指能力名单，不是「不要打开 mysql 的文件」。

## 三种范围

| 范围 | 再分 | 判定 | 落地 |
| --- | --- | --- | --- |
| **全部** | — | 用该骨架的 DB 都要（influxdb 不用三套骨架则除外） | `common/` 默认实现 + [registry-map.md](registry-map.md) 标「全部」的表 |
| **一类** | **形态类**：关系型 / Redis / 大数据 / K8s | 由形态特征决定（有没有实例页、主机、工具箱、K8s Tab） | 形态分支（如 `clusterType.includes('k8s')`），或只给该类登记 |
| **一类** | **能力白名单**：跨形态，成员不是一整类 | 本篇「已记录的能力」里已有这行，或新开一行把成员写死 | 公共组件可以抽，**只接线名单内的 DB**；不要给名单外补 |
| **某一个** | 单 DB 或单架构 | 只有这一个产品 / 这一种 `ClusterTypes` 有 | 只改 `{db}/`；公共层最多加空 slot，不写默认实现、不进 `CommonColumn` |

## 怎么判定（按这个顺序，命中就停）

1. 需求原文写了「所有集群 / 所有 DB」→ **全部**
2. 能力取决于形态特征（有实例页、有主机、有工具箱、K8s 无主机）→ **形态类**，对照 SKILL.md 四类形态
3. 下表「已记录的能力」已有这行 → 按表里的**现有成员**做，**不要自行扩名单**
4. 只有这一个 DB 的后端有接口，或产品只点了这一个 → **某一个**
5. 跨了形态但不是全部，表里还没有 → **新开白名单**：先把成员写进本篇，再实现
6. 仍不确定 → 停，把「全部 / 形态类 / 白名单（列出候选） / 某一个」摆出来问

禁止当判据用的话：

- 「mysql 有，所以关系型都该有」
- 「同目录都有 partition-manage，新 DB 也抄一份」
- 「公共组件里已经有这个 hook，每个 DB 都该接线」

## 落地对照

| 范围 | 改哪里 | 不要做什么 |
| --- | --- | --- |
| 全部 | `CommonColumn` / `ActionPanel` 默认 Tab / registry「全部」表；各 DB 列表只传 `clusterType` | 只在某一个 `{db}/` 里实现一遍，让别的 DB 缺着 |
| 形态类 | 公共组件里的形态分支，或只改该类的 `{db}/` + 只给该类登记 | 删 `includes('k8s')` 却说不清它在区分什么；强迫大数据有实例列表页 |
| 能力白名单 | `common/` 下已有组件（webconsole、cluster-authorize、useAddClb、useAddPolaris…）可以复用；**只在名单 DB 的列表 / 菜单 / 路由接线** | 给名单外的 DB 补菜单或补登记「以免漏」 |
| 某一个 | `{db}/` 页面、该 DB 的 source / Model；公共层没有对应 slot 就按字段名加空 slot | 写进 `CommonColumn`、写成 `ActionPanel` 默认 Tab、顺手给 oracle 也做一份 |

范围是「某一个」却去改 `common/cluster-table`、`common/instance-table`、`common/cluster-details` 的默认实现，
就是落错层——那三个目录等于所有用了这套骨架的 DB。

## 已记录的能力

「没有」= 设定。新 DB 的骨架跟**同形态里排序最靠前的样本**（上一节），不跟样本的白名单能力走。

### 形态类（和 SKILL.md 四类形态一致）

| 能力 | 有 | 没有 | 说明 |
| --- | --- | --- | --- |
| 集群列表 + 详情双入口 | 除 influxdb | influxdb | influxdb 只用实例列表 |
| 独立实例列表页 | 关系型、Redis | 大数据、K8s、influxdb 的「集群实例」 | 形态内还有缺口，见下一张表 |
| 详情主机 / 参数 / 单据记录 Tab | 非 K8s | K8s | `ActionPanel` 按 `clusterType.includes('k8s')` 分流，业务页不要各自判断 |
| 详情操作记录 Tab | K8s | 非 K8s | 同上 |
| 工具箱 | 关系型 5 个 + redis | 大数据、K8s | 业务设定；实现走 `dbm-toolbox-developer` |
| 申请页 | 除 oracle | oracle | 有则走 `createApplyRoute` |

形态内缺口（仍是设定）：

| 缺口 | 谁没有 | 不要做什么 |
| --- | --- | --- |
| 独立实例列表页 | mysql / sqlserver / oracle 的**单节点**架构 | 不要给 `TENDBSINGLE` 补 `DatabaseTendbsingleInstance` |
| 申请页 | oracle | 不要给 oracle 补申请卡 |
| 启停删 | oracle、influxdb | 不要给它们补 `useOperateClusterBasic` |

### 能力白名单（跨形态，成员写死）

| 能力 | 有 | 落地（本 skill 管入口） |
| --- | --- | --- |
| webconsole | mysql、tendb-cluster、redis、mongodb | `common/webconsole/` + 各 DB `webconsole/Index.vue` + 列表入口 |
| 授权规则 | mysql、tendb-cluster、sqlserver、mongodb | 侧栏 + `{db}/permission`；`AccountTypes` 只有这四个 |
| 权限查询 | mysql、tendb-cluster | `{db}/routes.ts` 的 `permission-retrieve` |
| 白名单 | mysql、tendb-cluster | `{db}/routes.ts` 的 whitelist。不要因为有授权就补白名单 |
| 分区管理 | mysql、tendb-cluster | `{db}/partition-manage` + 侧栏 |
| Excel 导入授权 | mysql（主从 + 单节点）、tendb-cluster | 列表 header 的 `ExcelAuthorize` |
| 启用 CLB | `TENDBHA`、`TENDBCLUSTER`、`ES`、`REDIS_CLUSTER`、`MONGO_SHARED_CLUSTER` | `useAddClb.ticketTypeMap` |
| 绑定 / 解绑 CLB 域名 | `TENDBHA`、`TENDBCLUSTER`、`ES`、`REDIS_CLUSTER` | `useBindOrUnbindClb.ticketTypeMap`（没有 mongo） |
| 启用 Polaris | `ES`、`REDIS_CLUSTER` | `useAddPolaris.ticketTypeMap`。不要和 CLB 合成一张表 |

两张 CLB 表成员不完全相同，Polaris 又是第三张，登记时对号入座。

### 某一个

| 能力 | 谁有 | 落地 |
| --- | --- | --- |
| 数据订阅（Dumper） | 只有 mysql | 侧栏 + `mysql/dumper/`，开关 `mysql.dataSubscription` |

## 新开一条差异

实现白名单或单 DB 能力的**同一批改动**里，在上表加一行：能力名、有谁、落在哪。不写进表，下一个 agent 会当成遗漏去补。

成员变更（新产品要给 sqlserver 也做分区）先改本篇名单，再改代码。不要先改代码再让名单过期。

## 和 registry-map「范围」列的关系

[registry-map.md](registry-map.md) 的「范围」说的是**这张映射表谁要登记**。本篇说的是**这个需求谁要做**。

定完本篇的范围之后：

- 全部 → 核 registry 里标「全部」的表
- 形态类 → 核标「K8s / 非 K8s / 有实例页」的表
- 白名单 / 某一个 → 只核该能力自己的表（`useAddClb`、`useAddPolaris`、`AccountTypes`、菜单），**不要**按「全部」把 `clusterTypeListPageMap` 以外的表硬补一行
