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
            v-model="scopeType"
            type="card">
            <BkRadioButton label="cluster">{{ t('按集群') }}</BkRadioButton>
            <BkRadioButton label="tag">{{ t('按标签') }}</BkRadioButton>
          </BkRadioGroup>
        </template>
      </BkFormItem>
      <!-- 按集群 -->
      <SelectClusters
        v-if="!showBusinessPolicyReadOnly && scopeType === 'cluster'"
        ref="targetRef"
        v-model="selectedClusters"
        :biz-id="selectClustersData.bizId"
        :db-type="selectClustersData.dbType" />
      <!-- 按标签 -->
      <TagScopeEditor
        v-else-if="!showBusinessPolicyReadOnly && scopeType === 'tag'"
        ref="tagScopeRef"
        :cluster-tags="data.cluster_tags"
        :get-tag-id="getTagId"
        :key-value-map="keyValueMap" />
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
        class="mb-24"
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

  import TicketFlowDescribeModel, { type ScopeType } from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { type ClusterIdItem, type ClusterTagItem, saveTicketFlowConfig } from '@services/source/ticket';

  import { useBeforeClose } from '@hooks';

  import { DBTypes } from '@common/const';

  import { messageError, messageSuccess } from '@utils';

  import { useClusterTags } from '../hooks/use-cluster-tags';

  import SelectClusters, { type SelectedCluster } from './SelectClusters.vue';
  import TagScopeEditor from './TagScopeEditor.vue';

  interface Props {
    data: TicketFlowDescribeModel;
    /** 已有子策略的集群 id 集合（用于不重复校验） */
    existingClusterIds?: number[];
    isEdit?: boolean;
    parentApprovalSetting?: boolean;
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    existingClusterIds: () => [],
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

  const formData = reactive({
    need_itsm: false,
    remark: '',
  });

  const selectedClusters = ref<SelectedCluster[]>([]);
  const scopeType = ref<ScopeType>('cluster');

  const targetRef = ref<InstanceType<typeof SelectClusters>>();
  const tagScopeRef = ref<InstanceType<typeof TagScopeEditor>>();

  const isSubmitting = ref(false);

  const isChildPolicy = computed(() => props.data.isChildPolicy);

  // 编辑父策略时为只读模式（生效范围固定为业务下全部集群）
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
    () => {
      formData.need_itsm = props.data.configs?.need_itsm ?? false;
      formData.remark = props.data.remark || '';
      // 编辑态按 data.scopeType 回填，新建态默认按集群
      scopeType.value = props.isEdit ? props.data.scopeType : 'cluster';
      // 按集群回填：cluster_ids 为对象数组 [{id, immute_domain}]
      selectedClusters.value =
        props.data.scopeType === 'cluster'
          ? (props.data.cluster_ids || []).map((item) => ({
              id: item.id,
              immute_domain: item.immute_domain || '',
            }))
          : [];
    },
    { immediate: true },
  );

  const handleSubmit = async () => {
    isSubmitting.value = true;

    try {
      let clusterIds: ClusterIdItem[] = [];
      let clusterTags: ClusterTagItem[] = [];

      // 子策略需校验生效范围
      if (isChildPolicy.value) {
        if (scopeType.value === 'cluster') {
          // 按集群：校验至少一个集群
          const clusters = await targetRef.value?.getValue();
          if (!clusters || clusters.length === 0) {
            messageError(t('请至少选择一个集群'));
            isSubmitting.value = false;
            return;
          }
          // 按集群不重复校验：同一单据类型下，一集群仅属一条按集群子策略
          const existingSet = new Set(props.existingClusterIds);
          // 编辑态排除自身已选集群（cluster_ids 为对象数组，提取 id）
          const selfIds = new Set((props.data.cluster_ids || []).map((item) => item.id));
          const duplicate = clusters.find((c) => existingSet.has(c.id) && !selfIds.has(c.id));
          if (duplicate) {
            messageError(t('集群 x 已在另一条按集群子策略中，不可重复', { x: duplicate.immute_domain }));
            isSubmitting.value = false;
            return;
          }
          clusterIds = clusters.map((c) => ({ id: c.id, immute_domain: c.immute_domain }));
        } else {
          // 按标签：校验标签条件
          const tagResult = await tagScopeRef.value?.getValue();
          if (!tagResult) {
            messageError(t('请选择标签键与匹配条件'));
            isSubmitting.value = false;
            return;
          }
          clusterTags = tagResult.clusterTags;
        }
      }

      const params = {
        bk_biz_id: props.data.bk_biz_id || window.PROJECT_CONFIG.BIZ_ID,
        cluster_ids: clusterIds,
        cluster_tags: clusterTags,
        configs: {
          need_itsm: formData.need_itsm,
        },
        remark: formData.remark,
        ticket_types: [props.data.ticket_type],
      } as Parameters<typeof saveTicketFlowConfig>[0];

      if (props.isEdit) {
        params.config_ids = [props.data.id];
      }

      saveRun(params);
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
    selectedClusters.value = [];
    scopeType.value = 'cluster';
    tagScopeRef.value?.reset();
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
