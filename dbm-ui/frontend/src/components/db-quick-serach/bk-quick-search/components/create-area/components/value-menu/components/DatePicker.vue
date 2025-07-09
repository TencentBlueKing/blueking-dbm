<template>
  <DatePickerPanel
    v-model="localValue"
    @change="handleChange" />
</template>
<script setup lang="ts">
  import { DatePickerPanel } from 'tdesign-vue-next';

  interface IResult {
    label: string;
    value: string | number;
  }

  type Emits = (e: 'change', value: IResult[]) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IResult[]>({
    default: () => [],
  });

  const localValue = ref<string | number>();

  watch(
    modelValue,
    () => {
      localValue.value = modelValue.value[0]?.value || '';
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string | number | Date) => {
    emits('change', [
      {
        label: `${value}`,
        value: `${value}`,
      },
    ]);
  };
</script>
