<template>
  <div>
    <I18nT
      v-if="data.context.action === 'SKIP'"
      keypath="U_已处理_A"
      scope="global">
      <span>{{ data.done_by }}</span>
      <span style="color: #f59500">{{ t('立即执行') }}</span>
    </I18nT>
    <div
      v-if="data.context.action && data.context.remark"
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
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import { utcDisplayTime } from '@utils';

  interface Props {
    data: FlowMode<
      unknown,
      unknown,
      { action: 'CHANGE' | 'TERMINATE' | 'SKIP'; flow_id: number; remark: string; ticket_id: number }
    >['todos'][number];
  }

  defineOptions({
    name: FlowMode.TODO_STATUS_DONE_SUCCESS,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
