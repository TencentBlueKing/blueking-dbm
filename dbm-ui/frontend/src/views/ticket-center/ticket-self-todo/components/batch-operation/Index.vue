<template>
  <div v-if="isRender">
    <BkButton
      :disabled="ticketList.length < 1"
      theme="primary"
      @click="handleShowDialog">
      {{ title }}
    </BkButton>
    <DbDialog
      v-model:is-show="isShow"
      class="ticket-self-todo-batch-operation"
      :title="title">
      <BkForm
        ref="form"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('操作意见')"
          property="action"
          required>
          <component
            :is="actionCom"
            v-model="formData.action" />
        </BkFormItem>
        <BkFormItem
          :label="t('意见')"
          property="remark"
          :required="isRemarkRequired">
          <BkInput
            v-model="formData.remark"
            :maxlength="100"
            :rows="3"
            type="textarea" />
        </BkFormItem>
      </BkForm>
      <template #footer>
        <BkButton
          :loading="isSubmiting"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-8"
          :disabled="isSubmiting"
          @click="handleCancle">
          {{ t('取消') }}
        </BkButton>
      </template>
    </DbDialog>
  </div>
</template>
<script setup lang="ts">
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTicket } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { approvalRequestPayload, handleApprovalError } from '@views/ticket-center/common/ticket-modify/utils';

  import { messageSuccess } from '@utils';

  import StatusApproveAction from './StatusApproveAction.vue';
  import StatusFailed from './StatusFailedAction.vue';
  import StatusResourceReplenishAction from './StatusResourceReplenishAction.vue';
  import StatusTimerAction from './StatusTimerAction.vue';
  import StatusTodoAction from './StatusTodoAction.vue';

  interface Props {
    ticketList: TicketModel<unknown>[];
    ticketStatus: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const eventBus = useEventBus();

  const titleMap = {
    [TicketModel.STATUS_APPROVE]: t('批量审批'),
    [TicketModel.STATUS_FAILED]: t('批量终止'),
    [TicketModel.STATUS_RESOURCE_REPLENISH]: t('批量处理'),
    [TicketModel.STATUS_TIMER]: t('批量处理'),
    [TicketModel.STATUS_TODO]: t('批量处理'),
  };

  const actionComMap = {
    [TicketModel.STATUS_APPROVE]: StatusApproveAction,
    [TicketModel.STATUS_FAILED]: StatusFailed,
    [TicketModel.STATUS_RESOURCE_REPLENISH]: StatusResourceReplenishAction,
    [TicketModel.STATUS_TIMER]: StatusTimerAction,
    [TicketModel.STATUS_TODO]: StatusTodoAction,
  };

  const genDefaultValue = () => ({
    action: 'APPROVE' as 'APPROVE' | 'TERMINATE' | 'SKIP',
    remark: '',
  });
  const isShow = ref(false);

  const formRef = useTemplateRef('form');
  const isSubmiting = ref(false);
  const formData = reactive(genDefaultValue());

  const isRender = computed(() => Boolean(titleMap[props.ticketStatus]));
  const title = computed(() => titleMap[props.ticketStatus]);
  const actionCom = computed(() => actionComMap[props.ticketStatus]);

  const isRemarkRequired = computed(() => formData.action === 'TERMINATE');

  const handleShowDialog = () => {
    Object.assign(formData, genDefaultValue());
    isShow.value = true;
  };

  const handleSubmit = () => {
    // 只有批量审批按「已被提单人重新编辑」提示版本冲突，其它操作沿用请求层提示
    const isApprove = props.ticketStatus === TicketModel.STATUS_APPROVE;
    isSubmiting.value = true;
    formRef
      .value!.validate()
      .then(() =>
        batchProcessTicket(
          {
            action: formData.action,
            params: {
              remark: formData.remark,
              versions: Object.fromEntries(props.ticketList.map((item) => [item.id, item.version])),
            },
            ticket_ids: props.ticketList.map((item) => item.id),
          },
          isApprove ? approvalRequestPayload : {},
        ),
      )
      .then(() => {
        isShow.value = false;
        messageSuccess(t('操作成功'));
        eventBus.emit('refreshTicketStatus');
      })
      .catch((error) => (isApprove ? handleApprovalError(error) : Promise.reject(error)))
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleCancle = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .ticket-self-todo-batch-operation {
    .bk-form-label {
      color: #63656e;
    }
  }
</style>
