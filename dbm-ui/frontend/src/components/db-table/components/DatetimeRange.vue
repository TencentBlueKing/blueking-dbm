<template>
  <div>
    <DateRangePickerPanel
      v-model="localValue"
      enable-time-picker
      :presets="presets"
      @change="handleChange" />
  </div>
</template>
<script setup lang="ts">
  import { DateRangePickerPanel } from 'tdesign-vue-next';

  interface Props {
    presets?: Record<string, [string, string]>;
    value?: string;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  type Emits = (e: 'change', value: string) => void;

  const localValue = ref<[string, string]>(['', '']);

  watch(
    () => props.value,
    () => {
      if (!props.value) {
        return;
      }
      const [startTime = '', endTime = ''] = props.value.split(',');
      localValue.value = [startTime, endTime];
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: (string | number | Date)[]) => {
    emits('change', `${value[0]},${value[1]}`);
  };
</script>
