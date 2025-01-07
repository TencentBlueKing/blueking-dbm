<template>
  <BaseRoleColumn v-bind="props">
    <template #default="{ data }"> {{ data.ip }}:{{ data.port }}(%_{{ data.shard_id }}) </template>
    <template #instanceList="{ clusterData }: { clusterData: TendbClusterModel }">
      <BkTable :data="clusterData.remote_db">
        <BkTableColumn label="Master">
          <template #default="{ data }: { data: TendbClusterModel['remote_db'][number] }">
            {{ data.instance }}
          </template>
        </BkTableColumn>
        <BkTableColumn label="Slave">
          <template #default="{ rowIndex }: { rowIndex: number }">
            {{ clusterData.remote_dr[rowIndex]?.instance || '--' }}
          </template>
        </BkTableColumn>
        <BkTableColumn label="Shard_id">
          <template #default="{ data }: { data: TendbClusterModel['remote_db'][number] }">
            {{ data.shard_id || '--' }}
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
  } from '@views/db-manage/common/cluster-table-column/components/base-role-column/Index.vue';

  const props = defineProps<
    Props<ClusterTypes.TENDBCLUSTER, 'remote_db' | 'remote_dr'> & {
      field: 'remote_db' | 'remote_dr';
    }
  >();
</script>
