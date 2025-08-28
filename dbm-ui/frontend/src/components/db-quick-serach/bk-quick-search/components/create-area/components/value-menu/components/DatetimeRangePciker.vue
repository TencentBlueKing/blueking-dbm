<template>
  <ElDatePickerPanel
    v-model="localValue"
    :border="false"
    type="datetimerange"
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

  const localValue = ref<IResult['value'][]>(['', '']);

  watch(
    modelValue,
    () => {
      if (modelValue.value.length < 1) {
        return;
      }
      localValue.value = [modelValue.value[0]!.value || '', modelValue.value[1]!.value || ''];
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string[]) => {
    const startDatetimeFormat = dayjs(value[0]).format('YYYY-MM-DD HH:mm:ss');
    const endDatetimeFormat = dayjs(value[1]).format('YYYY-MM-DD HH:mm:ss');
    localValue.value = value;

    emits('change', [
      {
        label: startDatetimeFormat,
        value: startDatetimeFormat,
      },
      {
        label: endDatetimeFormat,
        value: endDatetimeFormat,
      },
    ]);
  };
</script>
