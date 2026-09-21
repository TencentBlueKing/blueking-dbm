# 开发范式

优先复制同族页，只改业务列 / 单据类型 / `dataSource`。不要为一次需求抽公共层。

| 要做 | 复制 |
| --- | --- |
| 集群 / 实例列表、详情 | 同形态已有 DB + `cluster-table` / `instance-table` |
| 工具箱提单 | 同 DB 最像的 `{TICKET_TYPE}/Index.vue` |
| 配置 CRUD | 表格 + 侧滑 |
| 左表右预览选择器 | `host-selector/`（取值见 known-issues `selector-dialog-skeleton`） |
| HTML 原型 | [assets/page-frame.html](assets/page-frame.html) |

基础控件先用 `src/components/bkui-vue/` 的 `DbInput` / `DbSelect` / `DbTag` / `DbPagination`，没有再用 bkui-vue。新代码不要引入 element-plus。全局已注册的不要再包一层。

| 需求 | 用 | 不要 |
| --- | --- | --- |
| 远程分页表 | `DbTable` | 裸 `BkTable` 自接分页 |
| 可编辑表 | `EditableTable` | 用 `DbTable` 假装可编辑 |
| 单据只读表 | `InfoTable` | 再包 `DbTable` |
| 搜索 | `DbQuickSearch`（不传 `placeholder`） | 自绘一排 Input |
| 侧滑 | `DbSideslider` | 裸 `BkSideslider` 再抄 footer |
| 气泡确认 / 重置 | `DbPopconfirm` / `DbResetButton` | 自写 tippy |
| 行内更多（>3） | `MoreActionExtend` | 每页自写菜单 |
| 行内详情 | `TableDetailDialog` | 侧滑或跳路由 |
| 吸底栏 | `SmartAction` 或 `.absolute-footer` | 两种混用 |
| 卡片 / 空态 | `DbCard` / `EmptyStatus` | 自写阴影盒、自写三套插图 |
| 权限 / 开关 | `Auth*` / `FunController` | 裸按钮 `disabled`、散落 `v-if` |
| 状态点 / 实例状态 / 属性 | `DbStatus` / `ClusterInstanceStatus` / `DbTag`（表格用 `MiniTag`） | 三种串台 |
| 表单 | `DbForm`（脏检查、校验滚动） | 裸 `BkForm` 漏 `changeConfirm` |
| 主按钮宽 | `w-88` | 每处手写还漏 |

图标 `<DbIcon type="copy" />`。
