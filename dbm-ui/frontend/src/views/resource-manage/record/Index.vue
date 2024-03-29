<template>
  <div class="resource-pool-operation-record-page">
    <div class="header-action mb-16">
      <BkDatePicker
        v-model="operationDateTime"
        append-to-body
        clearable
        :placeholder="$t('请选择操作时间')"
        type="datetimerange"
        @change="handleDateChange" />
      <DbSearchSelect
        v-model="searchValues"
        class="ml-8"
        :data="serachData"
        :placeholder="$t('请输入操作人或选择条件搜索')"
        style="width: 500px"
        unique-select
        :validate-values="serachValidateValues"
        @change="handleSearch" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="dataSource"
      releate-url-query
      @clear-search="handleClearSearch" />
  </div>
</template>
<script setup lang="tsx">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import {
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import OperationModel from '@services/model/db-resource/Operation';
  import { fetchOperationList } from '@services/source/dbresourceResource';

  import { ipv4 } from '@common/regex';

  import { getSearchSelectorParams } from '@utils';

  import HostDetail from './components/HostDetail.vue';

  const route = useRoute();
  const { t } = useI18n();

  const dataSource = fetchOperationList;

  const tableRef = ref();
  const operationDateTime = ref<[string, string]>([
    dayjs().subtract(7, 'day')
      .format('YYYY-MM-DD HH:mm:ss'),
    dayjs().format('YYYY-MM-DD HH:mm:ss'),
  ]);
  const searchValues = ref([]);

  const serachData = [
    {
      name: 'IP',
      id: 'ip_list',
    },
    {
      name: t('操作类型'),
      id: 'operation_type',
      children: [
        {
          id: [OperationModel.OPERATIN_TYPE_IMPORTED],
          name: t('导入主机'),

        },
        {
          id: [OperationModel.OPERATIN_TYPE_CONSUMED],
          name: t('消费主机'),
        },
      ],
    },
    {
      name: t('关联单据'),
      id: 'ticket_ids',
    },
    {
      name: t('关联任务'),
      id: 'task_ids',
    },
    {
      name: t('操作状态'),
      id: 'status',
      children: [
        {
          id: [OperationModel.STATUS_PENDING],
          name: t('等待执行'),

        },
        {
          id: [OperationModel.STATUS_RUNNING],
          name: t('执行中'),

        },
        {
          id: [OperationModel.STATUS_SUCCEEDED],
          name: t('执行成功'),

        },
        {
          id: [OperationModel.STATUS_FAILED],
          name: t('执行失败'),

        },
        {
          id: [OperationModel.STATUS_REVOKED],
          name: t('执行失败'),
        },
      ],
    },
    {
      name: t('操作人'),
      id: 'operator',
    },
  ];

  const tableColumn = [
    {
      label: t('操作时间'),
      field: 'update_time',
      fixed: true,
      width: 200,
      sort: true,
      render: ({ data }: {data: OperationModel}) => data.updateTimeDisplay,
    },
    {
      label: t('操作主机明细（台）'),
      field: 'total_count',
      render: ({ data }: {data: OperationModel}) => (
        <HostDetail data={data} />
      ),
    },
    {
      label: t('操作类型'),
      field: 'operationTypeText',
      render: ({ data }: {data: OperationModel}) => data.operationTypeText,
    },
    {
      label: t('单据类型'),
      field: 'ticket_type_display',
      render: ({ data }: {data: OperationModel}) => data.ticket_type_display || '--',
    },
    {
      label: t('关联单据'),
      field: 'ticket_id',
      width: 170,
      render: ({ data }: {data: OperationModel}) => (data.ticket_id
        ? <auth-router-link
            action-id="ticket_view"
            resource={data.ticket_id}
            permission={data.permission.ticket_view}
            to={{
              name: 'SelfServiceMyTickets',
              query: {
                id: data.ticket_id,
              },
            }}
            target="_blank">
            {data.ticket_id}
          </auth-router-link>
        : '--')
      ,
    },
    {
      label: t('关联任务'),
      field: 'task_id',
      render: ({ data }: {data: OperationModel}) => (data.task_id
        ? <auth-router-link
            action-id="flow_detail"
            resource={data.task_id}
            permission={data.permission.flow_detail}
            to={{
              name: 'taskHistoryDetail',
              params: {
                root_id: data.task_id,
              },
              query: {
                from: route.name as string,
              },
            }}
            target="_blank">
            {data.task_id}
          </auth-router-link>
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
        <div style="display: flex; align-items: center;">
          <db-icon
            class={{
              'rotate-loading': data.isRunning,
            }}
            style={{
              'font-size': data.isRunning ? '12px' : '16px',
              'vertical-align': 'middle',
            }}
            type={data.statusIcon}
            svg />
          <span class="ml-4">{data.statusText}</span>
        </div>
      ),
    },
  ];

  const serachValidateValues = (
    payload: Record<'id'|'name', string>,
    values: Array<Record<'id'|'name', string>>,
  ) => {
    if (payload.id === 'ticket_ids') {
      const [{ id }] = values;
      return Promise.resolve(_.every(id.split(','), item => /^\d+?/.test(item)));
    }
    if (payload.id === 'ip_list') {
      const [{ id }] = values;
      return Promise.resolve(_.every(id.split(','), item => ipv4.test(item)));
    }
    return Promise.resolve(true);
  };

  // 获取数据
  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValues.value);
    const [
      beginTime,
      endTime,
    ] = operationDateTime.value;
    tableRef.value.fetchData({
      ...searchParams,
      begin_time: beginTime ? dayjs(beginTime).format('YYYY-MM-DD HH:mm:ss') : '',
      end_time: endTime ? dayjs(endTime).format('YYYY-MM-DD HH:mm:ss') : '',
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
  // 清空搜索条件
  const handleClearSearch = () => {
    operationDateTime.value = ['', ''];
    searchValues.value = [];
    fetchData();
  };
</script>

<style lang="less">
  .resource-pool-operation-record-page {
    .header-action {
      display: flex;
    }
  }
</style>
