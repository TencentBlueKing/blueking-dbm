<template>
  <BkSideslider
    v-model:isShow="isShow"
    :before-close="handleClose"
    class="append-config-side"
    render-directive="if"
    :title="isEdit ? t('编辑免审批') : t('添加免审批')"
    :width="840"
    @closed="handleClose">
    <DbForm
      ref="formRef"
      class="append-config-form"
      form-type="vertical">
      <BkAlert
        class="mb16"
        closable>
        {{
          t(
            '添加免审批后，相关单据可直接进入下一环节，无需经过审批流程。免审批可应用于业务下的全部集群或特定部分集群。',
          )
        }}
      </BkAlert>
      <BkFormItem
        :label="t('免审批目标')"
        required>
        <RenderTarget
          ref="targetRef"
          v-model="targetData" />
      </BkFormItem>
    </DbForm>
    <template #footer>
      <BkButton
        class="w-88 mr-8"
        :loading="isCreateSubmitting || isUpdateSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isCreateSubmitting || isUpdateSubmitting"
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
  import { createTicketFlowConfig, updateTicketFlowConfig } from '@services/source/ticket';

  import { useBeforeClose } from '@hooks';

  import { DBTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  import RenderTarget from './render-target/Index.vue';

  interface Props {
    isEdit?: boolean;
    data: TicketFlowDescribeModel;
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    isEdit: false,
  });

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

  const { run: createTicketFlowConfigRun, loading: isCreateSubmitting } = useRequest(createTicketFlowConfig, {
    manual: true,
    onSuccess() {
      isShow.value = false;
      window.changeConfirm = false;
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  const { run: updateTicketFlowConfigRun, loading: isUpdateSubmitting } = useRequest(updateTicketFlowConfig, {
    manual: true,
    onSuccess() {
      isShow.value = false;
      window.changeConfirm = false;
      messageSuccess(t('操作成功'));
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
    const params: ServiceParameters<typeof updateTicketFlowConfig> = {
      ...targetData,
      ticket_types: [props.data.ticket_type],
      configs: {
        need_manual_confirm: props.data.configs.need_manual_confirm,
        need_itsm: false,
      },
    };
    if (props.isEdit) {
      params.config_ids = [props.data.id];
      updateTicketFlowConfigRun(params);
      return;
    }
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
