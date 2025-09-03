<template>
  <ElDatePickerPanel
    :key="refreshKey"
    v-model="localValue"
    :border="false"
    v-bind="attrs"
    :default-time="defaultTime"
    type="datetimerange"
    @update:model-value="handleChange">
  </ElDatePickerPanel>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { ElDatePickerPanel } from 'element-plus';
  import { useAttrs } from 'vue';

  interface IResult {
    label: string;
    value: string;
  }

  type Emits = (e: 'change', value: IResult[]) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IResult[]>({
    default: () => [],
  });

  const attrs = useAttrs();

  const refreshKey = ref(0);
  const localValue = ref<IResult['value'][]>(['', '']);

  const defaultTime: [Date, Date] = [new Date(2000, 1, 1, 0, 0, 0), new Date(2000, 2, 1, 23, 59, 59)];

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
    refreshKey.value = Date.now();

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
