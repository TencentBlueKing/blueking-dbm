<template>
  <BkDialog
    :is-show="isShow"
    :quick-close="false"
    theme="primary"
    :title="t('批量设置')"
    @closed="handleClose"
    @confirm="handleConfirm">
    <div class="mb-21">
      <I18nT keypath="已选择n个单据类型">
        <span style="font-weight: bold">{{ ticketTypes.length }}</span>
      </I18nT>
    </div>
    <BkCheckbox
      v-for="item in configList"
      :key="item.value"
      v-model="item.checked">
      {{ item.label }}
    </BkCheckbox>
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

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const defaultConfigList = [
    {
      value: 'need_itsm',
      label: t('添加单据审批节点'),
      checked: false,
    },
    {
      value: 'need_manual_confirm',
      label: t('添加人工确认节点'),
      checked: false,
    },
  ];

  const configList = ref(_.cloneDeep(defaultConfigList));

  const { run: updateTicketFlowConfigRun } = useRequest(updateTicketFlowConfig, {
    manual: true,
    onSuccess: (data) => {
      if (!data) {
        isShow.value = false;
        configList.value = _.cloneDeep(defaultConfigList);
        messageSuccess(t('操作成功'));
        emits('success');
      }
    },
  });

  const handleConfirm = () => {
    const params = {
      ticket_types: props.ticketTypes,
      configs: configList.value.reduce<Record<string, boolean>>(
        (results, item) =>
          Object.assign(results, {
            [item.value]: item.checked,
          }),
        {},
      ),
    };
    updateTicketFlowConfigRun(params);
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>
