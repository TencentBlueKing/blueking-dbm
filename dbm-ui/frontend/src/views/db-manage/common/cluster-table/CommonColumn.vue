<template>
  <TableColumn
    col-key="major_version"
    :filter="columnFilter?.['major_version']"
    :min-width="150"
    :title="t('版本')">
    <template #default="{ row }: { row: IRowData }">
      {{ row.major_version || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="disaster_tolerance_level"
    :min-width="160"
    :title="t('容灾要求')">
    <template #default="{ row }: { row: IRowData }">
      {{ row.disasterToleranceLevelName || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="region"
    :filter="columnFilter?.['region']"
    :min-width="150"
    :title="t('地域园区')">
    <template #default="{ row }: { row: IRowData }">
      <div>{{ row.regionDisplay }}</div>
      <TextOverflowLayout>{{ row.clusterSubzonesDisplay }}</TextOverflowLayout>
    </template>
  </TableColumn>
  <TableColumn
    col-key="cluster_spec"
    :min-width="180"
    :title="t('规格')">
    <template #default="{ row }: { row: IRowData }">
      <template v-if="row.cluster_spec.spec_name">
        <TextOverflowLayout
          v-for="spaceName in row.cluster_spec.spec_name.split(',')"
          :key="spaceName">
          {{ spaceName }}
        </TextOverflowLayout>
      </template>
      <span v-else> -- </span>
    </template>
  </TableColumn>
  <TableColumn
    col-key="bk_cloud_id"
    :filter="columnFilter?.['bk_cloud_id']"
    :title="t('管控区域')"
    :width="120">
    <template #default="{ row }: { row: IRowData }">
      {{ row.bk_cloud_name ? `${row.bk_cloud_name}[${row.bk_cloud_id}]` : '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="creator"
    :filter="columnFilter?.['creator']"
    :title="t('创建人')"
    :width="140">
    <template #default="{ row }: { row: IRowData }">
      {{ row.creator || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="create_at"
    :filter="columnFilter?.['create_at']"
    sort
    :title="t('部署时间')"
    :width="180">
    <template #default="{ row }: { row: IRowData }">
      {{ row.createAtDisplay || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="time_zone"
    :filter="columnFilter?.['time_zone']"
    :title="t('时区')"
    :width="100">
    <template #default="{ row }: { row: IRowData }">
      {{ row.cluster_time_zone || '--' }}
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import { useClusterColumnFilter } from '@hooks';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props {
    clusterType: ISupportClusterType;
  }

  export type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();

  const { t } = useI18n();

  type IRowData = ClusterModel<T>;

  const { data: columnFilter } = useClusterColumnFilter({
    cluster_attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'] as const,
    cluster_type: props.clusterType,
  });
</script>
