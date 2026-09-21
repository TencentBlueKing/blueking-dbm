# 接入一个新 DB

先按 [feature-scope.md](feature-scope.md)「抄代码选哪个 DB」在同形态里选样本。下面的目录树以 surrealdb 为例，
只因为 `{架构}-cluster-list` 命名干净，**不是**因为 K8s 是默认模板。

跨全仓库大约几十到上百个文件。抄骨架和登记，不要把样本的 webconsole / 分区 / CLB / Polaris / Dumper 一起抄走。

## 0. 先问清楚，别猜

开工前这些必须从后端 / 需求确认，全是字符串对齐问题，猜错了后面每一步都要返工：

- **形态**：关系型 / 大数据 / K8s（决定复用哪套页面、要登记哪些表，见 SKILL.md 的四类形态）
- **`db_type` 的值**，以及 **每种集群架构的 `cluster_type` 值**（几种架构 = 几个 `ClusterTypes`）
- **功能开关**：挂在哪个模块下（独立模块，还是 `bigdata` / `k8s` 的子 key），key 叫什么
- **接口**：URL 前缀（按后端模块拼，不是按 `db_type` 拼）、列表 / 详情 / 实例 / 拓扑各自的 path
- **单据**：申请 / 启用 / 禁用 / 删除 / 重启各自的 `ticket_type`，以及启停删是按 DB 一套还是按架构各一套
- **能力范围**：先读 [feature-scope.md](feature-scope.md)，骨架跟样本、白名单能力不跟样本
- **iam action id** 命名（`{db}_apply` / `{db}_manage` / `{db}_enable_disable` / `{db}_destroy` / `{db}_edit`）

## 1. 登记常量与功能开关

按 [registry-map.md](registry-map.md) 的 A 节逐条加。顺序：`dbTypes.ts` → `clusterTypes.ts` →
`dbTypesInfos/` → `clusterTypesInfos/` → `queryClusterTypes.ts` → `clusterCountMap.ts`
（独立模块登 `ClusterCountMap`，K8s 登 `ClusterK8sCountMap`，大数据不用这张表，见
[registry-map.md](registry-map.md)）→
`ticketTypes.ts` → `userPersonalSettings.ts`（非 K8s 还要 `machineTypes.ts`）。

`dbTypesInfos` 与 `clusterTypesInfos` 都是「分组文件 + `index.ts` 里 spread」两处改，新 DB 属于已有分组
就加进去，是新分组才新建文件。

功能开关在 `services/model/function-controller/functionController.ts`：加模块 key 或 children key
（同时改对应的 `XxxFunctions` 联合类型），以及页面 / 按钮级的 dbConsole 点路径属性（`{db}.{页面}.{动作}`）。
前端只是声明类型，**实际开关值来自后端 `/apis/conf/function_controller/`**，后端没配则路由 gate 恒为 false、
页面整体不出现，本地调试看 `defaultController.json`。

**验证**：`yarn type-check`。`queryClusterTypes.ts` 和 `MenuGroup.vue` 的 `foldNameMap` 是
`Record<DBTypes, ...>`，漏了会在这一步就报错——报错是好事，说明还有编译期保障。

## 2. 数据层

- `services/source/{db}*.ts`：一个架构一个文件（`surrealdbHa.ts` / `surrealdbSingle.ts`）或一个 DB 一个文件
  （`kafka.ts`），照抄同形态样本：`getRootPath()` + 列表 / 实例 / 详情 / 拓扑 / 主机 / 导出
- 列表返回 `ListBase<XxxModel[]>`，`.then()` 里 `new XxxModel(...)` 包装，并把接口级 `permission`
  合并进每行：`Object.assign(item, { permission: Object.assign({}, item.permission, data.permission) })`
- `services/model/{db}/`：列表行 Model `extends ClusterBase`，只写该 DB 特有的操作态 getter；
  详情 / 实例 / 机器 Model 各一个文件
- `services/model/ticket/details/{db}/` + 同目录 `index.ts` 导出 + `model/ticket/ticket.ts` 的
  `export type * as`

服务层分层见 `dbm-frontend-developer` 的 `references/architecture.md`。**验证**：`yarn type-check`。

## 3. 页面

目录命名用 `{架构}-cluster-list`（与 surrealdb / mysql 的 ha、single 一致），不要抄 redis 的
`cluster-list` / `cluster-ha-list` 或大数据旧目录 `list/` / `detail/`：

```
views/db-manage/{db}/
├── Index.vue                              模块壳（<RouterView />）
├── routes.ts
├── {架构}-cluster-list/Index.vue
├── {架构}-cluster-detail/Index.vue        路由壳
├── common/{架构}-cluster-detail/Index.vue 详情实现
└── {TICKET_TYPE}_APPLY/Index.vue          申请页
```

骨架与 slot 见 [page-skeletons.md](page-skeletons.md)。这一步同时要补 [registry-map.md](registry-map.md)
C 节的类型映射与行为映射——**页面能跑起来不代表登记完了**，C 节里大半是点了才发现的。

**验证**：`yarn type-check` + `npx eslint <改动文件> --fix`。

## 4. 挂载

1. `{db}/routes.ts`：静态 `routes` 数组（一个父路由 + children）+ `export default getRoutes(funControllerData)`，
   开关关闭返回 `[]`。父级用 glob 自动收集，**不用改 `src/router/`**，但所有页面必须挂在同一个父路由下
2. `layout/.../module-group/{Db}.vue` 手写菜单项 + 同目录 `Index.vue` 的 `comMap` +
   `components/MenuGroup.vue` 的 `foldNameMap`
3. `layout/Index.vue` 的 `routeGroup[menuEnum.databaseManage]` 加路由 name
4. 有申请页：`service-apply/routes.ts` 的 `createApplyRoute` + `service-apply/index/Index.vue` 的卡片 +
   `components/auth-component/use-base.ts` 的 `withBizActionList`
5. **`DBTypes` 值 ≠ 目录名**：`utils/createApplyRoute.ts` 的 `routeNameMap`

## 5. 收尾

- 文案全部走 `t()`，`locales/zh-cn.json` 与 `en.json` 同步加 key
- 图标：`DBTypeInfos.icon` 填 `lib/bk-icon/style.css` 里已有的 `db-icon-{name}`，没有对应图标就用通用的
  `cluster` / `node`，需要专属图标得先让设计出字体图标
- 决定要不要在 db-configure、resource-manage/spec、version-files 里排除该 DB（见 registry-map E 节）
- 跑一遍 [registry-map.md](registry-map.md) 末尾的 `rg -il` 差集自查

## 验收

前端改完只能证明「不报错」，功能要在联调环境上点一遍，清单见
[review-checklist.md](review-checklist.md) 的「人工验证清单」，新接入的 DB 全部跑一遍。
