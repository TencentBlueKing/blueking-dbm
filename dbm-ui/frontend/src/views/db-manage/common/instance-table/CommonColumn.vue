<template>
  <TableColumn
    col-key="status"
    :filter="columnFilter?.['status']"
    :title="t('状态')"
    width="100">
    <template #default="{ row }: { row: IRowData }">
      <ClusterInstanceStatus :data="row.status" />
    </template>
  </TableColumn>
  <TableColumn
    col-key="role"
    :filter="columnFilter?.['role']"
    :title="t('部署角色')"
    :width="140">
    <template #default="{ row }: { row: IRowData }">
      {{ row.role }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="version"
    :filter="columnFilter?.['version']"
    :title="t('版本')"
    :width="240">
    <template #default="{ row }: { row: IRowData }">
      {{ row.version || '--' }}
    </template>
  </TableColumn>
  <slot name="relatedCluster" />
  <slot name="ip" />
  <TableColumn
    col-key="bk_sub_zone"
    :filter="columnFilter?.['bk_sub_zone']"
    :title="t('园区')"
    :width="140">
    <template #default="{ row }: { row: IRowData }">
      {{ row.bk_sub_zone || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="bk_os_name"
    :filter="columnFilter?.['bk_os_name']"
    :title="t('操作系统')"
    :width="140">
    <template #default="{ row }: { row: IRowData }">
      {{ row.bk_os_name || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="create_at"
    :filter="columnFilter?.['create_at']"
    sorter
    :title="t('部署时间')"
    :width="140">
    <template #default="{ row }: { row: IRowData }">
      {{ row.createAtDisplay || '--' }}
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useInstanceColumnFilter } from '@hooks';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  import type { InstanceModel, ISupportClusterType } from './types';

  export interface Props {
    clusterType: ISupportClusterType;
  }

  export type Emits = (e: 'refresh') => void;

  export interface Slots {
    ip: () => VNode;
    relatedCluster: () => VNode;
  }

  const props = defineProps<Props>();
  defineSlots<Slots>();

  const { t } = useI18n();

  type IRowData = InstanceModel<T>;

  const { data: columnFilter } = useInstanceColumnFilter({
    cluster_type: props.clusterType,
    instance_attrs: ['role', 'version', 'bk_os_name', 'bk_sub_zone'] as const,
  });
</script>
