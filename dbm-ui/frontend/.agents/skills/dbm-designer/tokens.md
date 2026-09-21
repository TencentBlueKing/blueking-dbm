# 令牌补表

[SKILL.md](SKILL.md) 已有布局间距、字号、语义色。这里只放派生值。Less 用 `@primary-color`，不要在业务样式另写 hex。

## 微间距与高度

| 值 | 用途 |
| --- | --- |
| 4 | 复制图标与文字、Tag 间距 |
| 6 | 紧凑图标组、详情内联图标按钮 padding |
| 32 | 输入 / 选择器 / KV 行 / 气泡菜单项 |
| 40 | 可编辑单元格、选择器 Tab、侧栏菜单项 |
| 42 | Tab header |
| 52 / 56 / 60 | 顶栏·底栏 / 侧栏折叠触发器 / 分页·侧栏折叠宽·菜单图标列 |

## 派生色（不要再扩）

| 色 | 用途 |
| --- | --- |
| #e1ecff | hover 浅蓝（预览行、下拉选中） |
| #ebf2ff / #f3fcf5 | 行选中 / 新增行 |
| #fff1f1 | 可编辑错误格底 |
| #e4faf0 / #edf4ff / #fff1db / #feebea | Tag success / info / warning / danger 底 |
| #fafbfd | 无权限按钮底、选择器 Tab 未选 |
| #dcffe2 / #ffe8c3 / #fdd | `DbStatus` 圆点外圈 |

导航深色（`#0e1525` 顶栏、`#182132` 侧栏、菜单选中渐变 `#3f87ff → #3a84ff`）只用于导航，内容区禁止引用。完整导航色在 [assets/page-frame.html](assets/page-frame.html)。

## 圆角 / 阴影 / 动效 / z-index

- 圆角 2px；胶囊 8px 仅侧栏数量角标；圆点用 50%
- 阴影：卡片 `0 2px 4px 0 rgb(25 25 41 / 5%)`；面包屑 `0 3px 4px 0 #0000000a`；气泡 `0 2px 6px 0 rgb(0 0 0 / 10%)`；吸底 `0 -2px 4px 0 rgb(0 0 0 / 6%)`。表格和输入不要加阴影
- 动效：显隐 `0.3s ease`，侧栏宽 `0.3s cubic-bezier(0.4, 0, 0.2, 1)`，箭头 `0.15s`。进行中用 `.rotate-loading`（1.5s，#3a84ff）。不要弹跳
- z-index：2 吸底、9 Loading、999 行内详情、1002 `.absolute-footer`、999999 气泡。不要新档

## 滚动条

全局 4px thumb `#dcdee5` hover `#979ba5`；横向 8px `#a0a0a0`；深色侧栏 6px `rgb(151 155 165 / 80%)`。
