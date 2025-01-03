<template>
  <BkTableColumn
    field="cluster_stats"
    :label="t('容量使用率')"
    :width="240">
    <template #default="{ data }: { data: IRowData }">
      <ClusterCapacityUsageRate :cluster-stats="data.cluster_stats" />
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';

  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: ISupportClusterType;
  }

  type IRowData = ClusterModel<T>;

  defineProps<Props>();

  const { t } = useI18n();
</script>
