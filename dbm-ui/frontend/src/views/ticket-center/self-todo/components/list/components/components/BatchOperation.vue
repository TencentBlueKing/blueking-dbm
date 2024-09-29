<template>
  <div v-if="isRender">
    <BkButton
      :disabled="ticketList.length < 1"
      theme="primary"
      @click="handleShowDialog">
      {{ title }}
    </BkButton>
    <BkDialog
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
          <BkRadioGroup
            v-if="ticketStatus === TicketModel.STATUS_TODO"
            v-model="formData.action"
            style="display: block">
            <BkRadio
              label="APPROVE"
              style="width: 100%">
              <BkTag
                size="small"
                theme="success"
                type="stroke">
                {{ t('通过') }}
              </BkTag>
              <span>{{ t('通过后，单据将继续往下流转') }}</span>
            </BkRadio>
            <BkRadio
              label="TERMINATE"
              style="margin-left: 0">
              <BkTag
                size="small"
                theme="danger"
                type="stroke">
                {{ t('拒绝') }}
              </BkTag>
              <span>{{ t('拒绝后，单据将被终止') }}</span>
            </BkRadio>
          </BkRadioGroup>
          <BkRadioGroup
            v-else
            v-model="formData.action">
            <BkRadio label="APPROVE">
              <BkTag
                size="small"
                theme="success"
                type="stroke">
                {{ t('确认执行') }}
              </BkTag>
            </BkRadio>
            <BkRadio label="TERMINATE">
              <BkTag
                size="small"
                theme="danger"
                type="stroke">
                {{ t('终止单据') }}
              </BkTag>
            </BkRadio>
          </BkRadioGroup>
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
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-8"
          @click="handleCancle">
          {{ t('取消') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
</template>
<script setup lang="ts">
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTicket } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { messageSuccess } from '@utils';

  interface Props {
    ticketList: TicketModel<unknown>[];
    ticketStatus: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const eventBus = useEventBus();

  const isShow = ref(false);

  const formRef = useTemplateRef('form');
  const isSubmiting = ref(false);
  const formData = reactive({
    action: 'APPROVE' as 'APPROVE' | 'TERMINATE',
    remark: '',
  });

  const isRender = computed(() => [TicketModel.STATUS_TODO, TicketModel.STATUS_APPROVE].includes(props.ticketStatus));
  const title = computed(() => (props.ticketStatus === TicketModel.STATUS_TODO ? t('批量审批') : t('批量确认')));

  const isRemarkRequired = computed(() => formData.action === 'TERMINATE');

  const handleShowDialog = () => {
    isShow.value = true;
  };

  const handleSubmit = () => {
    isSubmiting.value = true;
    formRef
      .value!.validate()
      .then(() =>
        batchProcessTicket({
          action: formData.action,
          ticket_ids: props.ticketList.map((item) => item.id),
          params: {
            remark: formData.remark,
          },
        }),
      )
      .then(() => {
        isShow.value = false;
        messageSuccess(t('操作成功'));
        eventBus.emit('refreshTicketStatus');
      })
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
