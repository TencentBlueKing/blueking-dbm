<template>
  <DbSideslider
    v-model:is-show="isShow"
    :before-close="handleBeforeClose"
    class="edit-policy-side"
    quick-close
    render-directive="if"
    :width="960">
    <template #header>
      <span>{{ titleText }}</span>
      <span class="ticket-type-subtitle">{{ data.ticket_type_display }}</span>
    </template>
    <DbForm
      class="edit-policy-form"
      form-type="vertical">
      <DbFormItem
        :label="t('单据类型')"
        required>
        <BkInput
          disabled
          :model-value="data.ticket_type_display" />
      </DbFormItem>
      <DbFormItem
        :label="t('生效范围')"
        required>
        <template v-if="showBusinessPolicyReadOnly">
          <BkInput
            disabled
            :model-value="t('业务下全部集群')" />
        </template>
        <template v-else>
          <!-- 范围类型：按集群 / 按标签（仅子策略显示） -->
          <BkRadioGroup
            v-model="formData.scope_type"
            type="card">
            <BkRadioButton label="cluster">{{ t('按集群') }}</BkRadioButton>
            <BkRadioButton label="tag">{{ t('按标签') }}</BkRadioButton>
          </BkRadioGroup>
        </template>
      </DbFormItem>
      <!-- 按集群 -->
      <SelectClusters
        v-if="!showBusinessPolicyReadOnly && formData.scope_type === 'cluster'"
        ref="selectClustersRef"
        v-model="formData.cluster_ids"
        :biz-id="selectClustersData.bizId"
        :config-id="isEdit ? data.id : undefined"
        :db-type="selectClustersData.dbType"
        :ticket-type="data.ticket_type"
        @change="dirty = true" />
      <!-- 按标签 -->
      <DbFormItem
        v-else-if="!showBusinessPolicyReadOnly && formData.scope_type === 'tag'"
        :label="t('标签条件')"
        required>
        <TagScopeEditor
          ref="tagScopeRef"
          :biz-id="data.bk_biz_id"
          :cluster-tags="data.cluster_tags"
          :config-id="isEdit ? data.id : undefined"
          :ticket-type="data.ticket_type"
          @change="dirty = true" />
      </DbFormItem>
      <DbFormItem
        :label="t('是否审批')"
        required>
        <BkSwitcher
          v-model="formData.need_itsm"
          theme="primary" />
        <span class="form-tip ml-8">
          <I18nT
            v-if="!formData.need_itsm"
            keypath="免审批，单据提交后 {action}，直接进入下一阶段">
            <template #action>
              <strong>{{ t('跳过 DBA 审批') }}</strong>
            </template>
          </I18nT>
          <I18nT
            v-else
            keypath="需审批，单据提交后 {action}，才可进入下一阶段">
            <template #action>
              <strong>{{ t('需经 DBA 审批') }}</strong>
            </template>
          </I18nT>
        </span>
      </DbFormItem>
      <BkAlert
        v-if="isChildPolicy && isSameAsParent"
        class="mb-24"
        theme="warning">
        {{ t('当前审批设置与父策略相同，该子策略不会产生实际效果') }}
      </BkAlert>
      <DbFormItem
        :label="t('备注')"
        property="remark">
        <BkInput
          v-model="formData.remark"
          :autosize="{ minRows: 3, maxRows: 10 }"
          :maxlength="500"
          :resize="false"
          type="textarea" />
      </DbFormItem>
    </DbForm>
    <template #footer>
      <BkButton
        v-bk-tooltips="{
          content: t('当前无变更，请先修改内容'),
          disabled: dirty,
        }"
        class="w-88 mr-8"
        :disabled="!dirty"
        :loading="isSubmitting"
        theme="primary"
        @click="handleConfirm">
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

  import TicketFlowDescribeModel, { type ScopeType } from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { type ClusterIdItem, type ClusterTagItem, saveTicketFlowConfig } from '@services/source/ticket';

  import { useBeforeClose } from '@hooks';

  import { DBTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  import SelectClusters from './SelectClusters.vue';
  import TagScopeEditor from './TagScopeEditor.vue';

  interface Props {
    data: TicketFlowDescribeModel;
    isEdit?: boolean;
    parentApprovalSetting?: boolean;
  }

  type Emits = (e: 'success') => void;

  interface FormData {
    cluster_ids: number[];
    cluster_tags: number[];
    need_itsm: boolean;
    remark: string;
    scope_type: ScopeType;
  }

  const props = withDefaults(defineProps<Props>(), {
    isEdit: false,
    parentApprovalSetting: undefined,
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const beforeClose = useBeforeClose();
  const handleBeforeClose = () => beforeClose(dirty.value);

  const isSubmitting = ref(false);
  const dirty = ref(false);
  let initDone = false;

  const selectClustersRef = ref<InstanceType<typeof SelectClusters>>();
  const tagScopeRef = ref<InstanceType<typeof TagScopeEditor>>();

  const formData = reactive<FormData>({
    cluster_ids: [],
    cluster_tags: [],
    need_itsm: false,
    remark: '',
    scope_type: 'cluster',
  });

  const isChildPolicy = computed(() => props.data.isChildPolicy);

  // 编辑父策略为只读：生效范围固定为业务下全部集群
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

  // 打开时回填数据并复位 dirty；关闭时清除校验状态
  watch(isShow, (val) => {
    if (val) {
      dirty.value = false;
      initDone = false;
      formData.need_itsm = props.data.configs?.need_itsm ?? false;
      formData.remark = props.data.remark || '';
      formData.scope_type = props.isEdit ? props.data.scopeType : 'cluster';
      formData.cluster_ids =
        props.data.scopeType === 'cluster' ? (props.data.cluster_ids || []).map((item) => item.id) : [];
      formData.cluster_tags = (props.data.cluster_tags || []).map((item) => item.id);
      // 双 nextTick 确保 SelectClusters/TagScopeEditor 内部异步回显完成后再开始追踪
      nextTick(() => {
        nextTick(() => {
          initDone = true;
        });
      });
    }
    if (!val) {
      selectClustersRef.value?.clearValidate?.();
      tagScopeRef.value?.clearValidate?.();
    }
  });

  // dirty 一经置位不再复位
  watch(
    formData,
    () => {
      if (initDone) {
        dirty.value = true;
      }
    },
    { deep: true },
  );

  const handleConfirm = async () => {
    if (!dirty.value) return;

    const isClusterScope = isChildPolicy.value && formData.scope_type === 'cluster';
    const isTagScope = isChildPolicy.value && formData.scope_type === 'tag';
    // getValue 内部触发校验并报红，失败 reject 中断提交
    const clusterIds: ClusterIdItem[] = isClusterScope ? await selectClustersRef.value!.getValue() : [];
    const clusterTags: ClusterTagItem[] = isTagScope ? (await tagScopeRef.value!.getValue()).clusterTags : [];

    const params = {
      bk_biz_id: props.data.bk_biz_id || window.PROJECT_CONFIG.BIZ_ID,
      cluster_ids: clusterIds,
      cluster_tags: clusterTags,
      configs: {
        need_itsm: formData.need_itsm,
      },
      remark: formData.remark,
      ticket_types: [props.data.ticket_type],
      ...(props.isEdit ? { config_ids: [props.data.id] } : {}),
    } as Parameters<typeof saveTicketFlowConfig>[0];

    isSubmitting.value = true;
    try {
      await saveRun(params);
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleCancel = async () => {
    isShow.value = false;
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
</style>
