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
    <BkButton
      class="opration-button"
      :disabled="!isClusterTagEditable"
      text
      @click="() => (showClusterBatchAddTag = true)">
      {{ t('添加标签') }}
    </BkButton>
  </BkDropdownItem>
  <BkDropdownItem v-db-console="'redis.clusterManage.batchRemoveTag'">
    <BkButton
      class="opration-button"
      :disabled="!isClusterTagEditable"
      text
      @click="() => (showClusterBatchRemoveTag = true)">
      {{ t('移除标签') }}
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
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterBatchAddTag from '@views/db-manage/common/cluster-batch-add-tag/Index.vue';
  import ClusterBatchRemoveTag from '@views/db-manage/common/cluster-batch-remove-tag/Index.vue';
  import { useRedisClusterListToToolbox } from '@views/db-manage/common/hooks';

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

  const showClusterBatchAddTag = ref(false);
  const showClusterBatchRemoveTag = ref(false);

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

  const isClusterTagEditable = computed(() =>
    props.selected.every((data) => data.permission[`${data.db_type}_edit` as keyof typeof data.permission]),
  );

  const handleSuccess = () => {
    emits('success');
  };
</script>
