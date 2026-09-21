# 按 DB 类型分发的映射表清单

公共组件靠 `Record<DBTypes, ...>` / `Record<ClusterTypes, ...>` 分发，**多数是 `Partial<Record<...>>`、
`Record<string, ...>` 或用 `as` 断言收口的，少一个 key 时 TS 不报错**。这份清单就是这些表的全集，
接入新 DB 逐条登记，review 时逐条核对。

「范围」列：`全部` = 任何新 DB 都要；`K8s` / `非 K8s` = 只有该形态需要；其余是能力条件。
先定需求谁做、再来对这张表该登记谁，见 [feature-scope.md](feature-scope.md)。

## A. 常量层 `src/common/const/`

| 文件 | 登记什么 | 漏了会怎样 | 范围 |
| --- | --- | --- | --- |
| `dbTypes.ts` | `DBTypes` 枚举值，与后端 `db_type` 完全一致 | 后续所有表都无从下手 | 全部 |
| `clusterTypes.ts` | `ClusterTypes`，**每种集群架构一个** | 集群类型识别不了 | 全部 |
| `dbTypesInfos/{组}.ts` + `index.ts` 的 spread | `DBTypeInfos` 条目：`icon`、`id`、`machineList`、`moduleId`、`name`、`routeIndexName` | 侧栏不出现该 DB；DB 下拉 / Tab / 快速搜索 / 告警筛选全部缺项 | 全部 |
| `dbTypesInfos/index.ts` 的 `readExcludeDbTypeMap` / `editExcludeDbTypeMap` | 该 DB 是否出现在资源池读 / 写下拉 | 不想要它出现时会多出来 | 按需 |
| `clusterTypesInfos/{组}.ts` + `index.ts` | `clusterTypeInfos` 条目：`dbType`（**ClusterType→DBType 的唯一反查**）、`listRouteName`、`name`、`specClusterName`、`machineList` | 详情页 `clusterTypeInfos[cluster_type].dbType` 取到 `undefined`，拓扑组件拿不到 dbType | 全部 |
| `queryClusterTypes.ts` | `clusterTypesByDBTypeRaw[DBTypes.X]` | 类型是 `Record<DBTypes, ...>`，**漏了 TS 会报错**，属于少数有编译期保障的 | 全部 |
| `clusterCountMap.ts` 的 `ClusterCountMap` | 独立模块的 clusterType 列表 | `useBizDbDisplay` 里非 bigdata / 非 k8s 分支统计集群数恒为 0，侧栏不显示 | 独立模块：mysql / tendbcluster / redis / mongodb / sqlserver / oracle。**大数据不要登这张表** |
| `clusterCountMap.ts` 的 `ClusterK8sCountMap` | K8s 的 clusterType 列表 | 同上，K8s 侧栏不显示 | K8s |
| `useBizDbDisplay` 大数据分支 | 不用 map，用 `DBTypes` 值当 `cluster_type` 取 count（与该 DB 的 `ClusterTypes` 同值） | 侧栏不显示 | 大数据（含 influxdb） |
| `machineTypes.ts` | `MachineTypes` 机器角色 | 规格、资源池、部署方案里角色缺失 | 非 K8s |
| `ticketTypes.ts` | 申请 / 启用 / 禁用 / 删除 / 重启等 `TicketTypes`。**每登记一条就要配套一套单据四件套，见 `dbm-ticket-developer`** | 提单 `ticket_type` 对不上，单据详情落 `Default.vue` | 全部 |
| `userPersonalSettings.ts` | `XXX_TABLE_SETTINGS`（每个集群列表一个）、`XXX_INSTANCE_SETTINGS` | 用户的列显隐 / 排序存不住 | 全部 |
| `userPersonalSettings.ts` 的 `toolboxProfileKeyMap` | 工具箱 favor / used / menus 三个 key | 工具箱收藏与最近使用失效 | 有工具箱 |
| `accountTypes.ts` | `AccountTypes` | 授权模块选不到该 DB | 有授权 |

