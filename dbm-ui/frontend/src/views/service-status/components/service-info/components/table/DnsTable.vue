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
      <template #default="{ row }: { row: DnsServiceStatusModel }">
        <ClusterInstanceStatus :data="row.status" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="bk_city"
      :title="t('城市名')">
    </TableColumn>
    <TableColumn
      col-key="isAccessDisplay"
      :title="t('可访问')">
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

  import DnsServiceStatusModel from '@services/model/db-extension/dns-service-status';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  interface Props {
    list: DnsServiceStatusModel[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() =>
    props.list.map((item, index) => Object.assign(item, { rowKey: `${index}#${Date.now()}` })),
  );
</script>
