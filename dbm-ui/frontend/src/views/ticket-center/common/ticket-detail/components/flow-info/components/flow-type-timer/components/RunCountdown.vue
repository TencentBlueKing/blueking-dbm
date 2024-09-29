<template>
  <span>{{ timeInterval < 1 ? '0s' : getCostTimeDisplay(timeInterval) }}</span>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';

  import { getCostTimeDisplay } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  const modelValue = defineModel<string>();

  const timeInterval = ref(dayjs(modelValue.value).diff(dayjs(), 'second'));

  const { pause } = useTimeoutPoll(
    () => {
      timeInterval.value = timeInterval.value - 1;
      if (timeInterval.value <= 0) {
        setTimeout(() => {
          pause();
        });
      }
    },
    1000,
    {
      immediate: true,
    },
  );
</script>
