<template>
  <DbDialog
    :is-show="isShow"
    :quick-close="false"
    theme="primary"
    :title="t('批量设置')"
    @closed="handleClose">
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
    <!-- 提交时需要 loading 并禁用取消，改为自写底部按钮 -->
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isSubmitting"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isSubmitting"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbDialog>
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

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const defaultConfigList = [
    {
      checked: false,
      label: t('添加单据审批节点'),
      value: 'need_itsm',
    },
    {
      checked: false,
      label: t('添加人工确认节点'),
      value: 'need_manual_confirm',
    },
  ];

  const configList = ref(_.cloneDeep(defaultConfigList));

  const { loading: isSubmitting, run: updateTicketFlowConfigRun } = useRequest(updateTicketFlowConfig, {
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
      configs: configList.value.reduce<Record<string, boolean>>(
        (results, item) =>
          Object.assign(results, {
            [item.value]: item.checked,
          }),
        {},
      ),
      ticket_types: props.ticketTypes,
    };
    updateTicketFlowConfigRun(params);
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>
