<template>
  <PrimaryTable
    :data="tableData"
    row-key="rowKey">
    <TableColumn
      col-key="ip"
      fixed="left"
      :title="t('实例')"
      :width="200">
      <template #default="{ row }: { row: DbhaServiceStatusModel }">
        <span>{{ row.ip }}</span>
        <span v-if="row.port">:{{ row.port }}</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="status"
      :title="t('状态')"
      :width="100">
      <template #default="{ row }: { row: DbhaServiceStatusModel }">
        <ClusterInstanceStatus :data="row.status" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="module"
      :title="t('类型')">
    </TableColumn>
    <TableColumn
      col-key="db_type"
      :title="t('探测组件类型')">
    </TableColumn>
    <TableColumn
      col-key="bk_city_name"
      :title="t('城市名')">
    </TableColumn>
    <TableColumn
      col-key="startTimeDisplay"
      :title="t('启动时间')">
    </TableColumn>
    <TableColumn
      col-key="lastTimeDisplay"
      :title="t('上次更新时间')">
    </TableColumn>
    <TableColumn
      col-key="report_interval"
      :title="t('上报间隔')">
      <template #default="{ row }: { row: DbhaServiceStatusModel }">
        {{ row.report_interval || '--' }}
      </template>
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DbhaServiceStatusModel from '@services/model/db-extension/dbha-service-status';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  interface Props {
    list: DbhaServiceStatusModel[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() =>
    props.list.map((item, index) => Object.assign(item, { rowKey: `${index}#${Date.now()}` })),
  );
</script>
