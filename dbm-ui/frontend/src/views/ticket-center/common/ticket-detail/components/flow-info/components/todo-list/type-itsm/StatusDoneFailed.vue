<template>
  <div
    v-if="data.context.remark"
    style="margin-top: 12px; line-height: 16px; color: #63656e">
    <I18nT keypath="备注：c">
      <span>{{ data.context.remark }}</span>
    </I18nT>
  </div>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.TODO_STATUS_DONE_FAILED,
  });
</script>
