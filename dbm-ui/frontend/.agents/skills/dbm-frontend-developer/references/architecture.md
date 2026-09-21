# 仓库与 src 分层

## 仓库分层

- `src/` 源码
- `public/` 静态资源，构建后原样输出
- `lib/` 内部库（别名 `@lib/*`）
- `openspec/` 变更提案与规格（未纳入 git）

## src 分层

| 目录          | 职责                                                         |
| ------------- | ------------------------------------------------------------ |
| `views/`      | 页面，每个功能一个文件夹                                     |
| `components/` | 跨业务可复用 UI                                              |
| `services/`   | API、数据模型                                                |
| `stores/`     | Pinia                                                        |
| `hooks/`      | 全局 composable                                              |
| `router/`     | 路由入口，`registerModule` / `registerBusinessModule`        |
| `utils/`      | 通用工具                                                     |
| `common/`     | 常量、正则、缓存（`TicketTypes`、`DBTypes`、`ClusterTypes`） |
| `layout/`     | 导航壳                                                       |
| `locales/`    | i18n                                                         |
| `styles/`     | 全局样式                                                     |
| `types/`      | 全局 TypeScript 类型声明                                     |
| `images/`     | 图片资源                                                     |
| `directives/` | 自定义指令                                                   |
| `helper/`     | 本地缓存、校验器                                             |

`layout/` 的导航壳与菜单体系见 [navigation-menu.md](navigation-menu.md)。

## 组件与页面的放置

- 组件命名：目录 kebab-case，入口固定 `Index.vue`，仅本组件使用的子文件放同级 `components/`
- 页面按业务拆在 `src/views/` 下，各自有 `routes.ts`，由 `src/router/index.ts` 聚合。
  常见模块：`db-manage`、`ticket-center`、`resource-manage`、`monitor-alarm`、`service-apply`、
  `password-manage`、`db-configure`
- 跨业务复用才进 `components/`；只有一个页面用的组件留在该页面目录下，不要提前上移

## 服务层 `src/services/`

| 目录      | 职责                                 |
| --------- | ------------------------------------ |
| `source/` | 接口函数，经 `http` 发请求           |
| `model/`  | 列表 / 详情数据类与单据 details 类型 |
| `http/`   | 请求封装                             |
| `types/`  | 列表分页等通用类型                   |

新增接口：在 `source/` 按资源写函数，列表行用 `model/` 的类包装。组件里不直接拼请求。

单据 details 接口与提单字段对齐，并在 `model/ticket/details/{db}/index.ts` 导出，详见 `dbm-ticket-developer` skill。
