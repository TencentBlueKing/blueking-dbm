<template>
  <BkTableColumn
    field="status"
    :label="t('状态')"
    width="100">
    <template #default="{ data }: { data: TendnclusterModel }">
      <ClusterRoleStatus :data="data"></ClusterRoleStatus>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendnclusterModel from '@services/model/tendbcluster/tendbcluster';

  import ClusterRoleStatus from '@views/db-manage/common/cluster-role-status/Index.vue';

  import type { ISupportClusterType } from './types';

  interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: ISupportClusterType;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
