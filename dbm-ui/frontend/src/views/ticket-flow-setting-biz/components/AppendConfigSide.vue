<template>
  <BkSideslider
    v-model:isShow="isShow"
    :before-close="handleClose"
    class="append-config-side"
    render-directive="if"
    :title="t('追加配置')"
    :width="840"
    @closed="handleClose">
    <DbForm
      ref="formRef"
      class="append-config-form"
      form-type="vertical">
      <BkAlert
        class="mb16"
        closable>
        {{ t('追加的配置不能与已存在的') }}
      </BkAlert>
      <BkFormItem
        :label="t('目标')"
        required>
        <RenderTarget
          ref="targetRef"
          v-model="targetData" />
      </BkFormItem>
      <BkFormItem
        :label="t('可增加的流程节点')"
        required>
        <BkCheckbox
          v-for="item in configList"
          :key="item.value"
          v-model="item.checked"
          :disabled="item.disabled"
          @change="handleChangeCheckbox">
          {{ item.label }}
        </BkCheckbox>
      </BkFormItem>
    </DbForm>
    <template #footer>
      <BkButton
        class="w-88 mr-8"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { createTicketFlowConfig } from '@services/source/ticket';

  import { useBeforeClose } from '@hooks';

  import { DBTypes } from '@common/const';

  import RenderTarget from './render-target/Index.vue';

  interface Props {
    data: TicketFlowDescribeModel;
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
  const handleBeforeClose = useBeforeClose();

  const formRef = ref();
  const targetRef = ref<InstanceType<typeof RenderTarget>>();
  const needItsm = ref(false);

  const targetData = computed(() => ({
    dbType: (props.data.group as DBTypes) || DBTypes.MYSQL,
    bizId: props.data.bk_biz_id || 0,
    clusterIds: props.data.cluster_ids || [],
  }));

  const configList = computed(() => [
    {
      value: 'need_itsm',
      label: t('单据审批'),
      checked: props.data.configs.need_itsm,
      disabled: false,
    },
    {
      value: 'need_manual_confirm',
      label: t('人工确认'),
      checked: props.data.configs.need_manual_confirm,
      disabled: true,
    },
  ]);

  const { run: createTicketFlowConfigRun, loading: isSubmitting } = useRequest(createTicketFlowConfig, {
    manual: true,
    onSuccess() {
      isShow.value = false;
      window.changeConfirm = false;
      emits('success');
    },
  });

  const handleChangeCheckbox = (value: boolean) => {
    needItsm.value = value;
  };

  const handleClose = async () => {
    window.changeConfirm = true;
    const result = await handleBeforeClose();
    if (!result) {
      return;
    }
    isShow.value = false;
  };

  const handleSubmit = async () => {
    const targetData = await targetRef.value!.getValue();
    const params = {
      ...targetData,
      ticket_types: [props.data.ticket_type],
      configs: {
        need_manual_confirm: props.data.configs.need_manual_confirm,
        need_itsm: needItsm.value,
      },
    };
    createTicketFlowConfigRun(params);
  };
</script>

<style lang="less" scoped>
  .append-config-form {
    padding: 24px 40px 8px;

    :deep(.bk-form-label) {
      font-size: 12px;
      font-weight: bold;
    }
  }

  :deep(.bk-sideslider-footer) {
    padding: 0 40px;
  }
</style>
