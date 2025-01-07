<template>
  <BaseRoleColumn v-bind="props">
    <template #nodeTag="data">
      <slot
        name="nodeTag"
        v-bind="data" />
    </template>
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
      </BkTable>
    </template>
  </BaseRoleColumn>
</template>
<script setup lang="ts">
  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { ClusterTypes } from '@common/const';

  import BaseRoleColumn, {
    type Props,
    type Slots,
  } from '@views/db-manage/common/cluster-table-column/components/base-role-column/Index.vue';

  const props = defineProps<Props<ClusterTypes.TENDBCLUSTER, 'spider_master' | 'spider_slave'>>();

  defineSlots<Slots<ClusterTypes.TENDBCLUSTER, 'spider_master' | 'spider_slave'>>();
</script>
