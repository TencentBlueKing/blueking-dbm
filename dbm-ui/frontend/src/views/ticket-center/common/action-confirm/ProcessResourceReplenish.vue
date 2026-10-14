<template>
  <DbPopconfirm
    :confirm-handler="handleApproval"
    placement="bottom"
    :title="t('单据重试确认')"
    trigger="click"
    :width="350">
    <slot />
    <template #content>
      <div>
        {{ t('操作：') }}
        <DbTag
          class="mr-4"
          theme="success"
          type="stroke">
          {{ t('重试') }}
        </DbTag>
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
    data: TicketModel;
    // 传入时只处理这条待办，否则按单据处理
    todoData?: FlowMode['todos'][number];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const eventBus = useEventBus();

  const isSubmitting = ref(false);

  const handleApproval = () => {
    isSubmitting.value = true;

    return Promise.resolve()
      .then(() => {
        if (props.todoData) {
          return batchProcessTodo({
            action: 'APPROVE',
            operations: [
              {
                params: {
                  remark: '确认补货',
                  version: props.data.version,
                },
                todo_id: props.todoData.id,
              },
            ],
          });
        }
        return batchProcessTicket({
          action: 'APPROVE',
          params: {
            remark: '确认补货',
            versions: { [props.data.id]: props.data.version },
          },
          ticket_ids: [props.data.id],
        });
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
