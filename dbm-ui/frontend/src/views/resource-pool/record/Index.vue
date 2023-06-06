<template>
  <div class="resource-pool-operation-record-page">
    <DbTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="dataSource" />
  </div>
</template>
<script setup lang="tsx">
  import {
    onMounted,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import {
    fetchOperationList,
  } from '@services/dbResource';
  import OperationModel from '@services/model/db-resource/Operation';

  const { t } = useI18n();

  const dataSource = fetchOperationList;

  const tableRef = ref();

  const tableColumn = [
    {
      label: t('操作时间'),
      field: 'create_time',
      fixed: true,
    },
    {
      label: t('操作主机明细（台）'),
      field: 'total_count',
    },
    {
      label: t('操作类型'),
      field: 'operationTypeText',
    },
    {
      label: t('关联单据'),
      field: 'ticket_id',
      width: 170,
      render: ({ data }: {data: OperationModel}) => data.ticket_id || '--',
    },
    {
      label: t('关联任务'),
      field: 'task_id',
      render: ({ data }: {data: OperationModel}) => data.task_id || '--',
    },
    {
      label: t('操作人'),
      field: 'operator',
    },
    {
      label: t('操作结果'),
      field: 'status',
      render: ({ data }: {data: OperationModel}) => (
        <div>
          <db-icon type={data.statusIcon} />
          {data.statusText}
        </div>
      ),
    },
  ];

  onMounted(() => {
    tableRef.value.fetchData();
  });
</script>
<style lang="postcss">
  .resource-pool-operation-record-page {
    display: block
  }
</style>
