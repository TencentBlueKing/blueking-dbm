<template>
  <EditableTableColumn
    :field="field"
    :label="label"
    :min-width="180"
    required
    :rules="rules">
    <EditableDatePicker
      v-model="modelValue"
      :disabled-date="disabledDate"
      format="yyyy-MM-dd HH:mm:ss"
      type="datetime">
      <template #footer>
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

  interface Props {
    label: string;
    field: string;
    disabledDate?: (params: any) => boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    disabledDate: () => false,
  });

  const { t } = useI18n();

  const modelValue = defineModel<string | Date>();

  const isNowTime = ref(false);

  const rules = [
    {
      required: true,
      validator: (value: string[]) => {
        if (isNowTime.value) {
          return true;
        }
        return Boolean(value);
      },
      message: `${props.label}${t('不能为空')}`,
      trigger: 'blur',
    },
  ];

  watch(modelValue, () => {
    isNowTime.value = false;
  });

  const handleNowTime = () => {
    modelValue.value = '';
    setTimeout(() => {
      isNowTime.value = true;
    });
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
</style>
