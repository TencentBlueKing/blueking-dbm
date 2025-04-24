<template>
  <DbPopconfirm
    :confirm-handler="handleTerminate"
    placement="bottom"
    :title="t('修改定时')"
    trigger="click"
    :width="360">
    <slot />
    <template #content>
      <div style="font-size: 12px; color: #63656e">
        <BkForm
          ref="formRef"
          class="mt-14"
          form-type="vertical"
          :model="formMode">
          <BkFormItem
            :label="t('定时时间')"
            property="trigger_time">
            <BkDatePicker
              v-model="formMode.trigger_time"
              :disabled-date="disableDateMethod"
              format="yyyy-MM-dd HH:mm:ss"
              style="width: 100%"
              type="datetime" />
          </BkFormItem>
        </BkForm>
        <div style="margin-top: 4px; font-size: 12px; color: #979ba5">
          {{ t('原定时时间：') }}
          {{ data.details.trigger_time }}
        </div>
      </div>
    </template>
  </DbPopconfirm>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import { operateTimerFlow } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { messageSuccess } from '@utils';

  interface Props {
    data: FlowMode<{
      run_time: string;
      trigger_time: string;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const eventBus = useEventBus();

  const formMode = reactive({
    trigger_time: props.data.details.trigger_time,
  });

  const disableDateMethod = (value: Date | number) => {
    return dayjs(value).isBefore(dayjs());
  };

  const handleTerminate = () => {
    if (!formMode.trigger_time) {
      return Promise.resolve();
    }
    return operateTimerFlow({
      action: 'change',
      flow_id: props.data.id,
      trigger_time: dayjs(formMode.trigger_time).format('YYYY-MM-DD HH:mm:ss'),
    }).then(() => {
      messageSuccess(t('操作成功'));
      eventBus.emit('refreshTicketStatus');
    });
  };
</script>
