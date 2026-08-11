<template>
  <PrimaryTable
    :data="tableData"
    row-key="rowKey">
    <TableColumn
      col-key="ip"
      fixed="left"
      title="IP"
      :width="200">
    </TableColumn>
    <TableColumn
      col-key="status"
      :title="t('状态')"
      :width="100">
      <template #default="{ row }: { row: DrsServiceStatusModel }">
        <ClusterInstanceStatus :data="row.status" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="updater"
      :title="t('更新人')">
    </TableColumn>
    <TableColumn
      col-key="updateAtDisplay"
      :title="t('更新时间')">
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DrsServiceStatusModel from '@services/model/db-extension/drs-service-status';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  interface Props {
    list: DrsServiceStatusModel[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() =>
    props.list.map((item, index) => Object.assign(item, { rowKey: `${index}#${Date.now()}` })),
  );
</script>
