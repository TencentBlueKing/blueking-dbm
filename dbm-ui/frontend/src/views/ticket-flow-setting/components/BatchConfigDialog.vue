<template>
  <BkDialog
    class="ticket-flow-batch-config-dialog"
    :is-show="showDialog"
    :quick-close="false"
    theme="primary"
    :title="t('批量设置')"
    @confirm="handleConfirmBatchEdit">
    <div class="ticket-flow-batch-config">
      <div class="desc-text">
        {{ t('已选择n个单据类型', { n: ticketTypes.length }) }}
      </div>
      <div class="check-list">
        <BkCheckbox
          v-for="item in configList"
          :key="item.value"
          v-model="item.checked">
          {{ item.label }}
        </BkCheckbox>
      </div>
    </div>
  </BkDialog>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateTicketFlowConfig } from '@services/source/ticket';

  import { messageSuccess } from '@utils';

  interface Props {
    ticketTypes: string[];
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const showDialog = defineModel<boolean>('isShow', {
    default: false,
  });

  const configList = reactive([
    {
      value: 'need_itsm',
      label: t('单据审批'),
      checked: false,
    },
    {
      value: 'need_manual_confirm',
      label: t('人工确认'),
      checked: false,
    },
  ]);

  const { run: runUpdateTicketFlowConfig } = useRequest(updateTicketFlowConfig, {
    manual: true,
    onSuccess: (data) => {
      if (!data) {
        messageSuccess(t('操作成功'));
        emits('success');
        showDialog.value = false;
      }
    },
  });

  const handleConfirmBatchEdit = _.debounce(() => {
    const configs = configList.reduce(
      (results, item) => {
        Object.assign(results, {
          [item.value]: item.checked,
        });
        return results;
      },
      {} as Record<string, boolean>,
    );
    const params = {
      ticket_types: props.ticketTypes,
      configs,
    };
    runUpdateTicketFlowConfig(params);
  }, 500);
</script>

<style lang="less" scoped>
  .ticket-flow-batch-config-dialog {
    :deep(.bk-dialog-header) {
      padding: 16px 24px 28px;
    }

    :deep(.ticket-flow-batch-config) {
      .desc-text {
        margin-bottom: 32px;
        font-size: 14px;
        color: #313238;
      }
    }

    :deep(.bk-dialog-footer) {
      .bk-button {
        width: 64px;
      }
    }
  }
</style>
