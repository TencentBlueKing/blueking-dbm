<template>
  <div style="margin-top: 10px; color: #979ba5">{{ utcDisplayTime(data.done_at) }}</div>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import { utcDisplayTime } from '@utils';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
  }

  defineOptions({
    name: FlowMode.TODO_STATUS_DONE_SUCCESS,
  });

  defineProps<Props>();
</script>
