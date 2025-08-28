<template>
  <ElConfigProvider :locale="zhCn">
    <ElDatePickerPanel
      v-model="localValue"
      :border="false"
      :shortcuts="shortcuts"
      type="datetimerange"
      @update:model-value="handleChange" />
  </ElConfigProvider>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { ElConfigProvider, ElDatePickerPanel } from 'element-plus';
  import zhCn from 'element-plus/es/locale/lang/zh-cn';

  interface Props {
    shortcuts?: {
      text: string;
      value: () => [Date, Date];
    }[];
    value?: string;
  }

  defineOptions({
    inheritAttrs: false,
  });

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
    const startDatetimeFormat = dayjs(value[0]).format('YYYY-MM-DD HH:mm:ss');
    const endDatetimeFormat = dayjs(value[1]).format('YYYY-MM-DD HH:mm:ss');
    emits('change', `${startDatetimeFormat},${endDatetimeFormat}`);
  };
</script>
