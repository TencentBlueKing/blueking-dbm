<template>
  <ElDatePickerPanel
    v-model="localValue"
    :border="false"
    type="datetime"
    @update:model-value="handleChange" />
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { ElDatePickerPanel } from 'element-plus';

  interface IResult {
    label: string;
    value: string;
  }

  type Emits = (e: 'change', value: IResult[]) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IResult[]>({
    default: () => [],
  });

  const localValue = ref<string>();

  watch(
    modelValue,
    () => {
      localValue.value = modelValue.value[0]?.value || '';
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string) => {
    const valueFormat = dayjs(value).format('YYYY-MM-DD HH:mm:ss');
    emits('change', [
      {
        label: valueFormat,
        value: valueFormat,
      },
    ]);
  };
</script>
