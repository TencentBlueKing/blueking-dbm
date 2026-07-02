<template>
  <DbSideslider
    v-model:is-show="isShow"
    :before-close="handleBeforeClose"
    class="edit-policy-side"
    :width="840"
    @closed="handleClosed">
    <template #header>
      <span>{{ titleText }}</span>
      <span class="ticket-type-subtitle">{{ data.ticket_type_display }}</span>
    </template>
    <DbForm
      ref="formRef"
      class="edit-policy-form"
      form-type="vertical">
      <BkFormItem
        :label="t('单据类型')"
        required>
        <BkInput
          disabled
          :model-value="data.ticket_type_display" />
      </BkFormItem>
      <BkFormItem
        :label="t('应用范围')"
        required>
        <template v-if="showBusinessPolicyReadOnly">
          <BkInput
            disabled
            :model-value="t('业务下全部集群')" />
        </template>
        <template v-else>
          <SelectClusters
            ref="targetRef"
            v-model="selectedClusterIds"
            :biz-id="selectClustersData.bizId"
            :db-type="selectClustersData.dbType" />
        </template>
      </BkFormItem>
      <BkFormItem
        :label="t('免审批')"
        required>
        <BkSwitcher
          v-model="formData.need_itsm"
          theme="primary" />
        <span class="form-tip ml-8">
          <I18nT
            v-if="!formData.need_itsm"
            keypath="开启免审批，单据提交后 {action}，直接进入下一阶段">
            <template #action>
              <strong>{{ t('跳过 DBA 审批') }}</strong>
            </template>
          </I18nT>
          <I18nT
            v-else
            keypath="关闭免审批，单据提交后 {action}，才可进入下一阶段">
            <template #action>
              <strong>{{ t('需经 DBA 审批') }}</strong>
            </template>
          </I18nT>
        </span>
      </BkFormItem>
      <BkAlert
        v-if="isChildPolicy && isSameAsParent"
        class="mb-16"
        theme="warning">
        {{ t('当前审批设置与父策略相同，该子策略不会产生实际效果') }}
      </BkAlert>
      <BkFormItem :label="t('备注')">
        <BkInput
          v-model="formData.remark"
          :autosize="{ minRows: 3, maxRows: 10 }"
          :maxlength="500"
          :resize="false"
          type="textarea" />
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
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { createTicketFlowConfig, saveTicketFlowConfig, updateTicketFlowConfig } from '@services/source/ticket';

  import { useBeforeClose } from '@hooks';

  import { DBTypes } from '@common/const';

  import { messageError, messageSuccess } from '@utils';

  import SelectClusters from './SelectClusters.vue';

  interface Props {
    data: TicketFlowDescribeModel;
    isEdit?: boolean;
    parentApprovalSetting?: boolean;
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    isEdit: false,
    parentApprovalSetting: undefined,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const formData = reactive({
    need_itsm: false,
    remark: '',
  });

  const selectedClusterIds = ref<number[]>([]);

  const isSubmitting = ref(false);

  const isChildPolicy = computed(() => props.data.isChildPolicy);

  // 是否显示业务策略的只读模式（编辑父策略时为 true：非子策略的编辑场景即父策略，应用范围固定为业务下全部集群）
  const showBusinessPolicyReadOnly = computed(() => props.isEdit && !isChildPolicy.value);

  const titleText = computed(() => {
    if (!props.isEdit) {
      return t('新建子策略');
    }
    if (isChildPolicy.value) {
      return t('编辑子策略');
    }
    return t('编辑父策略');
  });

  const isSameAsParent = computed(() => {
    if (props.parentApprovalSetting === undefined) {
      return false;
    }
    return formData.need_itsm === props.parentApprovalSetting;
  });

  const selectClustersData = computed(() => ({
    bizId: props.data.bk_biz_id || window.PROJECT_CONFIG.BIZ_ID,
    dbType: (props.data.group as DBTypes) || DBTypes.MYSQL,
  }));

  const { run: saveRun } = useRequest(saveTicketFlowConfig, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('success');
      isShow.value = false;
    },
  });

  const { run: createRun } = useRequest(createTicketFlowConfig, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('success');
      isShow.value = false;
    },
  });

  const { run: updateRun } = useRequest(updateTicketFlowConfig, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('success');
      isShow.value = false;
    },
  });

  watch(
    () => props.data,
    () => {
      formData.need_itsm = props.data.configs?.need_itsm ?? false;
      formData.remark = props.data.remark || '';
      selectedClusterIds.value = props.data.cluster_ids || [];
    },
    { immediate: true },
  );

  const handleSubmit = async () => {
    isSubmitting.value = true;

    try {
      // 子策略（新建或编辑）需要选择集群
      if (isChildPolicy.value) {
        if (selectedClusterIds.value.length === 0) {
          messageError(t('请至少选择一个集群'));
          isSubmitting.value = false;
          return;
        }
      }

      const params = {
        bk_biz_id: props.data.bk_biz_id || window.PROJECT_CONFIG.BIZ_ID,
        configs: {
          need_itsm: formData.need_itsm,
          need_manual_confirm: props.data.configs?.need_manual_confirm ?? false,
        },
        remark: formData.remark,
        ticket_types: [props.data.ticket_type],
      } as Parameters<typeof createTicketFlowConfig>[0];

      if (isChildPolicy.value) {
        params.cluster_ids = selectedClusterIds.value;
      }

      if (props.isEdit) {
        (params as any).config_ids = [props.data.id];
        if (isChildPolicy.value) {
          updateRun(params as Parameters<typeof updateTicketFlowConfig>[0]);
        } else {
          saveRun(params as Parameters<typeof saveTicketFlowConfig>[0]);
        }
      } else {
        createRun(params);
      }
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleCancel = () => {
    isShow.value = false;
  };

  const handleClosed = () => {
    formData.need_itsm = false;
    formData.remark = '';
    selectedClusterIds.value = [];
  };
</script>

<style lang="less" scoped>
  .edit-policy-form {
    padding: 24px;
  }

  .ticket-type-subtitle {
    padding-left: 8px;
    margin-left: 8px;
    font-size: 14px;
    color: #979ba5;
    border-left: 1px solid #dcdee5;
  }

  .form-tip {
    font-size: 12px;
  }

  .restore-dialog-content {
    p:first-child {
      font-weight: bold;
      margin-bottom: 8px;
    }
  }
</style>
