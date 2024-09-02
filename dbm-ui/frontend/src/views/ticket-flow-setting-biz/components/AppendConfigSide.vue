<template>
  <BkSideslider
    v-model:isShow="isShow"
    :before-close="handleClose"
    class="append-config-side"
    render-directive="if"
    :title="t('添加免审批')"
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

  const targetData = computed(() => ({
    dbType: (props.data.group as DBTypes) || DBTypes.MYSQL,
    bizId: props.data.bk_biz_id || window.PROJECT_CONFIG.BIZ_ID,
    clusterIds: props.data.cluster_ids || [],
  }));

  const { run: createTicketFlowConfigRun, loading: isSubmitting } = useRequest(createTicketFlowConfig, {
    manual: true,
    onSuccess() {
      isShow.value = false;
      window.changeConfirm = false;
      emits('success');
    },
  });

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
        need_itsm: false,
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
