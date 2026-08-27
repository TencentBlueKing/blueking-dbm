<template>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !extractTooltip || extractNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'redis.clusterManage.extractKey'">
    <BatchOperationButton
      :action-id="EXTRACT_ACTION_ID"
      :disabled="extractDisabled"
      :no-permission="extractNoPermission"
      :resources="resources"
      @click="handleExtractClick">
      {{ t('提取Key') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !deleteKeyTooltip || deleteKeyNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'redis.clusterManage.deleteKey'">
    <BatchOperationButton
      :action-id="DELETE_KEY_ACTION_ID"
      :disabled="deleteKeyDisabled"
      :no-permission="deleteKeyNoPermission"
      :resources="resources"
      @click="handleDeleteKeyClick">
      {{ t('删除Key') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !backupTooltip || backupNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'redis.clusterManage.backup'">
    <BatchOperationButton
      :action-id="BACKUP_ACTION_ID"
      :disabled="backupDisabled"
      :no-permission="backupNoPermission"
      :resources="resources"
      @click="handleBackupClick">
      {{ t('备份') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !purgeTooltip || purgeNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'redis.clusterManage.dbClear'">
    <BatchOperationButton
      :action-id="PURGE_ACTION_ID"
      :disabled="purgeDisabled"
      :no-permission="purgeNoPermission"
      :resources="resources"
      @click="handlePurgeClick">
      {{ t('清档') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !tagTooltip || tagNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'redis.clusterManage.batchAddTag'">
    <BatchOperationButton
      :action-id="TAG_ACTION_ID"
      :disabled="tagDisabled"
      :no-permission="tagNoPermission"
      :resources="resources"
      @click="handleAddTagClick">
      {{ t('添加标签') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-bk-tooltips="{
      disabled: !tagTooltip || tagNoPermission,
      content: t('所选集群均已禁用'),
      placement: 'right',
    }"
    v-db-console="'redis.clusterManage.batchRemoveTag'">
    <BatchOperationButton
      :action-id="TAG_ACTION_ID"
      :disabled="tagDisabled"
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
    v-db-console="'redis.clusterManage.configAlarmSubscription'">
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
    v-db-console="'redis.clusterManage.deleteAlarmSubscription'">
    <BatchOperationButton
      :action-id="SUBSCRIBE_ACTION_ID"
      :disabled="subscriptionDisabled"
      :no-permission="subscriptionNoPermission"
      :resources="resources"
      @click="handleDeleteSubscriptionClick">
      {{ t('删除告警订阅') }}
    </BatchOperationButton>
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
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import { useAlarmSubscribe } from '@hooks';

  import { clusterRedisTypeList, ClusterTypes, TicketTypes } from '@common/const';

  import ClusterBatchAddTag from '@views/db-manage/common/cluster-batch-add-tag/Index.vue';
  import ClusterBatchDeleteSubscription from '@views/db-manage/common/cluster-batch-delete-subscription/Index.vue';
  import ClusterBatchEditSubscription from '@views/db-manage/common/cluster-batch-edit-subscription/Index.vue';
  import ClusterBatchRemoveTag from '@views/db-manage/common/cluster-batch-remove-tag/Index.vue';
  import { useRedisClusterListToToolbox } from '@views/db-manage/common/hooks';

  import BatchOperationButton from '../BatchOperationButton.vue';

  interface Props {
    selected: RedisModel[];
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: ClusterTypes.REDIS,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { handleToToolbox } = useRedisClusterListToToolbox();
  const { isClusterTypeAlarmSupported } = useAlarmSubscribe(clusterRedisTypeList);

  const showClusterBatchAddTag = ref(false);
  const showClusterBatchRemoveTag = ref(false);
  const showClusterBatchEditSubscription = ref(false);
  const showClusterBatchDeleteSubscription = ref(false);

  /** 跳转类鉴权 action-id（与单行一致） */
  const EXTRACT_ACTION_ID = 'redis_keys_extract';
  const DELETE_KEY_ACTION_ID = 'redis_keys_delete';
  const BACKUP_ACTION_ID = 'redis_backup';
  const PURGE_ACTION_ID = 'redis_purge';
  /** 是否具备跳转类操作权限 */
  const hasExtractPermission = (data: RedisModel) => data.permission.redis_keys_extract !== false;
  const hasDeleteKeyPermission = (data: RedisModel) => data.permission.redis_keys_delete !== false;
  const hasBackupPermission = (data: RedisModel) => data.permission.redis_backup !== false;
  const hasPurgePermission = (data: RedisModel) => data.permission.redis_purge !== false;
  /**
   * 跳转类三态（对应需求 §2.2）：
   * - 全部无权限（含同时已禁用）：置灰（auth-button-disable 样式）可点击，点击弹权限申请
   * - 全部有权限且全部已禁用：置灰不可点，hover tooltip「所选集群均已禁用」
   * - 其余（含部分无权限、部分已禁用）：亮起，点击跳转工具页预填全部勾选
   */
  const extractNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasExtractPermission(data)),
  );
  const deleteKeyNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasDeleteKeyPermission(data)),
  );
  const backupNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasBackupPermission(data)),
  );
  const purgeNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasPurgePermission(data)),
  );
  const extractDisabled = computed(
    () =>
      !extractNoPermission.value &&
      props.selected.length > 0 &&
      props.selected.every((data) => hasExtractPermission(data) && isClusterDisabled(data)),
  );
  const deleteKeyDisabled = computed(
    () =>
      !deleteKeyNoPermission.value &&
      props.selected.length > 0 &&
      props.selected.every((data) => hasDeleteKeyPermission(data) && isClusterDisabled(data)),
  );
  const backupDisabled = computed(
    () =>
      !backupNoPermission.value &&
      props.selected.length > 0 &&
      props.selected.every((data) => hasBackupPermission(data) && isClusterDisabled(data)),
  );
  const purgeDisabled = computed(
    () =>
      !purgeNoPermission.value &&
      props.selected.length > 0 &&
      props.selected.every((data) => hasPurgePermission(data) && isClusterDisabled(data)),
  );
  /** 全部有权限且全部已禁用（状态不符）时 hover 出 tooltip */
  const extractTooltip = computed(() => extractDisabled.value);
  const deleteKeyTooltip = computed(() => deleteKeyDisabled.value);
  const backupTooltip = computed(() => backupDisabled.value);
  const purgeTooltip = computed(() => purgeDisabled.value);
  /** 单个集群是否已禁用（状态不符：离线或存在销毁/关闭单据） */
  const isClusterDisabled = (data: RedisModel) => {
    if (!data.isOnline) {
      return true;
    }
    if (data.operations?.length > 0) {
      return ([TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_PROXY_CLOSE] as string[]).includes(
        data.operations[0].ticket_type,
      );
    }
    return false;
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
  /** 添加/移除标签：全部有权限且全部已禁用时置灰并 hover tooltip */
  const tagDisabled = computed(
    () =>
      !tagNoPermission.value &&
      !props.selected.some((data) => data.permission.redis_edit !== false && !isClusterDisabled(data)),
  );
  const tagTooltip = computed(
    () => props.selected.length > 0 && props.selected.every((data) => isClusterDisabled(data)),
  );
  /** 设置/删除告警订阅：全部无权限时置灰可点击，点击弹权限申请 */
  const subscriptionNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => !hasSubscribePermission(data)),
  );
  /** 设置/删除告警订阅：全部有权限且全部已禁用时置灰并 hover tooltip */
  const subscriptionDisabled = computed(
    () =>
      !subscriptionNoPermission.value &&
      !props.selected.some((data) => hasSubscribePermission(data) && !isClusterDisabled(data)),
  );
  const subscriptionTooltip = computed(
    () => props.selected.length > 0 && props.selected.every((data) => isClusterDisabled(data)),
  );
  /** 批量操作权限申请的资源列表 */
  const resources = computed(() => props.selected.map((data) => ({ id: data.id, type: data.db_type })));

  /** 提取Key */
  const handleExtractClick = () => {
    handleToToolbox(TicketTypes.REDIS_KEYS_EXTRACT, props.selected);
  };
  /** 删除Key */
  const handleDeleteKeyClick = () => {
    handleToToolbox(TicketTypes.REDIS_KEYS_DELETE, props.selected);
  };
  /** 备份 */
  const handleBackupClick = () => {
    handleToToolbox(TicketTypes.REDIS_BACKUP, props.selected);
  };
  /** 清档 */
  const handlePurgeClick = () => {
    handleToToolbox(TicketTypes.REDIS_PURGE, props.selected);
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

  const handleSuccess = () => {
    emits('success');
  };
</script>
