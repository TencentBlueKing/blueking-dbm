# 工具箱提单页范式

新建工具箱页优先复制同类页面（如 `src/views/db-manage/mysql/MYSQL_CHECKSUM/Index.vue`）。跨 DB 复制成本极低：TendbCluster 与 MySQL 的同名工具几乎逐行相同，差异只在业务列组件与 ticketType。

## 标准骨架（顺序不可调整）

```vue
<template>
  <SmartAction class="db-toolbox mysql-xxx-page">
    <BkAlert class="mb-20" closable :title="t('业务限制说明')" />

    <BatchInput :config="batchInputConfig" @change="handleBatchInput" />

    <BkForm class="mt-16 mb-16 toolbox-form" form-type="vertical" :model="formData">
      <EditableTable :key="tableKey" ref="table" class="mb-20" :model="formData.tableData">
        <EditableRow v-for="(item, index) in formData.tableData" :key="index">
          <ClusterColumn v-model="item.cluster" @batch-edit="handleBatchEdit" />
          <XxxColumn v-model="item.xxx" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>

      <TicketPayload v-model="formData.payload" />
    </BkForm>

    <template #action>
      <BkButton class="mr-8 w-88" :loading="isSubmitting" theme="primary" @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton class="ml-8 w-88" :disabled="isSubmitting">{{ t('重置') }}</BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
```

关键 class：

- `db-toolbox` — 挂在 `SmartAction` 上，启用 `toolbox.less` 的公共样式
- `toolbox-form` — 挂在 `BkForm` 上，label 变为 `12px / bold / #313238`
- `{db}-{feature}-page` — 页面私有样式

标准表格型工具箱页**没有「取消」按钮**，只有「提交」和「重置」。

## Script 层模板

```ts
// 1. 行工厂
const createTableRow = (data = {} as Partial<RowData>) => ({ ...defaults, ...data });

// 2. 表单默认值
const defaultData = () => ({
  payload: createTicketPayload(),
  tableData: [createTableRow()],
});
const formData = reactive(defaultData());
const tableKey = ref(random());
const tableRef = useTemplateRef('table');

// 3. 克隆单据回填（URL 带 ?ticketId=）
useTicketDetail<Mysql.Xxx>(TicketTypes.MYSQL_XXX, {
  onSuccess(ticketDetail) { /* 回填 formData */ },
});

// 4. 提单
const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<DetailsType>(TicketTypes.MYSQL_XXX);

// 5. 返回工具箱首页
defineExpose({
  routerBack() {
    router.push({ name: 'MysqlToolboxIndex' });
  },
});
```

## 可编辑表格

| 项                  | 值                       |
| ------------------- | ------------------------ |
| 表头背景 / hover    | #f0f1f5 / #eaebf0        |
| 单元格字号          | 12px                     |
| 单元格 `min-height` | 40px                     |
| focus 边框          | #3a84ff                  |
| 错误态背景 / 边框   | #fff1f1 / #ea3636        |
| 操作列              | `fixed="right"`，100px   |
| 行图标默认 / hover  | #c4c6cc / #979ba5，14px  |
| 最少保留行数        | 1（`minRow`）            |

`EditableTable` 暴露的方法：`validate()`、`validateByRowIndex(n)`、`validateByField(field)`、`viewError(errorList)`。

列头两种批量入口：

- **批量选择集群 / 主机** — `#headAppend` slot 放 `.batch-host-select` 图标，选中后 `emit('batch-edit', list)`
- **统一设置列值** — 用 `batch-edit-column-new`，tippy 弹层

## 批量录入 Dialog

| 项           | 值                                |
| ------------ | --------------------------------- |
| 宽度         | 1200px                            |
| 格式说明区   | `padding: 16px`，背景 #f5f7fa     |
| 输入区高度   | 310px                             |
| 覆盖选项     | checkbox「覆盖表格已有数据」      |
| 底部按钮     | 确定 / 取消，各 `w-88`            |

清空表格的标准手法是 `tableKey.value = random()` 强制 remount。

## 校验与提交流程

```
1. 用户点「提交」
2. await tableRef.value!.validate()          整表校验，失败即 return
3. createTicketRun({ details, ...formData.payload })
4a. 成功  → Message 6s toast +「查看详情」外链
          → eventBus.emit('db-toolbox-success')
          → 布局壳 remount 当前路由（表单清空，可连续提单）
          → window.changeConfirm = false
4b. 重复单据(code 8704005) → InfoBox「是否继续提交单据」
          → 确认后带 ignore_duplication: true 重提
4c. 失败  → eventBus.emit('db-toolbox-error')
          → 布局壳底部 Teleport 渲染 BkAlert theme="danger"
          → 用户修改表格时自动清除该错误
```

**提交成功不跳转成功页**，而是原地清空表单让用户继续提单。只有多步 wizard 的最后一步才用 `src/components/ticket-success/`。

## 错误提示的三个层级

| 层级       | 位置                                   | 触发                                                  |
| ---------- | -------------------------------------- | ----------------------------------------------------- |
| 单元格级   | 输入框右侧红色感叹号 + tooltip         | `required`（trigger change）/ 自定义 rules（trigger blur） |
| 页面级     | 底部固定栏上方 `BkAlert theme="danger"` | 提单接口返回错误                                      |
| 行级回填   | `tableRef.viewError(errorList)`        | 后端返回按行的错误数组                                |

`required` 的默认文案由 Column 自动拼成 `${label}不能为空`，不用每列手写。

## 新建工具箱页的注册清单

- [ ] 建目录 `src/views/db-manage/{db}/{TICKET_TYPE}/Index.vue`，目录名 = `TicketTypes` 枚举值（全大写）
- [ ] 在 `ticketTypes.ts` 注册枚举，值与目录名、路由 name 三者完全一致
- [ ] 在 `{db}/routes.ts` 用 `createRouteItem()` 注册路由
- [ ] 在 `ticket-detail/.../com-factory/{db}/` 建详情组件，`defineOptions({ name: TicketTypes.XXX })` 必须匹配
- [ ] 页面按上述骨架实现，优先复用 `common/toolbox-field` 与 `{db}/common/toolbox-field` 下的公共列

## 参考实现

- `src/views/db-manage/mysql/MYSQL_CHECKSUM/Index.vue` — 页面模板
- `src/components/editable-table/Index.vue`
- `src/views/db-manage/common/toolbox-field/column/operation-column/` — 行操作列
- `src/views/db-manage/common/batch-input/` — 批量录入
- `src/hooks/useCreateTicket.tsx`、`src/hooks/useTicketDetail.ts`

## 旧范式（勿用于新页面）

`src/components/mysql-toolbox/ToolboxTable.vue` 基于 `DbOriginalTable` + `DbForm`，行高 42px、操作列宽 120px。新页面一律用 `EditableTable`。
