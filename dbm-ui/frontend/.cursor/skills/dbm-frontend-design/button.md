# 按钮体系

## 主题分布（全站 1342 个 BkButton）

| theme       | 数量 | 占比  |
| ----------- | ---- | ----- |
| 无 theme    | 737  | 55%   |
| `primary`   | 589  | 44%   |
| `danger`    | 11   | 0.8%  |
| `warning`   | 2    | —     |
| `success`   | 0    | —     |

`primary` 只给页面唯一主操作。`danger` 的稀缺性本身就是设计语言，它一出现就代表不可逆操作。`success` / `warning` 主题在按钮上不用，那两个色只属于 `BkTag` 和状态点。

## 位置与形态的对应关系

| 位置                       | 形态                                                    | 尺寸 / 间距              |
| -------------------------- | ------------------------------------------------------- | ------------------------ |
| 列表页操作区（最左）       | `theme="primary"` 实心                                  | 默认尺寸，次按钮 `ml-8`  |
| 表格行内 / 操作列          | `text` + `theme="primary"`                              | 按钮间 `ml-8`            |
| 批量操作                   | `disabled` + `v-bk-tooltips` 说明原因                   | 禁用必须给 tooltip       |
| 侧滑 footer                | primary「提交」+ 默认「取消」                           | `min-width: 88px`，`mr-8` |
| 弹窗 footer                | primary「确定」+ 默认「取消」                           | `mr-8`                   |
| 固定底栏（工具箱 / 详情）  | primary + `DbPopconfirm` 包裹的次操作                   | `class="w-88"`，栏高 52px |
| 详情内联更多操作           | `size="small"` + `DbIcon`                               | `padding: 0 6px`         |

## 文案语义

全部走 `t()`，不得硬编码中文。

| 文案            | 用在哪                       |
| --------------- | ---------------------------- |
| 提交            | 侧滑 / 工具箱主确认          |
| 确定            | Dialog footer 确认           |
| 取消            | 所有次要关闭                 |
| 新建 / 添加     | 列表页主操作                 |
| 删除 / 终止     | 破坏性操作，配 `theme="danger"` |
| 复制            | 行内 `text` 按钮             |
| 批量 xxx        | 选中后的批量区               |
| 克隆 / 再提一单 | 单据复用                     |

「提交」与「确定」不可互换。

## 尺寸规范

| 规则                 | 值                       |
| -------------------- | ------------------------ |
| 默认尺寸             | 不传 `size`（占 92%）    |
| 紧凑场景             | `size="small"`           |
| footer 主按钮最小宽  | 88px，用 `class="w-88"`  |
| 按钮间距             | 8px，用 `mr-8` / `ml-8`  |

## 权限按钮

涉及资源变更的操作用 `AuthButton`，不要用裸 `BkButton`。

```vue
<AuthButton
  action-id="mysql_apply"
  :permission="permission"
  :resource="bizId"
  theme="primary">
  {{ t('申请实例') }}
</AuthButton>
```

- `AuthButton` — 替换 `BkButton`，必传 `action-id`
- `AuthTemplate` — 包裹任意内容 + 透明遮罩

无权限时按钮变为 `#c4c6cc` 文字 / `#fafbfd` 背景 / `#dcdee5` 边框，点击不执行业务逻辑而是唤起 IAM 申请。

## 图标按钮

```vue
<BkButton size="small" style="padding: 0 6px">
  <DbIcon type="more" />
</BkButton>
```

`DbIcon` 的 `type` 对应字体图标 class `db-icon-{type}`，常用：`copy-2`、`link`、`more`、`close`、`add`、`batch-host-select`。

全局样式 `.db-icon-button`（`padding: 5px 8px`）在模板中零使用，属于死样式，沿用上面的写法。

## 参考实现

- `src/components/auth-component/button.vue`
- `src/components/db-icon/index.ts`
- `src/styles/base.less` — `.w-88`
