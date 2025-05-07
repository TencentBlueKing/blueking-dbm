<template>
  <EditableTableColumn
    :field="field"
    :label="label"
    :min-width="200"
    required
    :rules="rules">
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :disable-fn="disabledDate"
        :title="label"
        type="datetime"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableDatePicker
      v-model="modelValue"
      :disabled-date="disabledDate"
      format="yyyy-MM-dd HH:mm:ss"
      type="datetime">
      <template
        v-if="nowenable"
        #footer>
        <div
          style="line-height: 32px; text-align: center; cursor: pointer"
          @click="handleNowTime">
          now
        </div>
      </template>
    </EditableDatePicker>
    <div
      v-if="isNowTime"
      class="datetime-column-value-now">
      now
    </div>
  </EditableTableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import {
    Column as EditableTableColumn,
    DatePicker as EditableDatePicker,
  } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    disabledDate?: (params: any) => boolean;
    field: string;
    label: string;
    nowenable?: boolean;
  }

  interface Emits {
    (e: 'change'): void;
    (e: 'batch-edit', value: string, field: string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    disabledDate: () => false,
    nowenable: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string | Date>();

  const { t } = useI18n();

  const isNowTime = ref(false);
  const showBatchEdit = ref(false);

  const rules = [
    {
      message: `${props.label}${t('不能为空')}`,
      required: true,
      trigger: 'blur',
      validator: (value: string[]) => {
        if (isNowTime.value) {
          return true;
        }
        return Boolean(value);
      },
    },
  ];

  watch(modelValue, () => {
    isNowTime.value = modelValue.value === 'now';
    emits('change');
  });

  const handleNowTime = () => {
    modelValue.value = 'now';
    setTimeout(() => {
      isNowTime.value = true;
    });
  };

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value as string, props.field);
  };
</script>

<style lang="less">
  .datetime-column-value-now {
    position: absolute;
    display: flex;
    padding: 0 16px;
    pointer-events: none;
    cursor: pointer;
    inset: 0;
    align-items: center;
    justify-content: center;
  }

  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
