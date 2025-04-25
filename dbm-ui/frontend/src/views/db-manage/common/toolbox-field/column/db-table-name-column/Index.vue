<template>
  <EditableColumn
    :field="field"
    :label="label"
    :min-width="200"
    :required="required"
    :rules="rules">
    <template
      v-if="showBatchEdit"
      #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :single="single"
        :title="label"
        type="taginput"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-select-button"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <template #tips>
      <slot name="tip" />
    </template>
    <EditableTagInput
      v-model="modelValue"
      allow-auto-match
      allow-create
      clearable
      :disabled="disabled"
      has-delete-icon
      :max-data="single ? 1 : -1"
      :paste-fn="tagInputPasteFn"
      :placeholder="placeholder"
      @change="handleChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { type VNode } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  import { Column } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    disabled?: boolean;
    field: string;
    label: string;
    placeholder: string;
    required?: boolean;
    rules: NonNullable<ComponentProps<typeof Column>['rules']>;
    showBatchEdit?: boolean;
    single?: boolean;
  }

  interface Emits {
    (e: 'batch-edit', value: string[]): void;
    (e: 'change'): void;
  }

  interface Slots {
    tip: VNode;
  }

  withDefaults(defineProps<Props>(), {
    disabled: false,
    required: true,
    showBatchEdit: true,
  });
  const emits = defineEmits<Emits>();

  defineSlots<Slots>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const isShowBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string | string[]) => {
    emits('batch-edit', value as string[]);
  };

  const handleChange = () => {
    emits('change');
  };

  const tagInputPasteFn = (value: string) => value.split(batchSplitRegex).map((item) => ({ id: item }));
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
