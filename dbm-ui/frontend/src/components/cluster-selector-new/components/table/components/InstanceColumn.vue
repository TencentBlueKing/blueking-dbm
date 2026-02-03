<template>
  <TableColumn
    v-if="
      [ClusterTypes.TENDBSINGLE, ClusterTypes.SQLSERVER_SINGLE, ClusterTypes.ORACLE_SINGLE_NONE].includes(
        props.clusterType,
      )
    "
    col-key="instance"
    :title="t('实例')"
    width="180">
    <template #default="{ row }: { row: IRowData }">
      <span
        v-for="item in getInstances(row)"
        :key="item">
        {{ `${item.ip}:${item.port}` }}
      </span>
    </template>
  </TableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import OracleSingleModel from '@services/model/oracle/oracle-single';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';

  import { ClusterTypes } from '@common/const';

  import type { ISupportClusterType } from '@components/cluster-selector-new/types';

  interface Props {
    clusterType: ISupportClusterType;
  }

  type IRowData = TendbsingleModel | SqlServerSingleModel | OracleSingleModel;

  const props = defineProps<Props>();
  const { t } = useI18n();

  const getInstances = (row: IRowData) => {
    const roleMap = {
      [ClusterTypes.ORACLE_SINGLE_NONE]: 'primaries',
      [ClusterTypes.SQLSERVER_SINGLE]: 'storages',
      [ClusterTypes.TENDBSINGLE]: 'masters',
    };
    const role = roleMap[props.clusterType as keyof typeof roleMap];
    return row[role as keyof IRowData];
  };
</script>
