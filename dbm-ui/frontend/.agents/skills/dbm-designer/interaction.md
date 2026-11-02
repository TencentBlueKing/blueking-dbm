# 交互

新交互必须能对上某一条；对不上就问，不要发明第三套。列表空态 / 分页 / 复制 / 筛选见 [list-page.md](list-page.md)，提单见 [toolbox-page.md](toolbox-page.md)，弹层形态见 [overlay.md](overlay.md)。

## 两道门

先开关、后权限。

| 门 | 手段 | 关闭 / 无权限时 |
| --- | --- | --- |
| 功能开关 | `FunController` / `v-db-console` | **不渲染** |
| IAM | `Auth*`（`permission` 有值就传，避免再打接口） | **仍渲染**，置灰 + `v-cursor`，点击申请权限，不是 `disabled` |

平台锁定传 `disabled`，跳过鉴权。403 由请求层弹申请框（`permission: 'page'` / `'catch'` 换整页或局部）。直达链接与按钮走同一鉴权链路，见 `dbm-frontend-developer` 的 `references/direct-link.md`。

## 离开拦截

用户改过表单 → `window.changeConfirm = true`（`DbForm` / `EditableTable` 已做）。提交 / 关闭 / 卸载时清掉。

```
无变更或 changeConfirm === 'popover' → 直接离开
有变更                               → InfoBox「确认离开当前页」
侧滑打开期间                         → 外层标成 'popover'，避免套弹；关闭时还原为打开前的页面状态
```

拦截点：路由守卫（菜单、面包屑、`router.push`、前进后退；只改 query 的同页跳转不拦）、`beforeunload`、
`DbSideslider` / `DbDialog` 的关闭。表单一律用 `DbForm`；不走 `DbForm` 的自定义控件用 `useMarkChanged()` 标记，
不要直接写 `window.changeConfirm = true`（弹层打开期间会被还原掉）；
要在退出编辑 / 卸载时撤销的来源用 `markSourceChanged` / `releaseSourceChanged` 按 key 登记，不要直接写 `false`
（会清掉页面其它来源）。页面内切换选项跳到同族页面用
`switchSiblingRoute`，取消离开时把选项还原；选项组件在 `DbForm` 内部时不要改选项，直接 `router.push`。
只改 query 的同页切换（会卸载内容）路由守卫不拦，先 `leaveConfirm()` 再切换。

用 `leaveConfirm` / `useBeforeClose` / `DbSideslider` 的 `showLeaveConfirm`，不要手写文案。

## 确认分级

| 场景 | 形态 | 主按钮 |
| --- | --- | --- |
| 依附按钮的一句话（重置、行内删除） | `DbPopconfirm` 280px | 「确认」；危险操作用 danger |
| 阻断式（离开、继续提单、删集群） | `InfoBox` | 离开 / 继续提单 / 删除 |
| 带表单或清单 | 居中对话框 | 「确定」 |

删除资源不要求输入名称；灰底块列出受影响对象。工具箱重置用 `DbResetButton`。
