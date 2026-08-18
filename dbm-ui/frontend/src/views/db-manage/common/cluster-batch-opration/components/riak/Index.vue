<template>
  <BkDropdownItem v-db-console="'riak.clusterManage.batchAddTag'">
    <BatchOperationButton
      :action-id="TAG_ACTION_ID"
      :disabled="!tagEditable && !tagNoPermission"
      :no-permission="tagNoPermission"
      :resources="resources"
      @click="handleAddTagClick">
      {{ t('添加标签') }}
    </BatchOperationButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'riak.clusterManage.batchRemoveTag'">
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
    v-db-console="'riak.clusterManage.configAlarmSubscription'">
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
    v-db-console="'riak.clusterManage.deleteAlarmSubscription'">
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
    :get-editable="(item) => item.permission?.riak_edit !== false"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchRemoveTag
    v-model:is-show="showClusterBatchRemoveTag"
    :get-editable="(item) => item.permission?.riak_edit !== false"
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

  import RiakModel from '@services/model/riak/riak';

  import { useAlarmSubscribe } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import ClusterBatchAddTag from '@views/db-manage/common/cluster-batch-add-tag/Index.vue';
  import ClusterBatchDeleteSubscription from '@views/db-manage/common/cluster-batch-delete-subscription/Index.vue';
  import ClusterBatchEditSubscription from '@views/db-manage/common/cluster-batch-edit-subscription/Index.vue';
  import ClusterBatchRemoveTag from '@views/db-manage/common/cluster-batch-remove-tag/Index.vue';

  import BatchOperationButton from '../BatchOperationButton.vue';

  interface Props {
    selected: RiakModel[];
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: ClusterTypes.RIAK,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { isClusterTypeAlarmSupported } = useAlarmSubscribe([ClusterTypes.RIAK]);

  const showClusterBatchAddTag = ref(false);
  const showClusterBatchRemoveTag = ref(false);
  const showClusterBatchEditSubscription = ref(false);
  const showClusterBatchDeleteSubscription = ref(false);

  /** 添加/移除标签鉴权 action-id（与单行一致） */
  const TAG_ACTION_ID = 'riak_edit';
  /** 设置/删除告警订阅鉴权 action-id（与单行一致） */
  const SUBSCRIBE_ACTION_ID = 'riak_subscribe_monitor';
  /** 是否具备告警订阅权限 */
  const hasSubscribePermission = (data: RiakModel) =>
    (data.permission as Record<string, boolean | undefined>)?.[SUBSCRIBE_ACTION_ID] !== false;
  /** 添加/移除标签：全部无权限时置灰可点击，点击弹权限申请 */
  const tagNoPermission = computed(
    () => props.selected.length > 0 && props.selected.every((data) => data.permission.riak_edit === false),
  );
  /** 添加/移除标签：至少 1 个有权限则亮起 */
  const tagEditable = computed(() => props.selected.some((data) => data.permission.riak_edit !== false));
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
