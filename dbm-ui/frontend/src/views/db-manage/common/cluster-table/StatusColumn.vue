<template>
  <TableColumn
    col-key="status"
    :filter="columnFilter?.['status']"
    :title="t('状态')"
    width="100">
    <template #default="{ row }: { row: TendnclusterModel }">
      <ClusterRoleStatus :data="row" />
    </template>
  </TableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendnclusterModel from '@services/model/tendbcluster/tendbcluster';

  import { useClusterColumnFilter } from '@hooks';

  import ClusterRoleStatus from '@views/db-manage/common/cluster-role-status/Index.vue';

  import type { ISupportClusterType } from './types';

  interface Props {
    clusterType: ISupportClusterType;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { data: columnFilter } = useClusterColumnFilter({
    cluster_type: props.clusterType,
  });
</script>
