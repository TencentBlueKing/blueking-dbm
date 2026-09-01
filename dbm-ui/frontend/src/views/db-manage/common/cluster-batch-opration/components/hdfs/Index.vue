<template>
  <BkDropdownItem v-db-console="'hdfs.clusterManage.batchAddTag'">
    <BatchOperationButton
      :action-id="TAG_ACTION_ID"
      :no-permission="tagNoPermission"
      :resources="resources"
      @click="handleAddTagClick">
      {{ t('添加标签') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'hdfs.clusterManage.batchRemoveTag'">
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
    v-db-console="'rhdfs.clusterManage.configAlarmSubscription'">
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
    v-db-console="'hdfs.clusterManage.deleteAlarmSubscription'">
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
    :get-editable="(item) => item.permission?.hdfs_edit !== false"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchRemoveTag
    v-model:is-show="showClusterBatchRemoveTag"
    :get-editable="(item) => item.permission?.hdfs_edit !== false"
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

  import HdfsModel from '@services/model/hdfs/hdfs';

  import { useAlarmSubscribe } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import ClusterBatchAddTag from '@views/db-manage/common/cluster-batch-add-tag/Index.vue';
  import ClusterBatchDeleteSubscription from '@views/db-manage/common/cluster-batch-delete-subscription/Index.vue';
  import ClusterBatchEditSubscription from '@views/db-manage/common/cluster-batch-edit-subscription/Index.vue';
  import ClusterBatchRemoveTag from '@views/db-manage/common/cluster-batch-remove-tag/Index.vue';

  import BatchOperationButton from '../BatchOperationButton.vue';

  interface Props {
    selected: HdfsModel[];
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: ClusterTypes.HDFS,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { isClusterTypeAlarmSupported } = useAlarmSubscribe([ClusterTypes.HDFS]);

  const showClusterBatchAddTag = ref(false);
  const showClusterBatchRemoveTag = ref(false);
  const showClusterBatchEditSubscription = ref(false);
  const showClusterBatchDeleteSubscription = ref(false);

  /** 添加/移除标签鉴权 action-id（与单行一致） */
  const TAG_ACTION_ID = 'hdfs_edit';
  /** 设置/删除告警订阅鉴权 action-id（与单行一致） */
  const SUBSCRIBE_ACTION_ID = 'hdfs_subscribe_monitor';
  /** 是否具备告警订阅权限 */
  const hasSubscribePermission = (data: HdfsModel) =>
    (data.permission as Record<string, boolean | undefined>)?.[SUBSCRIBE_ACTION_ID] !== false;
  /** 添加/移除标签：全部无权限时置灰可点击，点击弹权限申请 */
  const tagNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => data.permission.hdfs_edit === false),
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
