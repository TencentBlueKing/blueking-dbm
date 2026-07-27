# 列表页范式

新建列表页优先复制 `src/views/db-manage/mysql/ha-cluster-list/Index.vue`。

## 标准骨架

```vue
<template>
  <div class="xxx-list-page">
    <div class="operation-box">
      <AuthButton theme="primary" action-id="xxx">{{ t('申请实例') }}</AuthButton>
      <ClusterBatchOperation class="ml-8" :selected="selectedList" @success="fetchData" />
      <BkButton class="ml-8">{{ t('导出') }}</BkButton>
      <DbQuickSearch
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <ClusterTable
      selectable
      releate-url-query
      :bk-ui-settings="settings"
      @bk-ui-settings-change="updateTableSettings" />
  </div>
</template>

<style lang="less">
  .xxx-list-page {
    .operation-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
```

搜索框靠 `margin-left: auto` 推到右侧，**不要用 `justify-content: space-between`**，因为左侧按钮数量不定。

## 操作区

顺序固定：主按钮（`theme="primary"`）→ 批量操作 → 导出 / 复制 → 搜索（最右）。

按钮之间用 `class="ml-8"`。按钮较多时可改用 `display: flex; flex-wrap: wrap; gap: 8px`。

## 搜索区宽度

| 宽度  | 场景                                 |
| ----- | ------------------------------------ |
| 500px | 集群列表、实例列表、白名单（主流）   |
| 550px | 单据中心                             |
| 560px | 标签管理、人员管理、资源池（条件多） |

## 列宽约定

| 列                       | fixed | 宽度                       | 说明                             |
| ------------------------ | ----- | -------------------------- | -------------------------------- |
| 选择列                   | left  | 80px（新栈）/ 70px（旧栈） | 表头带「本页全选 / 跨页全选」下拉 |
| 操作列（集群）           | left  | 30px                       | 只放 more 图标，行 hover 才显形  |
| 操作列（单据 / 配置类）  | right | 80 ~ 140px                 | inline text 按钮，间距 `mr-8`    |
| 主访问入口（域名）       | left  | min 180 / 280px            | 屏宽 < 1366 时收窄到 180         |
| 集群名称 / 标识          | —     | min 200 / 150px            | 用 `TextOverflowLayout`          |
| 状态                     | —     | 100px                      | 状态点 + 文字，间距 4px          |
| 部署时间                 | —     | 180px                      | 带 sorter                        |
| 创建人                   | —     | 140px                      | —                                |

集群列表的通用列改 `src/views/db-manage/common/cluster-table/CommonColumn.vue`；某个集群独有的列，先在 `cluster-table/Index.vue` 新增以字段名命名的 slot，再在该集群列表里实现。

## 操作列的两种流派

按操作数量选，不要混用：

- **超过 3 个操作** → 收进左侧 30px 的 `OperationMenu` 气泡菜单。菜单项 `line-height: 32px`、`padding: 0 12px`、`font-size: 12px`、hover 变 `#3a84ff`。
- **3 个及以内** → 右侧 inline `text` 按钮，间距 `mr-8`。

## 分页与空态

| 项           | 值                                             |
| ------------ | ---------------------------------------------- |
| 默认 limit   | 20                                             |
| limit 选项   | `[10, 20, 50, 100]`，新栈可加 200 / 500        |
| 持久化       | `localStorage: table_pagination_limit`         |
| layout       | `['total', 'limit', 'list']` 右对齐            |
| footer 高度  | 60px，`padding: 0 16px`                        |
| 空态区高度   | 260px，`padding-top: 48px`，字号 12px          |

空态用 `EmptyStatus` 三态：异常 → `type="500"` + 刷新按钮；搜索无结果 → `type="search-empty"` + 清空搜索；默认 → `type="empty"`。

Loading 用 `<BkLoading :loading="isLoading" :z-index="2">`。

## 行内渲染的 6 个套路

| 模式             | 实现                                                                   | 关键值                                |
| ---------------- | ---------------------------------------------------------------------- | ------------------------------------- |
| 复制按钮 hover 显形 | `role='table-cell-operation'` 默认 `display: none`，`tr:hover` 时显示 | 色 #3a84ff，间距 4px                  |
| 多值折叠         | 只渲染前 6 条，超出显示「共 n 个 查看更多」                            | 阈值 6                                |
| 空值占位         | `value \|\| '--'`                                                      | —                                     |
| 搜索命中高亮     | `TextHighlight` 组件                                                   | #F59500                               |
| 行状态着色       | 选中 / 新增 / 离线                                                     | #ebf2ff / #f3fcf5 / 字色 #c4c6cc      |
| 单行省略         | `TextOverflowLayout`，溢出才挂 tooltip                                 | —                                     |

## 批量选择

```ts
const { selectedList, selectedIdList, isSelected } = useClusterTableSelect();
```

- 批量按钮禁用条件：`:disabled="selectedIdList.length < 1"`，禁用时必须配 `v-bk-tooltips` 说明原因
- 新请求（非翻页 / 排序触发）自动清空选择
- 禁止某行被选：`disableSelectMethod` 返回 `true` 或提示字符串

## 列显示配置

用 `useTableSettings`，存到**服务端用户 Profile**（不是 localStorage），key 取自 `UserPersonalSettings` 枚举。必须声明 `disabled` 把主键列设为不可隐藏。

```ts
const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TENDBHA_TABLE_SETTINGS, {
  disabled: ['master_domain'],
});
```

## 参考实现

- `src/views/db-manage/mysql/ha-cluster-list/Index.vue` — 集群列表模板
- `src/views/db-manage/common/cluster-table/Index.vue` — 集群列表基类
- `src/components/db-table/IndexNew.vue` — 新栈表格
- `src/hooks/useTableSettings.ts`