## B. 服务层 `src/services/`

| 文件 | 登记什么 | 漏了会怎样 | 范围 |
| --- | --- | --- | --- |
| `model/function-controller/functionController.ts` | 模块 key 或 children key（`K8sFunctions` / `BigdataFunctions` 等联合类型）+ dbConsole 点路径属性 | `getFlatData` 拿不到开关，路由 gate 恒 false | 全部 |
| `source/{db}*.ts` | 列表 / 详情 / 实例 / 拓扑 / 主机 / 导出接口 | 页面无数据源 | 全部 |
| `model/{db}/` | 列表行、详情、实例、机器 Model，集群 Model `extends ClusterBase` | 表格字段与操作态 getter 全空 | 全部 |
| `model/ticket/details/{db}/` + 同目录 `index.ts` | 启停 / 删除 / 重启 / 申请的 details 类型（细节见 `dbm-ticket-developer` 的 `registry.md`） | 单据详情类型缺失 | 全部 |
| `model/ticket/ticket.ts` | `export type * as Xxx from './details/xxx'` | 详情组件引用不到 `Xxx.Yyy` | 全部 |
| `source/kubernetesToolbox.ts` | `addonType` 联合类型扩展 | 申请页拉版本 / 规格方案报错 | K8s |

## C. 页面公共层

### 类型映射（有编译期保障，改了必须同步）

| 文件 | 登记什么 | 范围 |
| --- | --- | --- |
| `db-manage/common/cluster-table/types.ts` | `ISupportClusterType` 联合类型 + `ClusterTypeRelateClusterModel` | 有集群列表（influxdb 除外） |
| `db-manage/common/cluster-details/ActionPanel.vue` | **另一份同名 `ClusterTypeRelateClusterModel`**，与上面那份不共享。Redis 两边 key 不一致（见下方「Redis 的 key」），照抄该文件现有邻居，不要两张表填同一个 `REDIS` | 有集群详情 |
| `db-manage/common/cluster-details/base-info/types.ts` | 详情 Model 映射 | 有集群详情 |
| `db-manage/common/instance-table/types.ts` | 实例 Model 映射 | 有独立实例页 |

### 行为映射（无编译期保障，是静默 bug 高发区）

