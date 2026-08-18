<template>
  <BkDropdownItem v-db-console="'mysql.haClusterList.batchSubscription'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchSubscriptionDisabled,
        content: t('仅可订阅状态为“已启用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchSubscriptionDisabled"
      text
      @click="showCreateSubscribeRuleSlider = true">
      {{ t('批量订阅') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.batchAuthorize'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchAuthorizeDisabled,
        content: t('仅可授权状态为“已启用”的集群'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchAuthorizeDisabled"
      text
      @click="clusterAuthorizeShow = true">
      {{ t('批量授权') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.batchAddTag'">
    <BkButton
      class="opration-button"
      :disabled="!isClusterTagEditable"
      text
      @click="() => (showClusterBatchAddTag = true)">
      {{ t('添加标签') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.batchRemoveTag'">
    <BkButton
      class="opration-button"
      :disabled="!isClusterTagEditable"
      text
      @click="() => (showClusterBatchRemoveTag = true)">
      {{ t('移除标签') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-if="isClusterTypeAlarmSupported"
    v-db-console="'mysql.haClusterList.configAlarmSubscription'">
    <BkButton
      class="opration-button"
      text
      @click="() => (showClusterBatchEditSubscription = true)">
      {{ t('设置告警订阅') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-if="isClusterTypeAlarmSupported"
    v-db-console="'mysql.haClusterList.deleteAlarmSubscription'">
    <BkButton
      class="opration-button"
      text
      @click="() => (showClusterBatchDeleteSubscription = true)">
      {{ t('删除告警订阅') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-db-console="'mysql.haClusterList.disable'"
    @click="handleDisableCluster(selected)">
    <BkButton
      class="opration-button"
      :disabled="disableDisabled"
      text
      @click="handleDisableCluster(selected)">
      {{ t('禁用') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.enable'">
    <BkButton
      class="opration-button"
      :disabled="enableDisabled"
      text
      @click="handleEnableCluster(selected)">
      {{ t('启用') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'mysql.haClusterList.delete'">
    <BkButton
      class="opration-button"
      :disabled="deleteDisabled"
      text
      @click="handleDeleteCluster(selected)">
      {{ t('删除') }}
    </BkButton>
  </BkDropdownItem>
  <CreateSubscribeRuleSlider
    v-model="showCreateSubscribeRuleSlider"
    :selected-clusters="selected"
    show-tab-panel
    @success="handleSubscribeSuccess" />
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.MYSQL"
    :cluster-types="[ClusterTypes.TENDBHA, 'tendbhaSlave']"
    :selected="selected"
    @success="handleAuthorizeSuccess" />
  <ClusterBatchAddTag
    v-model:is-show="showClusterBatchAddTag"
    :get-editable="(item) => item.permission?.mysql_edit !== false"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchRemoveTag
    v-model:is-show="showClusterBatchRemoveTag"
    :get-editable="(item) => item.permission?.mysql_edit !== false"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchEditSubscription
    v-model:is-show="showClusterBatchEditSubscription"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchDeleteSubscription
    v-model:is-show="showClusterBatchDeleteSubscription"
    :selected="selected"
    @success="handleSuccess" />
  <OperateClusterConfirmDialog
    v-model:is-show="isShow"
    v-bind="operateDialog"
    @confirm="handleConfirmDialog" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbHaModel from '@services/model/mysql/tendbha';

  import { useAlarmSubscribe } from '@hooks';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchAddTag from '@views/db-manage/common/cluster-batch-add-tag/Index.vue';
  import ClusterBatchDeleteSubscription from '@views/db-manage/common/cluster-batch-delete-subscription/Index.vue';
  import ClusterBatchEditSubscription from '@views/db-manage/common/cluster-batch-edit-subscription/Index.vue';
  import ClusterBatchRemoveTag from '@views/db-manage/common/cluster-batch-remove-tag/Index.vue';
  import { useOperateClusterBatch } from '@views/db-manage/common/hooks';
  import OperateClusterConfirmDialog from '@views/db-manage/common/OperateClusterConfirmDialog/Index.vue';
  import CreateSubscribeRuleSlider from '@views/db-manage/mysql/dumper/components/create-rule/Index.vue';

  interface Props {
    selected: TendbHaModel[];
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: ClusterTypes.TENDBHA,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const sideSliderShow = defineModel<boolean>('side-slider-show', {
    required: true,
  });

  const { t } = useI18n();
  const { handleConfirmDialog, handleDeleteCluster, handleDisableCluster, handleEnableCluster, isShow, operateDialog } =
    useOperateClusterBatch<TendbHaModel>(ClusterTypes.TENDBHA, {
      deleteMismatch: (data) => data.isOnline || Boolean(data.operationTicketId),
      disableMismatch: (data) => data.isOffline || Boolean(data.operationTicketId),
      enableMismatch: (data) => data.isOnline || data.isStarting,
      hasPermission: (data) =>
        data.permission.mysql_enable_disable !== false || data.permission.mysql_destroy !== false,
      onSuccess: () => handleSuccess(),
    });

  const { isClusterTypeAlarmSupported } = useAlarmSubscribe([ClusterTypes.TENDBHA]);

  const showCreateSubscribeRuleSlider = ref(false);
  const clusterAuthorizeShow = ref(false);
  const showClusterBatchAddTag = ref(false);
  const showClusterBatchRemoveTag = ref(false);
  const showClusterBatchEditSubscription = ref(false);
  const showClusterBatchDeleteSubscription = ref(false);

  const batchSubscriptionDisabled = computed(() => props.selected.some((data) => data.isOffline));
  const batchAuthorizeDisabled = computed(() => props.selected.some((data) => data.isOffline));
  const isClusterTagEditable = computed(() => props.selected.some((data) => data.permission.mysql_edit !== false));
  /** 是否具备禁用/启用/删除权限 */
  const hasOperatePermission = (data: TendbHaModel) =>
    data.permission.mysql_enable_disable !== false || data.permission.mysql_destroy !== false;
  /** 禁用/启用/删除：至少 1 个集群有权限且不计入跳过 b（状态不符）才亮起，全部无权限或全部计入跳过 b 则置灰。
   *  跳过 b 条件与摘要一致：禁用=已禁用或有操作单；启用=已启用或启动中；删除=未禁用或有操作单 */
  const disableDisabled = computed(
    () => !props.selected.some((data) => hasOperatePermission(data) && !data.isOffline && !data.operationTicketId),
  );
  const enableDisabled = computed(
    () => !props.selected.some((data) => hasOperatePermission(data) && !data.isOnline && !data.isStarting),
  );
  const deleteDisabled = computed(
    () => !props.selected.some((data) => hasOperatePermission(data) && !data.isOnline && !data.operationTicketId),
  );

  watch([showCreateSubscribeRuleSlider, clusterAuthorizeShow], () => {
    sideSliderShow.value = showCreateSubscribeRuleSlider.value || clusterAuthorizeShow.value;
  });

  const handleSuccess = () => {
    emits('success');
  };

  const handleSubscribeSuccess = () => {
    showCreateSubscribeRuleSlider.value = false;
    handleSuccess();
  };

  const handleAuthorizeSuccess = () => {
    clusterAuthorizeShow.value = false;
    handleSuccess();
  };
</script>
