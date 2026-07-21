<template>
  <DbSideslider
    v-model:is-show="isShow"
    :before-close="handleBeforeClose"
    :cancel-handler="handleCancel"
    class="edit-policy-side"
    :confirm-handler="handleConfirm"
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
        :ticket-type="data.ticket_type" />
      <!-- 按标签 -->
      <DbFormItem
        v-else-if="!showBusinessPolicyReadOnly && formData.scope_type === 'tag'"
        :label="t('标签条件')"
        required>
        <TagScopeEditor
          ref="tagScopeRef"
          :cluster-tags="data.cluster_tags"
          :get-tag-id="getTagId"
          :key-value-map="keyValueMap" />
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

  import { useClusterTags } from '../hooks/use-cluster-tags';

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
  const handleBeforeClose = useBeforeClose();

  // 标签键值聚合（失效判定由后端 is_invalid 字段提供）
  const { getTagId, keyValueMap } = useClusterTags();

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

  watch(
    () => props.data,
    (data) => {
      formData.need_itsm = data.configs?.need_itsm ?? false;
      formData.remark = data.remark || '';
      // 编辑态按 data.scopeType 回填，新建态默认按集群
      formData.scope_type = props.isEdit ? data.scopeType : 'cluster';
      // 按集群仅存 id；非集群范围时清空
      formData.cluster_ids = data.scopeType === 'cluster' ? (data.cluster_ids || []).map((item) => item.id) : [];
      formData.cluster_tags = (data.cluster_tags || []).map((item) => item.id);
    },
    { immediate: true },
  );

  const handleConfirm = async () => {
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

    await saveRun(params);
    return true;
  };

  const handleCancel = async () => {
    isShow.value = false;
    Object.assign(formData, {
      cluster_ids: [],
      cluster_tags: [],
      need_itsm: false,
      remark: '',
      scope_type: 'cluster',
    });
    selectClustersRef.value?.clearValidate?.();
    tagScopeRef.value?.clearValidate?.();
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
