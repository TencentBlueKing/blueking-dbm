<template>
  <div>
    <div
      v-if="data.context.remark"
      style="margin-top: 12px; line-height: 16px; color: #63656e">
      <I18nT
        keypath="备注：c"
        scope="global">
        <span>{{ data.context.remark }}</span>
      </I18nT>
    </div>
    <div style="margin-top: 10px; color: #979ba5">{{ utcDisplayTime(data.done_at) }}</div>
  </div>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import { utcDisplayTime } from '@utils';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.TODO_STATUS_DONE_FAILED,
  });
</script>
