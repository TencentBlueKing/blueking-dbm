<template>
  <span class="duration-counter-main">
    {{ durationTimeDisplay }}
  </span>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';

  import { getCostTimeDisplay } from '@utils';

  import { useIntervalFn } from '@vueuse/core';

  interface Props {
    endTime?: string | number;
    startTime?: string | number;
  }

  const props = withDefaults(defineProps<Props>(), {
    endTime: undefined,
    startTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  });

  const durationTimeDisplay = ref('');

  // 计时
  const { pause, resume } = useIntervalFn(() => {
    const duratiopn = Math.floor(Date.now() / 1000) - dayjs(props.startTime).valueOf() / 1000;
    durationTimeDisplay.value = getCostTimeDisplay(duratiopn);
  }, 1000);

  watch(
    () => [props.startTime, props.endTime],
    () => {
      if (props.endTime) {
        pause();
        const duration = dayjs(props.endTime).valueOf() / 1000 - dayjs(props.startTime).valueOf() / 1000;
        durationTimeDisplay.value = getCostTimeDisplay(duration);
        return;
      }

      resume();
    },
    {
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    pause();
  });
</script>
