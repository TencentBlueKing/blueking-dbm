<template>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !batchAuthorizeTooltip || authorizeNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'sqlserver.haClusterList.batchAuthorize'">
    <BatchOperationButton
      :action-id="AUTHORIZE_ACTION_ID"
      :disabled="batchAuthorizeDisabled"
      :no-permission="authorizeNoPermission"
      :resources="resources"
      @click="clusterAuthorizeShow = true">
      {{ t('授权') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'sqlserver.haClusterList.batchAddTag'">
    <BatchOperationButton
      :action-id="TAG_ACTION_ID"
      :no-permission="tagNoPermission"
      :resources="resources"
      @click="handleAddTagClick">
      {{ t('添加标签') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'sqlserver.haClusterList.batchRemoveTag'">
    <BatchOperationButton
      :action-id="TAG_ACTION_ID"
      :no-permission="tagNoPermission"
      :resources="resources"
      @click="handleRemoveTagClick">
      {{ t('移除标签') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-if="isClusterTypeAlarmSupported"
    v-bk-tooltips="{
      disabled: !subscriptionTooltip || subscriptionNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'sqlserver.haClusterList.configAlarmSubscription'">
    <BatchOperationButton
      :action-id="SUBSCRIBE_ACTION_ID"
      :disabled="subscriptionDisabled"
      :no-permission="subscriptionNoPermission"
      :resources="resources"
      @click="handleEditSubscriptionClick">
      {{ t('设置告警订阅') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-if="isClusterTypeAlarmSupported"
    v-bk-tooltips="{
      disabled: !subscriptionTooltip || subscriptionNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'sqlserver.haClusterList.deleteAlarmSubscription'">
    <BatchOperationButton
      :action-id="SUBSCRIBE_ACTION_ID"
      :disabled="subscriptionDisabled"
      :no-permission="subscriptionNoPermission"
      :resources="resources"
      @click="handleDeleteSubscriptionClick">
      {{ t('删除告警订阅') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !disableTooltip || disableNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'sqlserver.haClusterList.disable'">
    <BatchOperationButton
      :action-id="DISABLE_ACTION_ID"
      :disabled="disableDisabled"
      :no-permission="disableNoPermission"
      :resources="resources"
      @click="handleDisableClick">
      {{ t('禁用') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !enableTooltip || enableNoPermission,
      content: t('所选集群均已启用'),
      placement: 'right',
    }"
    v-db-console="'sqlserver.haClusterList.enable'">
    <BatchOperationButton
      :action-id="DISABLE_ACTION_ID"
      :disabled="enableDisabled"
      :no-permission="enableNoPermission"
      :resources="resources"
      @click="handleEnableClick">
      {{ t('启用') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !deleteTooltip || deleteNoPermission,
      content: t('所选集群均未禁用'),
      placement: 'right',
    }"
    v-db-console="'sqlserver.haClusterList.delete'">
    <BatchOperationButton
      :action-id="DELETE_ACTION_ID"
      :disabled="deleteDisabled"
      :no-permission="deleteNoPermission"
      :resources="resources"
      @click="handleDeleteClick">
      {{ t('删除') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.SQLSERVER"
    :cluster-types="[ClusterTypes.SQLSERVER_HA]"
    :selected="selected"
    @success="handleAuthorizeSuccess" />
  <ClusterBatchAddTag
    v-model:is-show="showClusterBatchAddTag"
    :get-editable="(item) => item.permission?.sqlserver_edit !== false"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchRemoveTag
    v-model:is-show="showClusterBatchRemoveTag"
    :get-editable="(item) => item.permission?.sqlserver_edit !== false"
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

  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';

  import { useAlarmSubscribe } from '@hooks';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchAddTag from '@views/db-manage/common/cluster-batch-add-tag/Index.vue';
  import ClusterBatchDeleteSubscription from '@views/db-manage/common/cluster-batch-delete-subscription/Index.vue';
  import ClusterBatchEditSubscription from '@views/db-manage/common/cluster-batch-edit-subscription/Index.vue';
  import ClusterBatchRemoveTag from '@views/db-manage/common/cluster-batch-remove-tag/Index.vue';
  import { useOperateClusterBatch } from '@views/db-manage/common/hooks';
  import OperateClusterConfirmDialog from '@views/db-manage/common/OperateClusterConfirmDialog/Index.vue';

  import BatchOperationButton from '../BatchOperationButton.vue';

  interface Props {
    selected: SqlserverHaModel[];
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: ClusterTypes.SQLSERVER_HA,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const sideSliderShow = defineModel<boolean>('side-slider-show', {
    required: true,
  });

  const { t } = useI18n();
  const { handleConfirmDialog, handleDeleteCluster, handleDisableCluster, handleEnableCluster, isShow, operateDialog } =
    useOperateClusterBatch<SqlserverHaModel>(ClusterTypes.SQLSERVER, {
      deleteMismatch: (data) => data.isOnline || Boolean(data.operationTicketId),
      deletePermission: (data) => data.permission.sqlserver_destroy !== false,
      disableMismatch: (data) => data.isOffline || Boolean(data.operationTicketId),
      disablePermission: (data) => data.permission.sqlserver_enable_disable !== false,
      enableMismatch: (data) => data.isOnline || data.isStarting,
      enablePermission: (data) => data.permission.sqlserver_enable_disable !== false,
      onSuccess: () => handleSuccess(),
    });

  const { isClusterTypeAlarmSupported } = useAlarmSubscribe([ClusterTypes.SQLSERVER_HA]);

  const clusterAuthorizeShow = ref(false);
  const showClusterBatchAddTag = ref(false);
  const showClusterBatchRemoveTag = ref(false);
  const showClusterBatchEditSubscription = ref(false);
  const showClusterBatchDeleteSubscription = ref(false);

  /** 批量授权鉴权 action-id（与单行/详情一致） */
  const AUTHORIZE_ACTION_ID = 'sqlserver_authorize';
  /** 批量授权：全部无权限时置灰可点击，点击弹权限申请 */
  const authorizeNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => data.permission.sqlserver_authorize === false),
  );
  /** 批量授权：全部已禁用（状态不符）时置灰并 hover tooltip */
  const batchAuthorizeDisabled = computed(
    () =>
      !authorizeNoPermission.value &&
      props.selected.length > 0 &&
      props.selected.every((data) => data.permission.sqlserver_authorize !== false && data.isOffline),
  );
  const batchAuthorizeTooltip = computed(() => batchAuthorizeDisabled.value);
  /** 禁用/启用鉴权 action-id（与单行一致） */
  const DISABLE_ACTION_ID = 'sqlserver_enable_disable';
  /** 删除鉴权 action-id（与单行一致） */
  const DELETE_ACTION_ID = 'sqlserver_destroy';
  /** 是否具备禁用/启用权限 */
  const hasDisablePermission = (data: SqlserverHaModel) => data.permission.sqlserver_enable_disable !== false;
  /** 是否具备删除权限 */
  const hasDeletePermission = (data: SqlserverHaModel) => data.permission.sqlserver_destroy !== false;
  /**
   * 禁用/启用/删除三态：
   * - 全部无权限：置灰（auth-button-disable 样式）可点击，点击弹权限申请
   * - 全部状态不符（跳过 b）：置灰不可点，hover tooltip
   * - 至少 1 个有权限且状态可做：亮起，点击打开确认弹窗
   */
  const disableNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasDisablePermission(data)),
  );
  const enableNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasDisablePermission(data)),
  );
  const deleteNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasDeletePermission(data)),
  );
  const disableDisabled = computed(
    () =>
      !disableNoPermission.value &&
      !props.selected.some((data) => hasDisablePermission(data) && !data.isOffline && !data.operationTicketId),
  );
  const enableDisabled = computed(
    () =>
      !enableNoPermission.value &&
      !props.selected.some((data) => hasDisablePermission(data) && !data.isOnline && !data.isStarting),
  );
  const deleteDisabled = computed(
    () =>
      !deleteNoPermission.value &&
      !props.selected.some((data) => hasDeletePermission(data) && !data.isOnline && !data.operationTicketId),
  );
  /** 禁用/启用/删除：全部选中集群均状态不符（跳过 b）时置灰并 hover 出 tooltip */
  const disableTooltip = computed(
    () =>
      props.selected.length > 0 && props.selected.every((data) => data.isOffline || Boolean(data.operationTicketId)),
  );
  const enableTooltip = computed(
    () => props.selected.length > 0 && props.selected.every((data) => data.isOnline || data.isStarting),
  );
  const deleteTooltip = computed(
    () => props.selected.length > 0 && props.selected.every((data) => data.isOnline || Boolean(data.operationTicketId)),
  );

  /** 添加/移除标签鉴权 action-id（与单行一致） */
  const TAG_ACTION_ID = 'sqlserver_edit';
  /** 设置/删除告警订阅鉴权 action-id（与单行一致） */
  const SUBSCRIBE_ACTION_ID = 'sqlserver_subscribe_monitor';
  /** 是否具备告警订阅权限 */
  const hasSubscribePermission = (data: SqlserverHaModel) =>
    (data.permission as Record<string, boolean | undefined>)?.[SUBSCRIBE_ACTION_ID] !== false;
  /** 添加/移除标签：全部无权限时置灰可点击，点击弹权限申请 */
  const tagNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => data.permission.sqlserver_edit === false),
  );
  /** 设置/删除告警订阅：全部无权限时置灰可点击，点击弹权限申请 */
  const subscriptionNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasSubscribePermission(data)),
  );
  /** 设置/删除告警订阅：全部有权限且全部已禁用时置灰并 hover tooltip */
  const subscriptionDisabled = computed(
    () =>
      !subscriptionNoPermission.value &&
      !props.selected.some((data) => hasSubscribePermission(data) && !data.isOffline),
  );
  const subscriptionTooltip = computed(
    () => props.selected.length > 0 && props.selected.every((data) => data.isOffline),
  );
  /** 批量操作权限申请的资源列表 */
  const resources = computed(() => props.selected.map((data) => ({ id: data.id, type: data.db_type })));
  /** 禁用 */
  const handleDisableClick = () => {
    handleDisableCluster(props.selected);
  };
  /** 启用 */
  const handleEnableClick = () => {
    handleEnableCluster(props.selected);
  };
  /** 删除 */
  const handleDeleteClick = () => {
    handleDeleteCluster(props.selected);
  };

  /** 添加标签 */
  const handleAddTagClick = () => {
    showClusterBatchAddTag.value = true;
  };
  /** 移除标签 */
  const handleRemoveTagClick = () => {
    showClusterBatchRemoveTag.value = true;
  };
  /** 设置告警订阅 */
  const handleEditSubscriptionClick = () => {
    showClusterBatchEditSubscription.value = true;
  };
  /** 删除告警订阅 */
  const handleDeleteSubscriptionClick = () => {
    showClusterBatchDeleteSubscription.value = true;
  };

  watch(clusterAuthorizeShow, () => {
    sideSliderShow.value = clusterAuthorizeShow.value;
  });

  const handleSuccess = () => {
    emits('success');
  };

  const handleAuthorizeSuccess = () => {
    clusterAuthorizeShow.value = false;
    handleSuccess();
  };
</script>
