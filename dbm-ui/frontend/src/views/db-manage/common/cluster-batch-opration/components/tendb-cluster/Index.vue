<template>
  <BkDropdownItem v-db-console="'tendbCluster.clusterManage.batchAuthorize'">
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
      {{ t('授权') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'tendbCluster.clusterManage.batchAddTag'">
    <BkButton
      class="opration-button"
      :class="{ 'auth-button-disable': tagNoPermission }"
      :disabled="!tagEditable && !tagNoPermission"
      text
      @click="handleAddTagClick">
      {{ t('添加标签') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'tendbCluster.clusterManage.batchRemoveTag'">
    <BkButton
      class="opration-button"
      :class="{ 'auth-button-disable': tagNoPermission }"
      :disabled="!tagEditable && !tagNoPermission"
      text
      @click="handleRemoveTagClick">
      {{ t('移除标签') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-if="isClusterTypeAlarmSupported"
    v-db-console="'tendbCluster.clusterManage.configAlarmSubscription'">
    <BkButton
      class="opration-button"
      :class="{ 'auth-button-disable': subscriptionNoPermission }"
      :disabled="!subscriptionEditable && !subscriptionNoPermission"
      text
      @click="handleEditSubscriptionClick">
      {{ t('设置告警订阅') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-if="isClusterTypeAlarmSupported"
    v-db-console="'tendbCluster.clusterManage.deleteAlarmSubscription'">
    <BkButton
      class="opration-button"
      :class="{ 'auth-button-disable': subscriptionNoPermission }"
      :disabled="!subscriptionEditable && !subscriptionNoPermission"
      text
      @click="handleDeleteSubscriptionClick">
      {{ t('删除告警订阅') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !disableTooltip,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'tendbCluster.clusterManage.disable'"
    @click="handleDisableClick">
    <BkButton
      class="opration-button"
      :class="{ 'auth-button-disable': disableNoPermission }"
      :disabled="disableDisabled"
      text
      @click="handleDisableClick">
      {{ t('禁用') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !enableTooltip,
      content: t('所选集群均已启用'),
      placement: 'right',
    }"
    v-db-console="'tendbCluster.clusterManage.enable'"
    @click="handleEnableClick">
    <BkButton
      class="opration-button"
      :class="{ 'auth-button-disable': enableNoPermission }"
      :disabled="enableDisabled"
      text
      @click="handleEnableClick">
      {{ t('启用') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !deleteTooltip,
      content: t('所选集群均未禁用'),
      placement: 'right',
    }"
    v-db-console="'tendbCluster.clusterManage.delete'"
    @click="handleDeleteClick">
    <BkButton
      class="opration-button"
      :class="{ 'auth-button-disable': deleteNoPermission }"
      :disabled="deleteDisabled"
      text
      @click="handleDeleteClick">
      {{ t('删除') }}
    </BkButton>
  </BkDropdownItem>
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.TENDBCLUSTER"
    :cluster-types="[ClusterTypes.TENDBCLUSTER, 'tendbclusterSlave']"
    :selected="selected"
    @success="handleAuthorizeSuccess" />
  <ClusterBatchAddTag
    v-model:is-show="showClusterBatchAddTag"
    :get-editable="(item) => item.permission?.tendbcluster_edit !== false"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchRemoveTag
    v-model:is-show="showClusterBatchRemoveTag"
    :get-editable="(item) => item.permission?.tendbcluster_edit !== false"
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

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getApplyDataLink } from '@services/source/iam';

  import { useAlarmSubscribe } from '@hooks';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchAddTag from '@views/db-manage/common/cluster-batch-add-tag/Index.vue';
  import ClusterBatchDeleteSubscription from '@views/db-manage/common/cluster-batch-delete-subscription/Index.vue';
  import ClusterBatchEditSubscription from '@views/db-manage/common/cluster-batch-edit-subscription/Index.vue';
  import ClusterBatchRemoveTag from '@views/db-manage/common/cluster-batch-remove-tag/Index.vue';
  import { useOperateClusterBatch } from '@views/db-manage/common/hooks';
  import OperateClusterConfirmDialog from '@views/db-manage/common/OperateClusterConfirmDialog/Index.vue';

  import { permissionDialog } from '@utils';

  interface Props {
    selected: TendbClusterModel[];
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: ClusterTypes.TENDBCLUSTER,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const sideSliderShow = defineModel<boolean>('side-slider-show', {
    required: true,
  });

  const { t } = useI18n();
  const { handleConfirmDialog, handleDeleteCluster, handleDisableCluster, handleEnableCluster, isShow, operateDialog } =
    useOperateClusterBatch<TendbClusterModel>(ClusterTypes.TENDBCLUSTER, {
      deleteMismatch: (data) => data.isOnline || Boolean(data.operationTicketId),
      deletePermission: (data) => data.permission.tendbcluster_destroy !== false,
      disableMismatch: (data) => data.isOffline || Boolean(data.operationTicketId),
      disablePermission: (data) => data.permission.tendbcluster_enable_disable !== false,
      enableMismatch: (data) => data.isOnline || data.isStarting,
      enablePermission: (data) => data.permission.tendbcluster_enable_disable !== false,
      onSuccess: () => handleSuccess(),
    });

  const { isClusterTypeAlarmSupported } = useAlarmSubscribe([ClusterTypes.TENDBCLUSTER]);

  const clusterAuthorizeShow = ref(false);
  const showClusterBatchAddTag = ref(false);
  const showClusterBatchRemoveTag = ref(false);
  const showClusterBatchEditSubscription = ref(false);
  const showClusterBatchDeleteSubscription = ref(false);

  const batchAuthorizeDisabled = computed(() => props.selected.some((data) => data.isOffline));
  /** 禁用/启用鉴权 action-id（与单行一致） */
  const DISABLE_ACTION_ID = 'tendbcluster_enable_disable';
  /** 删除鉴权 action-id（与单行一致） */
  const DELETE_ACTION_ID = 'tendbcluster_destroy';
  /** 是否具备禁用/启用权限 */
  const hasDisablePermission = (data: TendbClusterModel) => data.permission.tendbcluster_enable_disable !== false;
  /** 是否具备删除权限 */
  const hasDeletePermission = (data: TendbClusterModel) => data.permission.tendbcluster_destroy !== false;
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

  /** 无权限时点击，复用单行无权限反馈（权限申请弹窗） */
  const handleDisableClick = async () => {
    if (disableNoPermission.value) {
      const applyData = await getApplyDataLink({
        action_ids: [DISABLE_ACTION_ID],
        resources: props.selected.map((data) => ({ id: data.id, type: data.db_type })),
      });
      permissionDialog(applyData);
      return;
    }
    handleDisableCluster(props.selected);
  };
  const handleEnableClick = async () => {
    if (enableNoPermission.value) {
      const applyData = await getApplyDataLink({
        action_ids: [DISABLE_ACTION_ID],
        resources: props.selected.map((data) => ({ id: data.id, type: data.db_type })),
      });
      permissionDialog(applyData);
      return;
    }
    handleEnableCluster(props.selected);
  };
  const handleDeleteClick = async () => {
    if (deleteNoPermission.value) {
      const applyData = await getApplyDataLink({
        action_ids: [DELETE_ACTION_ID],
        resources: props.selected.map((data) => ({ id: data.id, type: data.db_type })),
      });
      permissionDialog(applyData);
      return;
    }
    handleDeleteCluster(props.selected);
  };

  /** 添加/移除标签鉴权 action-id（与单行一致） */
  const TAG_ACTION_ID = 'tendbcluster_edit';
  /** 设置/删除告警订阅鉴权 action-id（与单行一致） */
  const SUBSCRIBE_ACTION_ID = 'tendbcluster_subscribe_monitor';
  /** 是否具备告警订阅权限 */
  const hasSubscribePermission = (data: TendbClusterModel) =>
    (data.permission as Record<string, boolean | undefined>)?.[SUBSCRIBE_ACTION_ID] !== false;
  /** 添加/移除标签：全部无权限时置灰可点击，点击弹权限申请 */
  const tagNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => data.permission.tendbcluster_edit === false),
  );
  /** 添加/移除标签：至少 1 个有权限则亮起 */
  const tagEditable = computed(() => props.selected.some((data) => data.permission.tendbcluster_edit !== false));
  /** 设置/删除告警订阅：全部无权限时置灰可点击，点击弹权限申请 */
  const subscriptionNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasSubscribePermission(data)),
  );
  /** 设置/删除告警订阅：至少 1 个有权限则亮起 */
  const subscriptionEditable = computed(() => props.selected.some((data) => hasSubscribePermission(data)));

  /** 无权限时点击，批量获取申请数据后打开权限申请弹窗 */
  const handleAddTagClick = async () => {
    if (tagNoPermission.value) {
      const applyData = await getApplyDataLink({
        action_ids: [TAG_ACTION_ID],
        resources: props.selected.map((data) => ({ id: data.id, type: data.db_type })),
      });
      permissionDialog(applyData);
      return;
    }
    showClusterBatchAddTag.value = true;
  };
  const handleRemoveTagClick = async () => {
    if (tagNoPermission.value) {
      const applyData = await getApplyDataLink({
        action_ids: [TAG_ACTION_ID],
        resources: props.selected.map((data) => ({ id: data.id, type: data.db_type })),
      });
      permissionDialog(applyData);
      return;
    }
    showClusterBatchRemoveTag.value = true;
  };
  const handleEditSubscriptionClick = async () => {
    if (subscriptionNoPermission.value) {
      const applyData = await getApplyDataLink({
        action_ids: [SUBSCRIBE_ACTION_ID],
        resources: props.selected.map((data) => ({ id: data.id, type: data.db_type })),
      });
      permissionDialog(applyData);
      return;
    }
    showClusterBatchEditSubscription.value = true;
  };
  const handleDeleteSubscriptionClick = async () => {
    if (subscriptionNoPermission.value) {
      const applyData = await getApplyDataLink({
        action_ids: [SUBSCRIBE_ACTION_ID],
        resources: props.selected.map((data) => ({ id: data.id, type: data.db_type })),
      });
      permissionDialog(applyData);
      return;
    }
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
