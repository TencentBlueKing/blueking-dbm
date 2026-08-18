<template>
  <BkDropdownItem v-db-console="'redis.clusterManage.extractKey'">
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
  <BkDropdownItem v-db-console="'redis.clusterManage.deleteKey'">
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
  <BkDropdownItem v-db-console="'redis.clusterManage.backup'">
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
  <BkDropdownItem
    v-db-console="'redis.clusterManage.dbClear'"
    @click="handleToToolbox(TicketTypes.REDIS_PURGE, selected)">
    <BkButton
      v-bk-tooltips="{
        disabled: !batchOperationDisabled,
        content: t('仅已启用集群可以清档'),
        placement: 'right',
      }"
      class="opration-button"
      :disabled="batchOperationDisabled"
      text>
      {{ t('清档') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'redis.clusterManage.batchAddTag'">
    <BatchOperationButton
      :action-id="TAG_ACTION_ID"
      :disabled="!tagEditable && !tagNoPermission"
      :no-permission="tagNoPermission"
      :resources="resources"
      @click="handleAddTagClick">
      {{ t('添加标签') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'redis.clusterManage.batchRemoveTag'">
    <BatchOperationButton
      :action-id="TAG_ACTION_ID"
      :disabled="!tagEditable && !tagNoPermission"
      :no-permission="tagNoPermission"
      :resources="resources"
      @click="handleRemoveTagClick">
      {{ t('移除标签') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-if="isClusterTypeAlarmSupported"
    v-db-console="'redis.clusterManage.configAlarmSubscription'">
    <BatchOperationButton
      :action-id="SUBSCRIBE_ACTION_ID"
      :disabled="!subscriptionEditable && !subscriptionNoPermission"
      :no-permission="subscriptionNoPermission"
      :resources="resources"
      @click="handleEditSubscriptionClick">
      {{ t('设置告警订阅') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-if="isClusterTypeAlarmSupported"
    v-db-console="'redis.clusterManage.deleteAlarmSubscription'">
    <BatchOperationButton
      :action-id="SUBSCRIBE_ACTION_ID"
      :disabled="!subscriptionEditable && !subscriptionNoPermission"
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

  const batchOperationDisabled = computed(() =>
    props.selected.some((data) => {
      if (!data.isOnline) {
        return true;
      }

      if (data.operations?.length > 0) {
        const operationData = data.operations[0];
        return ([TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_PROXY_CLOSE] as string[]).includes(
          operationData.ticket_type,
        );
      }

      return false;
    }),
  );

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
  /** 批量操作权限申请的资源列表 */
  const resources = computed(() => props.selected.map((data) => ({ id: data.id, type: data.db_type })));

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
