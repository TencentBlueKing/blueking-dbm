<template>
  <div class="resource-pool-operation-record-page">
    <div class="header-action mb-16">
      <BkDatePicker
        v-model="operationDateTime"
        append-to-body
        clearable
        :placeholder="t('请选择操作时间')"
        type="datetimerange"
        @change="handleDateChange" />
      <DbSearchSelect
        class="ml-8"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="dataSource"
      releate-url-query
      @clear-search="handleClearSearch"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange" />
  </div>
</template>
<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import OperationModel from '@services/model/db-resource/Operation';
  import { fetchOperationList } from '@services/source/dbresourceResource';
  import { getTicketTypes } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  import HostDetail from './components/HostDetail.vue';

  const route = useRoute();
  const { t } = useI18n();

  const {
    searchValue,
    sortValue,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: 'resource_record',
    attrs: [],
    fetchDataFn: () => fetchData(),
  });

  const dataSource = fetchOperationList;

  const tableRef = ref();
  const operationDateTime = ref<[string, string]>([
    dayjs().subtract(7, 'day')
      .format('YYYY-MM-DD HH:mm:ss'),
    dayjs().format('YYYY-MM-DD HH:mm:ss'),
  ]);
  const ticketTypes = ref<Array<{id: string, name: string}>>([]);

  const searchSelectData = computed(() => [
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
      name: t('单据类型'),
      id: 'ticket_types',
      multiple: true,
      children: ticketTypes.value,
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
  ] as ISearchItem[]);

  const tableColumn = computed(() => [
    {
      label: t('操作时间'),
      field: 'update_time',
      fixed: 'left',
      width: 200,
      sort: true,
      render: ({ data }: {data: OperationModel}) => data.updateTimeDisplay,
    },
    {
      label: t('操作主机明细（台）'),
      field: 'total_count',
      sort: true,
      render: ({ data }: {data: OperationModel}) => (
        <HostDetail data={data} />
      ),
    },
    {
      label: t('操作类型'),
      field: 'operation_type',
      filter: {
        list: [
          {
            value: [OperationModel.OPERATIN_TYPE_IMPORTED],
            text: t('导入主机'),
          },
          {
            value: [OperationModel.OPERATIN_TYPE_CONSUMED],
            text: t('消费主机'),
          },
        ],
        checked: columnCheckedMap.value.operation_type,
      },
      render: ({ data }: {data: OperationModel}) => data.operationTypeText,
    },
    {
      label: t('单据类型'),
      field: 'ticket_types',
      filter: {
        list: ticketTypes.value.map(item => ({
          value: item.id,
          text: item.name,
        })),
        checked: columnCheckedMap.value.ticket_types,
      },
      render: ({ data }: {data: OperationModel}) => data.ticket_type_display || '--',
    },
    {
      label: t('关联单据'),
      field: 'ticket_id',
      width: 170,
      render: ({ data }: {data: OperationModel}) => (data.ticket_id
        ? <auth-router-link
            to={{
              name: 'bizTicketManage',
              query: {
                id: data.ticket_id,
              },
            }}
            action-id="ticket_view"
            resource={data.ticket_id}
            permission={data.permission.ticket_view}
            target="_blank">
            {data.ticket_id}
          </auth-router-link>
        : '--'),
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
      filter: {
        list: [
          {
            value: [OperationModel.STATUS_PENDING],
            text: t('等待执行'),

          },
          {
            value: [OperationModel.STATUS_RUNNING],
            text: t('执行中'),

          },
          {
            value: [OperationModel.STATUS_SUCCEEDED],
            text: t('执行成功'),

          },
          {
            value: [OperationModel.STATUS_FAILED],
            text: t('执行失败'),

          },
          {
            value: [OperationModel.STATUS_REVOKED],
            text: t('执行失败'),
          },
        ],
        checked: columnCheckedMap.value.status,
      },
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
  ]);

  useRequest(getTicketTypes, {
    defaultParams: [{
      is_apply: 1,
    }],
    onSuccess(data) {
      ticketTypes.value = data.map(item => ({
        id: item.key,
        name: item.value,
      }));
    },
  });

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'operator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
      return searchSelectData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'operator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then(res => res.results.map(item => ({
        id: item.username,
        name: item.username,
      })));
    }

    // 不需要远层加载
    return searchSelectData.value.find(set => set.id === item.id)?.children || [];
  };

  // const serachValidateValues = (
  //   payload: Record<'id'|'name', string>,
  //   values: Array<Record<'id'|'name', string>>,
  // ) => {
  //   if (payload.id === 'ticket_ids') {
  //     const [{ id }] = values;
  //     return Promise.resolve(_.every(id.split(','), item => /^\d+?/.test(item)));
  //   }
  //   if (payload.id === 'ip_list') {
  //     const [{ id }] = values;
  //     return Promise.resolve(_.every(id.split(','), item => ipv4.test(item)));
  //   }
  //   return Promise.resolve(true);
  // };

  // 获取数据
  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    const [
      beginTime,
      endTime,
    ] = operationDateTime.value;
    tableRef.value.fetchData({
      ...searchParams,
      ...sortValue,
      begin_time: beginTime ? dayjs(beginTime).format('YYYY-MM-DD HH:mm:ss') : '',
      end_time: endTime ? dayjs(endTime).format('YYYY-MM-DD HH:mm:ss') : '',
    });
  };

  // 切换时间
  const handleDateChange = () => {
    fetchData();
  };

  // 清空搜索条件
  const handleClearSearch = () => {
    operationDateTime.value = ['', ''];
    clearSearchValue();
  };

  // const handleGoTicketDetail = (data: OperationModel) => {
  //   const { href } = router.resolve({
  //     name: 'bizTicketManage',
  //     query: {
  //       id: data.ticket_id,
  //     },
  //   });
  //   window.open(href.replace(/(\d)+/, `${data.bk_biz_id}`));
  // };
</script>

<style lang="less">
  .resource-pool-operation-record-page {
    .header-action {
      display: flex;
    }
  }
</style>
