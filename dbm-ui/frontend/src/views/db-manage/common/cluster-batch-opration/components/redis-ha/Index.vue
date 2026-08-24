<template>
  <BkDropdownItem v-db-console="'redis.haClusterManage.extractKey'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchOperationDisabled,
        content: t('仅已启用集群可以提取 Key'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchOperationDisabled"
      text
      @click="handleToToolbox(TicketTypes.REDIS_KEYS_EXTRACT, selected)">
      {{ t('提取Key') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'redis.haClusterManage.deleteKey'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchOperationDisabled,
        content: t('仅已启用集群可以删除 Key'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchOperationDisabled"
      text
      @click="handleToToolbox(TicketTypes.REDIS_KEYS_DELETE, selected)">
      {{ t('删除Key') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'redis.haClusterManage.backup'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchOperationDisabled,
        content: t('仅已启用集群可以备份'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchOperationDisabled"
      text
      @click="handleToToolbox(TicketTypes.REDIS_BACKUP, selected)">
      {{ t('备份') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'redis.haClusterManage.dbClear'">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchOperationDisabled,
        content: t('仅已启用集群可以清档'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchOperationDisabled"
      text
      @click="handleToToolbox(TicketTypes.REDIS_PURGE, selected)">
      {{ t('清档') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'redis.haClusterManage.batchAddTag'">
    <BkButton
      class="opration-button"
      :class="{ 'auth-button-disable': tagNoPermission }"
      :disabled="!tagEditable && !tagNoPermission"
      text
      @click="handleAddTagClick">
      {{ t('添加标签') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'redis.haClusterManage.batchRemoveTag'">
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
    v-db-console="'redis.haClusterManage.configAlarmSubscription'">
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
    v-db-console="'redis.haClusterManage.deleteAlarmSubscription'">
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
    v-db-console="'redis.haClusterManage.disable'"
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
    v-db-console="'redis.haClusterManage.enable'"
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
    v-db-console="'redis.haClusterManage.delete'"
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
  <ClusterBatchAddTag
    v-model:is-show="showClusterBatchAddTag"
    :get-editable="(item) => item.permission?.redis_edit !== false"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchRemoveTag
    v-model:is-show="showClusterBatchRemoveTag"
    :get-editable="(item) => item.permission?.redis_edit !== false"
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

  import RedisModel from '@services/model/redis/redis';
  import { getApplyDataLink } from '@services/source/iam';

  import { useAlarmSubscribe } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterBatchAddTag from '@views/db-manage/common/cluster-batch-add-tag/Index.vue';
  import ClusterBatchDeleteSubscription from '@views/db-manage/common/cluster-batch-delete-subscription/Index.vue';
  import ClusterBatchEditSubscription from '@views/db-manage/common/cluster-batch-edit-subscription/Index.vue';
  import ClusterBatchRemoveTag from '@views/db-manage/common/cluster-batch-remove-tag/Index.vue';
  import { useOperateClusterBatch, useRedisClusterListToToolbox } from '@views/db-manage/common/hooks';
  import OperateClusterConfirmDialog from '@views/db-manage/common/OperateClusterConfirmDialog/Index.vue';

  import { permissionDialog } from '@utils';

  interface Props {
    selected: RedisModel[];
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: ClusterTypes.REDIS_INSTANCE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { handleToToolbox } = useRedisClusterListToToolbox();
  const { isClusterTypeAlarmSupported } = useAlarmSubscribe([ClusterTypes.REDIS_INSTANCE]);

  const { handleConfirmDialog, handleDeleteCluster, handleDisableCluster, handleEnableCluster, isShow, operateDialog } =
    useOperateClusterBatch<RedisModel>(ClusterTypes.REDIS_INSTANCE, {
      deleteMismatch: (data) => data.isOnline || Boolean(data.operationTicketId),
      deletePermission: (data) => data.permission.redis_destroy !== false,
      disableMismatch: (data) => data.isOffline || Boolean(data.operationTicketId),
      disablePermission: (data) => data.permission.redis_open_close !== false,
      enableMismatch: (data) => data.isOnline || data.isStarting,
      enablePermission: (data) => data.permission.redis_open_close !== false,
      onSuccess: () => handleSuccess(),
    });

  const showClusterBatchAddTag = ref(false);
  const showClusterBatchRemoveTag = ref(false);
  const showClusterBatchEditSubscription = ref(false);
  const showClusterBatchDeleteSubscription = ref(false);

  const batchOperationDisabled = computed(() =>
    props.selected.some((data) => {
      if (!data.isOnline) {
        return true;
      }

      if (data.operations?.length > 0) {
        const operationData = data.operations[0];
        return ([TicketTypes.REDIS_INSTANCE_DESTROY, TicketTypes.REDIS_INSTANCE_CLOSE] as string[]).includes(
          operationData.ticket_type,
        );
      }

      return false;
    }),
  );

  /** 禁用/启用鉴权 action-id（与单行一致） */
  const DISABLE_ACTION_ID = 'redis_open_close';
  /** 删除鉴权 action-id（与单行一致） */
  const DELETE_ACTION_ID = 'redis_destroy';
  /** 是否具备禁用/启用权限 */
  const hasDisablePermission = (data: RedisModel) => data.permission.redis_open_close !== false;
  /** 是否具备删除权限 */
  const hasDeletePermission = (data: RedisModel) => data.permission.redis_destroy !== false;
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
  const TAG_ACTION_ID = 'redis_edit';
  /** 设置/删除告警订阅鉴权 action-id（与单行一致） */
  const SUBSCRIBE_ACTION_ID = 'redis_subscribe_monitor';
  /** 是否具备告警订阅权限 */
  const hasSubscribePermission = (data: RedisModel) =>
    (data.permission as Record<string, boolean | undefined>)?.[SUBSCRIBE_ACTION_ID] !== false;
  /** 添加/移除标签：全部无权限时置灰可点击，点击弹权限申请 */
  const tagNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => data.permission.redis_edit === false),
  );
  /** 添加/移除标签：至少 1 个有权限则亮起 */
  const tagEditable = computed(() => props.selected.some((data) => data.permission.redis_edit !== false));
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

  const handleSuccess = () => {
    emits('success');
  };
</script>
