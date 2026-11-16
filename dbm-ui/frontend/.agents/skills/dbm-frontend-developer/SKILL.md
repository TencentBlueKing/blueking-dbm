---
name: dbm-frontend-developer
description: >-
  DBM 前端编码的基础规范，所有前端编码任务都要使用：只要会新建、修改、重构、修复 src/ 下的 .vue / .ts / .tsx / .less
  文件（写组件、加页面、改样式、调接口、修 bug、按需求或提案实现），动手前先读，与 db / 单据 / 工具箱等场景 skill
  叠加使用而非二选一。管跨模块通用的纵线：项目独有编码约定（auto-import、script setup 宏顺序、Props / Emits、t()、
  路径别名、Less 类名、版权头）、src 分层与文件放哪、服务层（source / model / http / types）与新增接口、
  导航与菜单挂载（routeGroup、DbMenu）、?open= 直达链接、DbQuickSearch 与列筛选联动、弹层提交后关闭与刷新。
  用户询问某个写法对不对、新接口放哪、路由为什么不高亮、筛选值形态时也使用。
---

# DBM 前端架构与代码逻辑

本 skill 管**不属于任何单一业务模块的通用纵线**：代码怎么写、文件放哪、数据怎么取、页面怎么挂上导航、URL 怎么驱动动作、筛选状态怎么同步。判据是「换个业务模块这条约定照样成立」——成立就在这里，只对某个模块成立就在场景 skill 里。

**只定「长什么样、怎么反馈」的归 `dbm-designer`**，其余边界与各 skill 分工见 `AGENTS.md`「技能索引」。

## 在做什么

| 场景                                                        | 读哪篇                                                    |
| ----------------------------------------------------------- | --------------------------------------------------------- |
| 写任何 `.vue` / `.ts`，或拿不准某个写法                     | [code-conventions.md](references/code-conventions.md)     |
| 新建文件不知道放哪、查目录职责、新增接口或改 `services/**`  | [architecture.md](references/architecture.md)             |
| 改 `src/layout/**`、`src/router/**`，或新增页面要挂菜单入口 | [navigation-menu.md](references/navigation-menu.md)       |
| 新增或修改直达链接入口                                      | [direct-link.md](references/direct-link.md)               |
| 页面同时有 `DbQuickSearch` 搜索栏和表格列筛选               | [search-filter-sync.md](references/search-filter-sync.md) |
| 写 `DbSideslider` / `DbDialog` 里的新建、编辑提交           | [popup-submit.md](references/popup-submit.md)             |

## 四条不读 reference 也要记住的

1. **新增带菜单入口的页面，路由 `name` 必须登记进 `layout/Index.vue` 的 `routeGroup`。**
   没登记则顶部导航不高亮、左侧菜单整体不渲染，且不报错。
2. **接口函数放 `services/source/`，列表 / 详情数据用 `services/model/` 的类包装。** 组件里不直接拼请求。
3. **搜索栏与列筛选是同一份筛选条件的两个入口**，首选绑同一个 ref；值形态全链路只允许逗号分隔字符串，变成数组或布尔时前端过滤仍能跑通，只在回显勾选态时才暴露。
4. **直达链接的参数解析 + 可用性判断 + 鉴权 + 动作调用收敛在一个 hook 里**，不在各页面内联，且与手动按钮共用同一个
   `actionId` 和同一个动作函数。
