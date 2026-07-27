# 详情页范式

**详情页不是左右两栏。** 统一是「顶部灰底摘要栏 + 下方纵向卡片栈或 Tab 面板」，卡片内部才是 50% 宽的双列 KV 网格。

## 三种详情容器

| 容器                 | 宽度                       | 适用                             | 关闭方式                  |
| -------------------- | -------------------------- | -------------------------------- | ------------------------- |
| `TableDetailDialog`  | 60%，可拖至 90%，min 300px | 列表点行看详情，保留列表上下文   | 点空白自动关闭 / 右上 X   |
| `DbSideslider`       | 960px 为主                 | 编辑型详情，需要 footer 提交     | footer 取消 / X（走离开确认） |
| 整页详情             | 内容区全宽                 | 单据详情等可分享链接的场景       | 面包屑返回箭头            |

## 顶部摘要栏

`DisplayBox`（集群）与 `ticket-detail`（单据）共用同一套规范：

| 元素                     | 规范                                        |
| ------------------------ | ------------------------------------------- |
| 背景                     | #f0f1f5                                     |
| padding                  | `16px 60px 16px 20px`（右侧留关闭按钮位）   |
| 主标题（域名 / 单据类型） | 16px / 700 / #313238 / `line-height: 24px`  |
| meta 行                  | 12px / `line-height: 20px`                  |
| meta label               | #979ba5                                     |
| meta value               | #313238                                     |
| meta 项间距              | 40px                                        |

## KV 信息项

用 `InfoList` + `InfoItem`，不要手写 flex。

| 元素         | 规范                                       |
| ------------ | ------------------------------------------ |
| 布局         | `flex: 1 0 50%`，每行两列                  |
| 行高         | 32px（或 20px + `padding-top: 6px`）       |
| label 对齐   | 右对齐，`padding-right: 8px`               |
| label 宽度   | **运行时计算同组最宽值对齐**，不写死像素   |
| label 色     | #4d4f56（集群）/ 继承（单据）              |
| value 色     | #313238                                    |
| 空值         | `'--'`                                     |

```vue
<InfoList>
  <InfoItem :label="t('字段名')">
    {{ value || '--' }}
  </InfoItem>
</InfoList>
```

多字段紧凑排布时用 `<table>`（如单据基本信息）：行高 32px，label 右对齐，首列 100px，其余奇数列 150px。

## 单据详情的三段式

```
DbCard「基本信息」   BaseInfo   → <table> 三列 KV，行高 32px
   ↕ margin-top 16px
DbCard「需求信息」   TaskInfo   → com-factory 按 ticket_type 动态匹配组件
                                  内部用 InfoList + InfoItem 50% 双列
   ↕ margin-top 16px
DbCard「实施进度」   FlowInfos  → 流程时间线

SmartAction #action → 克隆单据 / 撤销单据 / 终止单据

卡片内容区 padding-left: 116px（为左侧标题带留位）
详情页全局基准字号 12px
```

新增单据类型时，在 `src/views/ticket-center/common/ticket-detail/components/task-info/com-factory/{db}/` 下建组件，并且：

```ts
defineOptions({
  name: TicketTypes.MYSQL_ADD_SLAVE, // 必须等于 ticket_type 字符串，工厂靠它动态匹配
  inheritAttrs: false,
});
```

## 集群详情面板

`ActionPanel` 用 `BkTab type="card-tab"`，Tab 内容区 `padding: 0 24px`，高度 `calc(100vh - top - 42px)`。

## 分组标题

区块标题**不用左侧竖线**，只用 `font-weight: bold` + `#313238`（class 为 `.info-title`），区块间距 `mt-20`。

带竖线感的 `.title-spot` 是工具箱表单页的标题样式，两者不要混用。

## 参考实现

- `src/views/ticket-center/common/ticket-detail/Index.vue`
- `src/views/db-manage/common/cluster-details/DisplayBox.vue`
- `src/views/db-manage/common/cluster-details/base-info/components/InfoItem.vue`
- `src/components/table-detail-dialog/Index.vue`