| 文件 | 登记什么 | 漏了会怎样 | 范围 |
| --- | --- | --- | --- |
| `db-manage/const/clusterTypeListPageMap.ts` | clusterType → 集群详情路由 name | 下架待办、我的告警订阅里点集群名，`router.resolve` 拿到 `name: undefined`，跳转失败 | 有集群详情 |
| `db-manage/hooks/useClusterInstaceList.ts` | `dataSourceMap`：详情页实例列表 API | 详情「实例列表」Tab 空白 | 有集群详情（含大数据 / K8s 的详情 Tab） |
| `db-manage/hooks/useClusterMachineList.ts` | 详情页主机列表 API | 详情「主机列表」Tab 空白 | 非 K8s 且有集群详情 |
| `db-manage/common/hooks/useOperateClusterBasic.tsx` | `ticketTypeMap`：启用 / 禁用 / 删除的 `TicketTypes` | 点禁用弹窗能开，确认后提单 `ticket_type` 为 `undefined` | 有启停删。**oracle / influxdb 没有，不要补** |
| `db-manage/common/hooks/useK8sClusterRestart.tsx` | `ticketTypeMap`：重启 | 同上 | K8s |
| `db-manage/common/hooks/useAddClb.tsx` | `ticketTypeMap`：启用 CLB | 点启用 CLB 提单 `ticket_type` 为 `undefined` | 能力白名单，成员见 [feature-scope.md](feature-scope.md) |
| `db-manage/common/hooks/useBindOrUnbindClb.tsx` | `ticketTypeMap`：绑定 / 解绑 CLB 域名 | 同上；成员与 `useAddClb` 不完全相同，不要合并 | 能力白名单，成员见 [feature-scope.md](feature-scope.md) |
| `db-manage/common/hooks/useAddPolaris.tsx` | `ticketTypeMap`：启用 Polaris | 同上 | 能力白名单，成员见 [feature-scope.md](feature-scope.md) |
| `db-manage/common/dropdown-export-excel/index.vue` | `apiMap` + `type` prop。**key 不一律是 `ClusterTypes`**：k8s 用枚举值，其余用字面量，TenDBCluster 是 `spider` 不是 `tendbcluster` | 导出 Excel 点了没反应 | 全部 |
| `db-manage/common/cluster-tag/Index.vue`、`cluster-table/components/cluster-tag-cell/Index.vue` | DBTypes → 编辑标签 iam action-id | 鉴权 action 为空，按钮权限判定异常 | 全部 |
| `db-manage/common/UpdateClusterAliasName.vue` | DBTypes → 编辑别名 action-id | 同上 | 全部 |
| `db-manage/common/cluster-table/components/MasterDomainCell.vue` | clusterType → 查看详情 action-id | 域名链接鉴权异常 | 全部 |
| `cluster-details/components/cluster-topo/components/ViewTopo.vue` | clusterType → 拓扑图 API | 拓扑 Tab 无数据 | 全部 |
| `cluster-details/components/cluster-topo/components/common/useRenderGraph.tsx` | clusterType → 实例详情 API | 点拓扑节点无详情 | 全部 |
| `cluster-details/components/cluster-topo/components/common/graphData.ts` | 定制布局函数（有专属拓扑形态时） | 布局退化为默认，不阻断功能 | 按需 |
| `db-manage/utils/updateK8sClusterMeta.ts` | `CLUSTER_META_UPDATER_MAP`：clusterType → `update_cluster_meta` | 改别名 / 标签找不到 API | K8s |
| `db-manage/utils/getDomainPreview.ts` | 域名前缀 map + 策略 | 申请页域名预览前缀是 `undefined.` | 有申请页 |
| `cluster-details/base-info/K8SSpec.vue` | 组件规格 API map | 基本信息里规格拉不到 | K8s |
| `cluster-details/components/k8s-operation-record/Index.vue` | 操作记录 API map | 操作记录 Tab 空 | K8s |
| `cluster-details/components/k8s-instance-list/**` | 实例 Model、地址列 Model、实例配置 retrieve API 三处 map | K8s 实例列表报错或空白 | K8s |
| `components/cluster-selector/**`（`tableConfig.ts` 等） | 集群选择器的该 DB 配置 | 其他页面选不到该 DB 的集群 | 有工具箱 / 授权 |

## D. 挂载层

| 文件 | 登记什么 | 漏了会怎样 | 范围 |
| --- | --- | --- | --- |
| `views/db-manage/{db}/routes.ts` | `getRoutes(funControllerData)`，开关关闭返回 `[]` | 路由不存在 | 全部 |
| `layout/.../module-group/{Db}.vue` | 侧栏菜单项（手写 `DbMenuItem` + `FunController` + `v-db-console`） | 菜单里没有入口 | 全部 |
| `layout/.../module-group/Index.vue` 的 `comMap` | `DBTypes` → 上面那个菜单组件 | 侧栏该 DB 分组渲染空白 | 全部 |
| `layout/.../module-group/components/MenuGroup.vue` 的 `foldNameMap` | 折叠态缩写；类型是 `Record<DBTypes, string>`，**漏了 TS 报错** | 编译失败 | 全部 |
| `layout/Index.vue` 的 `routeGroup[menuEnum.databaseManage]` | 该 DB 的父路由 name | 进入该 DB 页面时顶部导航可能不高亮「数据库管理」。`DbManage` 已在组里，漏了不一定掉高亮，父路由仍要登 | 全部 |
| `views/service-apply/routes.ts` | `createApplyRoute(DBTypes.X, TicketTypes.X_APPLY, t('...'))` | 申请页路由 404 | 有申请页 |
| `views/service-apply/index/Index.vue` 的 `services` | 申请入口卡片，`id` 用 `TicketTypes`，`controllerId` 用开关 key | 部署申请页没有该 DB 的卡片 | 有申请页 |
| `utils/createApplyRoute.ts` 的 `routeNameMap` | `DBTypes` 值 ≠ views 目录名时的映射 | 申请页动态 import 路径错，**运行时**才报 | 目录名例外 |
| `components/auth-component/use-base.ts` 的 `withBizActionList` | 业务级（无资源实例）的 action，如 `{db}_apply` | 鉴权请求不带 `bk_biz_id`，权限校验结果不对 | 有申请页 |
| `locales/zh-cn.json`、`en.json` | 路由 `navName`、菜单、申请页文案 | 界面显示 key 原文 | 全部 |

