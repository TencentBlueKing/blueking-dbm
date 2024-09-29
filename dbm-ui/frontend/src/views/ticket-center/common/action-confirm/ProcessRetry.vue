<template>
  <DbPopconfirm
    :confirm-handler="handleApproval"
    placement="bottom"
    :title="t('单据重试确认')"
    trigger="click">
    <slot />
    <template #content>
      <div>
        {{ t('操作：') }}
        <BkTag
          class="mr-4"
          theme="success"
          type="stroke">
          {{ t('重试') }}
        </BkTag>
        <span>{{ t('重试后，单据将再次尝试申请资源') }}</span>
      </div>
    </template>
  </DbPopconfirm>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
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

  const { t } = useI18n();
  const eventBus = useEventBus();

  const approveFormMode = reactive({
    remark: '',
  });

  const isSubmitting = ref(false);

  const handleApproval = () => {
    isSubmitting.value = true;
    return Promise.resolve()
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
                params: {
                  remark: t('确认提交'),
                },
              },
            ],
          });
        }
        return Promise.reject();
      })
      .then(() => {
        messageSuccess(t('操作成功'));
        eventBus.emit('refreshTicketStatus');
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };
</script>
