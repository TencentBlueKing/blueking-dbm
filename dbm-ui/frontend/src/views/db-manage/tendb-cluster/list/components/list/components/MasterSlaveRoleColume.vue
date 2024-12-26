<template>
  <BaseRoleColumn v-bind="props">
    <template #instanceList="{ clusterData }: { clusterData: TendbClusterModel }">
      <BkTable :data="clusterData.spider_master">
        <BkTableColumn label="Master">
          <template #default="{ data }: { data: TendbClusterModel['spider_master'][number] }">
            {{ data.instance }}
          </template>
        </BkTableColumn>
        <BkTableColumn label="Slave">
          <template #default="{ rowIndex }: { rowIndex: number }">
            {{ clusterData.spider_slave[rowIndex]?.instance || '--' }}
          </template>
        </BkTableColumn>
        <!-- <BkTableColumn :label="t('分片')">
          <template #default="{ data }: { data: TendbClusterModel['spider_master'][number] }">
            {{ data.seg_range || '--' }}
          </template>
        </BkTableColumn> -->
      </BkTable>
    </template>
  </BaseRoleColumn>
</template>
<script setup lang="ts">
  // import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { ClusterTypes } from '@common/const';

  import BaseRoleColumn, {
    type Props,
  } from '@views/db-manage/common/cluster-table-column/components/base-role-column/Index.vue';

  const props = defineProps<
    Props<ClusterTypes.TENDBCLUSTER> & {
      field: 'spider_master' | 'spider_slave';
    }
  >();

  // const { t } = useI18n();
</script>
