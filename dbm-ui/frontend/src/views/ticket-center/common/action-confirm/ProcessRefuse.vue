<template>
  <DbPopconfirm
    :confirm-handler="handleTerminate"
    placement="bottom"
    :title="t('单据审批拒绝确认')"
    trigger="click"
    :width="400">
    <slot />
    <template #content>
      <div style="font-size: 12px; color: #63656e">
        <div>
          {{ t('操作：') }}
          <BkTag
            class="mr-4"
            theme="danger"
            type="stroke">
            {{ t('拒绝') }}
          </BkTag>
          <span>{{ t('拒绝后，单据将作废处理') }}</span>
        </div>
        <BkForm
          ref="terminateForm"
          class="mt-14"
          form-type="vertical"
          :model="terminateFormMode">
          <BkFormItem
            :label="t('备注')"
            property="remark"
            required>
            <BkInput
              v-model="terminateFormMode.remark"
              :maxlength="100"
              :rows="3"
              type="textarea" />
          </BkFormItem>
        </BkForm>
      </div>
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

  const terminateForm = useTemplateRef('terminateForm');

  const terminateFormMode = reactive({
    remark: '',
  });
  const isSubmitting = ref(false);

  const handleTerminate = () => {
    isSubmitting.value = true;
    return terminateForm
      .value!.validate()
      .then(() => {
        if (props.data) {
          return batchProcessTicket({
            action: 'TERMINATE',
            ticket_ids: [props.data.id],
            params: terminateFormMode,
          });
        }
        if (props.todoData) {
          return batchProcessTodo({
            action: 'TERMINATE',
            operations: [
              {
                todo_id: props.todoData.id,
                params: terminateFormMode,
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
