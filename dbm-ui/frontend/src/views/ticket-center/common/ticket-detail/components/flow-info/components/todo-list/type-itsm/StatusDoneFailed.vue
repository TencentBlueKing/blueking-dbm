<template>
  <div>
    <div
      v-if="data.context.remark"
      class="mt-12"
      style="line-height: 16px; color: #63656e">
      <I18nT
        keypath="备注：c"
        scope="global">
        <span>{{ data.context.remark }}</span>
      </I18nT>
    </div>
    <div
      class="mt-12"
      style="color: #979ba5">
      {{ utcDisplayTime(data.done_at) }}
    </div>
  </div>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import { utcDisplayTime } from '@utils';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
  }

  defineOptions({
    name: FlowMode.TODO_STATUS_DONE_FAILED,
  });

  defineProps<Props>();
</script>
