<template>
  <BkDropdownItem v-db-console="'hdfs.clusterManage.batchAddTag'">
    <BkButton
      class="opration-button"
      :disabled="!isClusterTagEditable"
      text
      @click="() => (showClusterBatchAddTag = true)">
      {{ t('添加标签') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'hdfs.clusterManage.batchRemoveTag'">
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
    v-db-console="'rhdfs.clusterManage.configAlarmSubscription'">
    <BkButton
      class="opration-button"
      text
      @click="() => (showClusterBatchEditSubscription = true)">
      {{ t('设置告警订阅') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem
    v-if="isClusterTypeAlarmSupported"
    v-db-console="'hdfs.clusterManage.deleteAlarmSubscription'">
    <BkButton
      class="opration-button"
      text
      @click="() => (showClusterBatchDeleteSubscription = true)">
      {{ t('删除告警订阅') }}
    </BkButton>
  </BkDropdownItem>
  <ClusterBatchAddTag
    v-model:is-show="showClusterBatchAddTag"
    :selected="selected"
    @success="handleSuccess" />
  <ClusterBatchRemoveTag
    v-model:is-show="showClusterBatchRemoveTag"
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

  const isClusterTagEditable = computed(() => props.selected.every((data) => data.permission.hdfs_edit));

  const handleSuccess = () => {
    emits('success');
  };
</script>
