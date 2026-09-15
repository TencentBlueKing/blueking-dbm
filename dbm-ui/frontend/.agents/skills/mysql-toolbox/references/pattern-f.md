# 模式 F：跨页 Wrapper 导航型

适用于多个独立 ticket_type 共享同一概念（如"迁移方式"），但每种方式是独立 ticket_type、各自有独立 `Index.vue` 的场景。

**参考实现**：`MYSQL_FIXPOINT_EXIST_CLUSTER`（构造：已有集群 / 新集群跨页切换）、`MYSQL_DTS_DATA_MIGRATE` / `MYSQL_DTS_DATA_MIGRATE_RENAME`（DTS 同名迁移 / 库改名迁移）

目录：

- 核心思路
- Wrapper 组件模板
- Index.vue 模板（使用 Wrapper）
- 页面共享模块（common.ts）
- 关键点

## 核心思路

创建一个 **Wrapper 组件**（类似 `FixpointWrapper.vue`），包含两个页面共享的元素：

1. `BkAlert`（顶部提示，文案从原型图获取）
2. `BkForm` 内放模式选择的 `CardCheckbox` 或 `BkRadioGroup`，切换时 `router.push` 到对方路由
3. `<slot />` 供各页面放入自己的 `SmartAction` 内容

每个 `Index.vue` 用 `<Wrapper>` 包裹 `<SmartAction>`，不再各自重复 BkAlert 和模式选择代码。

## Wrapper 组件模板

参考 `MYSQL_FIXPOINT_EXIST_CLUSTER/components/FixpointWrapper.vue`：

```vue
<template>
  <div class="db-toolbox">
    <!-- 1. BkAlert：第一个元素，文案从原型图获取 -->
    <BkAlert
      class="mb-20"
      closable
      :title="t('DTS 数据迁移：按库表将数据从源集群迁到目标集群，一行对应一对源与目标。同名迁移目标库与源库同名，库表支持通配；库改名迁移按整库指定目标库名。库级克隆请使用「MySQL DB 数据克隆」')" />
    <!-- 2. BkForm：模式选择 + slot -->
    <BkForm
      class="mb-24 toolbox-form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('迁移方式')"
        required>
        <CardCheckbox
          v-model="formData.migrateMethod"
          :desc="t('目标库与源库同名，支持按库表筛选和通配')"
          icon="bk-dbm-icon db-icon-copy"
          :title="t('同名迁移')"
          true-value="MYSQL_DTS_DATA_MIGRATE" />
        <CardCheckbox
          v-model="formData.migrateMethod"
          class="ml-8"
          :desc="t('逐库指定目标库名，按整库迁移')"
          icon="bk-dbm-icon db-icon-edit"
          :title="t('库改名迁移')"
          true-value="MYSQL_DTS_DATA_MIGRATE_RENAME" />
      </BkFormItem>
      <!-- 3. slot：各页面放入 SmartAction -->
      <slot />
    </BkForm>
  </div>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const formData = reactive({
    migrateMethod: (route.meta.ticketType as TicketTypes) || TicketTypes.MYSQL_DTS_DATA_MIGRATE,
  });

  watch(
    () => formData.migrateMethod,
    (val) => {
      if (val !== route.meta.ticketType) {
        router.push({ name: val });
      }
    },
  );
</script>
```

## Index.vue 模板（使用 Wrapper）

```vue
<template>
  <DtsMigrateWrapper>
    <SmartAction>
      <BatchInput :config="batchInputConfig" @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="tableRef"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow v-for="(item, index) in formData.tableData" :key="index">
          <!-- 列组件 -->
        </EditableRow>
      </EditableTable>
      <!-- 页级表单项 -->
      <BkFormItem :label="t('数据冲突处理')" required>
        <BkRadioGroup v-model="formData.conflictHandle">
          <BkRadio label="replace">{{ t('覆盖旧数据') }}</BkRadio>
          <BkRadio label="ignore">{{ t('保留旧数据') }}</BkRadio>
          <BkRadio label="error">{{ t('报错并停止') }}</BkRadio>
        </BkRadioGroup>
      </BkFormItem>
      <TicketPayload v-model="formData.payload" />
      <template #action>
        <BkButton class="mr-8 w-88" :loading="isSubmitting" theme="primary" @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbResetButton class="ml-8" :confirm-handler="handleReset" :disabled="isSubmitting" />
      </template>
    </SmartAction>
  </DtsMigrateWrapper>
</template>
```

## 页面共享模块（common.ts）

当两个页面存在完全相同的实现（如冲突枚举映射、规格 ID 提取、resource_spec 组装、提交类型），把重复逻辑抽到其中一个页面目录的 `common.ts`，另一个页面通过 `@views/...` 别名导入，与「RENAME 复用 MIGRATE 的 Wrapper」依赖方向一致：

```typescript
// MYSQL_DTS_DATA_MIGRATE/common.ts
import TendbhaModel from '@services/model/mysql/tendbha';

// DTS resource_spec 组装（master/worker 同规格）
export const buildDtsResourceSpec = (labels: { id: number; value: string }[], specId: number) => ({
  master: {
    count: 1,
    label_names: labels.map((label) => label.value),
    labels: labels.map((label) => String(label.id)),
    spec_id: specId,
  },
  worker: { /* 同 master */ },
});

// 提交 payload 的 resource_spec 类型，替换两页内联重复的 18 行泛型
export interface DtsTicketResourceSpec { /* ... */ }
```

## 关键点

- Wrapper 放在其中一个 ticket_type 的 `components/` 目录下（如 `MYSQL_DTS_DATA_MIGRATE/components/DtsMigrateWrapper.vue`），另一个页面通过 `@views/...` 别名导入
- `BkAlert` 和模式选择代码只写一次（在 Wrapper 中），不在每个 Index.vue 重复
- `EditableTable` 直接在 `SmartAction` 内（Wrapper 的 `BkForm` 通过 slot 包裹），不需要额外包一层 `BkForm`
- `BatchInput` 下方的 `EditableTable` 加 `class="mt-16 mb-20"`
- 模式切换通过 `route.meta.ticketType` 判断当前页，`watch` 监听变化时 `router.push`
- `CardCheckbox` 的 `true-value` 是当前模式的 ticket_type（如 `MYSQL_DTS_DATA_MIGRATE`），同一 `BkFormItem` 内多个 CardCheckbox 共享同一个 v-model
- `CardCheckbox` 的 `title`、`desc`、`BkAlert` 的 `title` 必须从原型图提取原文
- 页级表单项（如数据冲突处理）的 radio **直接绑后端枚举值**（`replace`/`ignore`/`error`），禁止自造前端枚举再写双向映射函数——详情组件本就直查 `on_duplicate`，映射层纯属冗余
