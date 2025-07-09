<template>
  <DateRangePickerPanel
    v-model="localValue"
    @change="handleChange" />
</template>
<script setup lang="ts">
  import { DateRangePickerPanel } from 'tdesign-vue-next';

  interface IResult {
    label: string;
    value: string | number;
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
      localValue.value = [modelValue.value[0].value || '', modelValue.value[1].value || ''];
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: (string | number | Date)[]) => {
    emits('change', [
      {
        label: `${value[0]}`,
        value: `${value[0]}`,
      },
      {
        label: `${value[1]}`,
        value: `${value[1]}`,
      },
    ]);
  };
</script>
