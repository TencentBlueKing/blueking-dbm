<template>
  <EditableColumn
    :append-rules="rules"
    field="execute_db"
    :label="t('变更 DB')"
    :min-width="300"
    required>
    <template #headAppend>
      <div style="display: flex">
        <BatchEditColumn
          :confirm-handler="handleBatchEditConfirm"
          :label="t('变更 DB')">
          <BatchEditTagInput v-model="batchEditValue" />
        </BatchEditColumn>
        <span style="margin-left: 4px; font-size: 12px; font-weight: normal; color: #8a8f99">
          ({{ t('如果变更 SQL 是“create database ...”，这个请填写 master') }})
        </span>
      </div>
    </template>
    <EditableTagInput
      v-model="modelValue"
      :placeholder="t('请输入DB名称_支持通配符_含通配符的仅支持单个')" />
    <template #tips>
      <div>{{ t('不允许输入系统库，如"msdb", "model", "tempdb", "Monitor"') }}</div>
      <div>{{ t('DB名、表名不允许为空，忽略DB名、忽略表名不允许为 *') }}</div>
      <div>{{ t('支持 %（指代任意长度字符串）,*（指代全部）2个通配符') }}</div>
      <div>{{ t('单元格可同时输入多个对象，使用换行，空格或；，｜分隔，按 Enter 或失焦完成内容输入') }}</div>
      <div>{{ t('包含通配符时, 每一单元格只允许输入单个对象。% 不能独立使用， * 只能单独使用') }}</div>
    </template>
  </EditableColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn, { BatchEditTagInput } from '@views/db-manage/common/batch-edit-column-new/Index.vue';

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('有 master 时只允许一个'),
      trigger: 'change',
      validator: (value: string[]) => !(value.includes('master') && value.length > 1),
    },
    {
      message: t('* 只能独立使用'),
      trigger: 'change',
      validator: (value: string[]) => !_.some(value, (item) => /\*/.test(item) && item.length > 1),
    },
    {
      message: t('% 不允许单独使用'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => !/^%$/.test(item)),
    },
    {
      message: t('含通配符的单元格仅支持输入单个对象'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (_.some(value, (item) => /[*%?]/.test(item))) {
          return value.length < 2;
        }
        return true;
      },
    },
  ];

  const batchEditValue = ref<string[]>([]);

  const handleBatchEditConfirm = () => {
    emits('batch-edit', batchEditValue.value, 'execute_db');
  };
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
