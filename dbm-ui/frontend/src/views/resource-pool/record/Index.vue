<template>
  <div class="resource-pool-operation-record-page">
    <div class="header-action mb-16">
      <BkDatePicker
        v-model="operationDateTime"
        append-to-body
        clearable
        type="datetimerange"
        @change="handleDateChange" />
      <DbSearchSelect
        v-model="searchValues"
        class="ml-8"
        :data="serachData"
        :placeholder="$t('请输入操作人或选择条件搜索')"
        style="width: 500px"
        unique-select
        @change="handleSearch" />
    </div>
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

  import { getSearchSelectorParams } from '@utils';

  const { t } = useI18n();

  const dataSource = fetchOperationList;

  const tableRef = ref();
  const operationDateTime = ref<[string, string]>(['', '']);
  const searchValues = ref([]);

  const serachData = [
    {
      name: t('操作类型'),
      id: 'operation_type',
    },
    {
      name: t('操作状态'),
      id: 'status',
    },
    {
      name: t('操作人'),
      id: 'operator',
    },
  ];

  const tableColumn = [
    {
      label: t('操作时间'),
      field: 'create_time',
      fixed: true,
      width: 170,
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
      render: ({ data }: {data: OperationModel}) => (data.ticket_id
        ? <router-link
            to={{
              name: 'SelfServiceMyTickets',
              params: {
                typeId: data.ticket_id,
              },
            }}
            target="_blank">
            {data.ticket_id}
          </router-link>
        : '--')
      ,
    },
    {
      label: t('关联任务'),
      field: 'task_id',
      render: ({ data }: {data: OperationModel}) => (data.task_id
        ? <router-link
            to={{
              name: 'DatabaseMissionDetails',
              params: {
                bizId: data.biz_id,
                root_id: data.task_id,
              },
            }}
            target="_blank">
            {data.task_id}
          </router-link>
        : '--'),
    },
    {
      label: t('操作人'),
      field: 'operator',
    },
    {
      label: t('操作结果'),
      field: 'status',
      width: 150,
      render: ({ data }: {data: OperationModel}) => (
        <div>
          <db-icon type={data.statusIcon} svg />
          <span class="ml-8">{data.statusText}</span>
        </div>
      ),
    },
  ];

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValues.value);
    const [
      beginTime,
      endTime,
    ] = operationDateTime.value;
    tableRef.value.fetchData({
      ...searchParams,
      begin_time: beginTime,
      end_time: endTime,
    });
  };

  // 切换时间
  const handleDateChange = () => {
    fetchData();
  };
  // 搜索
  const handleSearch = () => {
    fetchData();
  };

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="postcss">
  .resource-pool-operation-record-page {
    .header-action{
      display: flex;
    }
  }
</style>
