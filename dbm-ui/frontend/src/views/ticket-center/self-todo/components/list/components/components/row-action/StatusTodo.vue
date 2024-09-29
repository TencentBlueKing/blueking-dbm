<template>
  <DbPopconfirm
    :confirm-handler="handleApproval"
    placement="bottom"
    :title="t('单据审批')"
    trigger="click"
    :width="400">
    <BkButton
      class="mr-8"
      :loading="isSubmitting"
      text
      theme="primary">
      {{ t('通过') }}
    </BkButton>
    <template #content>
      <div>
        <span>{{ t('审批意见') }}</span>
        <BkTag
          size="small"
          theme="success"
          type="stroke">
          {{ t('通过') }}
        </BkTag>
        <span>{{ t('通过后，单据将继续往下流转') }}</span>
      </div>
      <BkForm
        ref="approveForm"
        class="mt-8"
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
  <DbPopconfirm
    :confirm-handler="handleTerminate"
    placement="bottom"
    :title="t('单据审批')"
    trigger="click"
    :width="400">
    <BkButton
      class="mr-8"
      :loading="isSubmitting"
      text
      theme="primary">
      {{ t('拒绝') }}
    </BkButton>
    <template #content>
      <div style="padding-bottom: 20px; font-size: 12px; color: #63656e">
        <div>
          <span>{{ t('审批意见') }}</span>
          <BkTag
            size="small"
            theme="danger"
            type="stroke">
            {{ t('拒绝') }}
          </BkTag>
          <span>{{ t('通过后，单据将继续往下流转') }}</span>
        </div>
        <BkForm
          ref="terminateForm"
          class="mt-8"
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
  <TicketClone :data="data" />
</template>
<script setup lang="ts">
  import { ref, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTicket } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import TicketClone from '@views/ticket-center/common/TicketClone.vue';

  import { messageSuccess } from '@utils';

  interface Props {
    data: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  const eventBus = useEventBus();
  const { t } = useI18n();

  const approveForm = useTemplateRef('approveForm');
  const terminateForm = useTemplateRef('terminateForm');

  const approveFormMode = reactive({
    remark: '',
  });
  const terminateFormMode = reactive({
    remark: '',
  });
  const isSubmitting = ref(false);

  const handleApproval = () => {
    isSubmitting.value = true;
    return approveForm
      .value!.validate()
      .then(() =>
        batchProcessTicket({
          action: 'APPROVE',
          ticket_ids: [props.data.id],
          params: approveFormMode,
        }),
      )
      .then(() => {
        eventBus.emit('refreshTicketStatus');
        messageSuccess(t('操作成功'));
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleTerminate = () => {
    isSubmitting.value = true;
    return terminateForm
      .value!.validate()
      .then(() =>
        batchProcessTicket({
          action: 'TERMINATE',
          ticket_ids: [props.data.id],
          params: terminateFormMode,
        }),
      )
      .then(() => {
        eventBus.emit('refreshTicketStatus');
        messageSuccess(t('操作成功'));
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };
</script>