## E. 其他模块的「排除名单」

这些页面默认按 `DBTypeInfos` / `ClusterTypes` 全量渲染，**不想让新 DB 出现就要主动排除**：

| 文件 | 机制 |
| --- | --- |
| `views/db-configure/business/list/Index.vue` | `ClusterTab` 的 `:excludes` |
| `views/resource-manage/spec/Index.vue` | `:exclude="[DBTypes.X]"` |
| `views/version-files/v1/Index.vue`、`v2/Index.vue` | `excludeDbTypes` / `:exclude` |

## 登记粒度：DB 级还是架构级

`useOperateClusterBasic` 这类以 `ClusterTypes` 为 key 的表，现存调用方粒度并不统一：
mysql 传 `TENDBHA` / `TENDBSINGLE`（架构级），sqlserver 传 `SQLSERVER`、mongodb 传 `MONGODB`（DB 级），
K8s 重启 `useK8sClusterRestart` 里 SurrealDB 传 `K8S_SURREALDB` 不是 HA/SINGLE。

**判据是后端单据的粒度，不是代码风格**：该 DB 的多种架构共用同一套启停 / 删除 `ticket_type` 就按 DB 级注册
一条，各架构有独立 `ticket_type` 就按架构分别注册。登记时照抄该 DB 页面实际传进去的那个枚举，
两边必须是同一个值，否则 `ticketTypeMap[clusterType]` 取到 `undefined`。

### Redis 的 key（不要假设三个名字是同一个）

Redis 至少三套 key 并存，往表里填之前先打开目标文件看邻居：

| 出现位置 | 用的 key |
| --- | --- |
| `cluster-table/types.ts` | `REDIS`、`REDIS_INSTANCE` |
| `instance-table/types.ts`、`useAddClb`、`useAddPolaris` | `REDIS_CLUSTER` |
| `useOperateClusterBasic` | 集群版 `REDIS`，主从 `REDIS_INSTANCE` |
| `clusterTypeListPageMap` | 具体 `PREDIXY_*` / `TWEMPROXY_*` / `REDIS_INSTANCE`，不是登一个 `REDIS` 就够 |

`ActionPanel` 里的 `ClusterTypeRelateClusterModel` 跟 `cluster-table/types.ts` **不是同一套 Redis key**。
两处都要加，但分别照抄该文件已有的 redis 邻居。

## 快速自查

新增或改动一个 DB 后，用它的 `DBTypes` 值扫一遍，对照组取 [feature-scope.md](feature-scope.md)
同形态里排序最靠前的（关系型 `mysql`，大数据 `es`，Redis `redis`，K8s `surrealdb`），条数应当接近：

```bash
rg -il '<新 DB 的 DBTypes 值>' src --glob '!**/locales/**' | sort
rg -il 'mysql' src --glob '!**/locales/**' | sort   # 关系型对照组；大数据换成 es，K8s 换成 surrealdb
```

差集里的每个文件都要能说清「为什么这个 DB 不需要」（白名单能力、形态没有的骨架、oracle 没有的启停删），
说不清就是漏登记。mysql 对照组会多出分区 / Dumper / webconsole 等文件，那些按 feature-scope 解释，不要补。
