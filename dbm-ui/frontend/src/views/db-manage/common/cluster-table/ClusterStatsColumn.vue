<template>
  <TableColumn
    col-key="cluster_stats"
    :title="t('容量使用率')"
    :width="280">
    <template #default="{ row }: { row: IRowData }">
      <ClusterStats
        :cluster-id="row.id"
        :cluster-type="clusterType" />
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import ClusterStats from '@views/db-manage/common/cluster-stats/Index.vue';

  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props {
    clusterType: ISupportClusterType;
  }

  type IRowData = ClusterModel<T>;

  defineProps<Props>();

  const { t } = useI18n();
</script>
