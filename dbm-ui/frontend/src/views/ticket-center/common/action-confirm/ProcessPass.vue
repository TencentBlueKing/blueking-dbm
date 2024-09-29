<template>
  <DbPopconfirm
    :confirm-handler="handleApproval"
    placement="bottom"
    :title="t('单据审批通过确认')"
    trigger="click"
    :width="400">
    <slot />
    <template #content>
      <div>
        {{ t('操作：') }}
        <BkTag
          class="mr-4"
          theme="success"
          type="stroke">
          {{ t('通过') }}
        </BkTag>
        <span>{{ t('通过后，单据将进入下一步骤') }}</span>
      </div>
      <BkForm
        ref="approveForm"
        class="mt-14"
        form-type="vertical"
        :model="approveFormMode">
        <BkFormItem
          :label="t('备注')"
          property="remark">
          <BkInput
            v-model="approveFormMode.remark"
            :maxlength="100"
            :rows="3"
            type="textarea" />
        </BkFormItem>
      </BkForm>
    </template>
  </DbPopconfirm>
</template>
<script setup lang="ts">
  import { ref, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTicket, batchProcessTodo } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { messageSuccess } from '@utils';

  interface Props {
    data?: TicketModel<unknown>;
    todoData?: FlowMode<unknown>['todos'][number];
  }

  const props = defineProps<Props>();

  const eventBus = useEventBus();
  const { t } = useI18n();

  const approveForm = useTemplateRef('approveForm');

  const approveFormMode = reactive({
    remark: '',
  });

  const isSubmitting = ref(false);

  const handleApproval = () => {
    isSubmitting.value = true;
    return approveForm
      .value!.validate()
      .then(() => {
        if (props.data) {
          return batchProcessTicket({
            action: 'APPROVE',
            ticket_ids: [props.data.id],
            params: approveFormMode,
          });
        }
        if (props.todoData) {
          return batchProcessTodo({
            action: 'APPROVE',
            operations: [
              {
                todo_id: props.todoData.id,
                params: approveFormMode,
              },
            ],
          });
        }
        return Promise.reject();
      })
      .then(() => {
        eventBus.emit('refreshTicketStatus');
        messageSuccess(t('操作成功'));
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };
</script>
