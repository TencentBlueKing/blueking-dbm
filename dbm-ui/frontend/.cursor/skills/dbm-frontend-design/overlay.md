# 弹窗、侧滑与反馈

## 形态选型

由「内容长度 + 是否需要保留上下文」两个变量唯一决定。

```
需要保留页面上下文，且内容较长 / 可滚动？
├─ 是，从列表行展开 ────────────→ TableDetailDialog   60%
├─ 是，表单或详情 ──────────────→ DbSideslider        960px
└─ 否，内容短需居中聚焦
   ├─ 含表格 / 批量清单 ────────→ BkDialog            500 ~ 1140px
   ├─ 依附触发按钮的一句话确认 ─→ DbPopconfirm        280px
   └─ 阻断式决策（离开 / 删集群）→ InfoBox             —
```

## 侧滑宽度档位

| 宽度            | 定位                       | 场景                                       |
| --------------- | -------------------------- | ------------------------------------------ |
| 640px           | 小表单                     | 版本发布编辑、告警订阅                     |
| **960px**       | **默认档，新功能从这里起步** | 告警组、任务节点详情、资源规格、权限规则   |
| 1100px          | 宽内容                     | SQL 文本、实例列表、机器缩容选主机         |
| 1110 / 1200px   | 超宽特例                   | 全局监控策略、Redis 内存分析               |

## DbSideslider

```vue
<DbSideslider
  v-model:is-show="isShow"
  :confirm-text="t('提交')"
  :title="t('编辑告警组')"
  :width="960">
  <Content ref="contentRef" />
</DbSideslider>
```

- footer 默认「提交」（primary）+「取消」，均 `min-width: 88px`，primary 在左
- 纯查看传 `:show-footer="false"`
- 提交逻辑由子组件 `defineExpose({ submit, cancel })` 提供
- 打开时自动置 `window.changeConfirm = 'popover'`，关闭走 `leaveConfirm()`
- 不需要取消二次确认时传 `:show-leave-confirm="false"`

## BkDialog 宽度档位

| 宽度            | 场景                             |
| --------------- | -------------------------------- |
| 480 / 500px     | 批量操作确认、小表单（主流）     |
| 600 / 640px     | 集群操作、白名单编辑             |
| 1000 / 1100px   | Excel 导入、实例只读预览         |
| 1140 / 1180px   | 导出文件列表、申请单预览         |

## 按钮文案规范

| 容器             | 主按钮                                  | 次按钮 |
| ---------------- | --------------------------------------- | ------ |
| `DbSideslider`   | 提交（primary）                         | 取消   |
| `BkDialog` 表单  | 确定 / 确认提交                         | 取消   |
| `BkDialog` 只读  | 关闭（单按钮）                          | —      |
| `DbPopconfirm`   | 确认（固定文案）                        | 取消   |
| `InfoBox`        | 语义化：删除 / 离开 / 禁用 / 继续提单   | 取消   |

「提交」与「确定」不可互换：侧滑用提交，弹窗用确定。

## DbPopconfirm

默认宽 280px（单据审批类扩到 400px），`theme` 默认 primary，危险操作传 `danger`。

```vue
<DbPopconfirm
  :confirm-handler="handleReset"
  :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
  :title="t('确认重置页面')">
  <BkButton class="w-88">{{ t('重置') }}</BkButton>
</DbPopconfirm>
```

## 离开拦截：window.changeConfirm 三态

```
false / undefined  → 直接离开
true               → leaveConfirm() 弹 InfoBox「确认离开当前页」
'popover'          → 侧滑已打开，跳过 InfoBox（避免弹窗套弹窗）
```

表单 `onChange` 时置 `true`，提交成功 / 关闭后置 `false`。`DbSideslider` 打开时自动置 `'popover'`。

项目里**没有** `isCloseConfirm` 属性，离开拦截统一走 `window.changeConfirm` + `leaveConfirm()`。

## 危险操作确认

**不要求用户输入集群名**，项目里没有这类强确认组件。删除集群的标准写法：

```ts
InfoBox({
  cancelText: t('取消'),
  confirmText: t('删除'),
  contentAlign: 'left',
  footerAlign: 'center',
  headerAlign: 'center',
  infoType: 'warning',
  onConfirm: () => { /* ... */ },
  subTitle, // JSX：灰底块列出集群名 + 影响说明
  theme: 'danger',
  title: t('确定删除集群？'),
});
```

行内删除用 `BkPopConfirm`：

```vue
<BkPopConfirm
  :confirm-config="{ theme: 'danger', loading: isDeleting }"
  :confirm-text="t('删除')"
  :title="t('确认删除该版本？')"
  width="280" />
```

## 消息反馈

| 场景         | 写法                                | 时长     | 附加                                    |
| ------------ | ----------------------------------- | -------- | --------------------------------------- |
| CRUD 成功    | `messageSuccess(t('删除成功'))`     | 3000ms   | —                                       |
| 轻量提醒     | `messageWarn(...)`                  | 3000ms   | —                                       |
| 接口错误     | `messageError(...)`                 | 3000ms   | 多数由 HTTP 中间件统一兜底，业务层不重复处理 |
| 提单成功     | `useCreateTicket` 内置 `Message`    | 6000ms   | `dismissable: false` +「查看详情」外链  |

工具类在 `src/utils/message.ts`。

## 参考实现

- `src/components/db-sideslider/index.vue`
- `src/components/db-popconfirm/index.vue`
- `src/components/table-detail-dialog/Index.vue`
- `src/utils/leaveConfirm.ts`、`src/utils/message.ts`
- `src/views/db-manage/common/hooks/useOperateClusterBasic.tsx` — 集群危险操作
