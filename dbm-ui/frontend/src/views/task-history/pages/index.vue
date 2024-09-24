<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="task-history-list-page">
    <div class="header-action">
      <DbSearchSelect
        :data="searchData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('ID_任务类型_状态_关联单据')"
        style="width: 500px"
        @change="handleSearchValueChange" />
      <BkDatePicker
        v-model="state.filter.daterange"
        class="ml-8"
        :placeholder="t('选择日期范围')"
        style="width: 300px"
        type="daterange"
        @change="fetchTableData" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="getTaskflow"
      @clear-search="handleClearSearch"
      @column-filter="columnFilterChange" />
  </div>
  <!-- 结果文件功能 -->
  <RedisResultFiles
    :id="resultFileState.rootId"
    v-model="resultFileState.isShow" />
</template>

<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { format } from 'date-fns';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import TaskFlowModel from '@services/model/taskflow/taskflow';
  import { getTaskflow } from '@services/source/taskflow';
  import { getTicketTypes } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach } from '@hooks';

  import {
    TicketTypes,
    type TicketTypesStrings,
  } from '@common/const';
  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import {
    getCostTimeDisplay,
    getMenuListSearch,
    getSearchSelectorParams,
  } from '@utils';

  import type { ListState } from '../common/types';
  import RedisResultFiles from '../components/RedisResultFiles.vue';

  const route = useRoute();
  const { t } = useI18n();

  const {
    searchValue,
    columnCheckedMap,
    columnFilterChange,
    clearSearchValue,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.TENDBHA,
    attrs: [],
    fetchDataFn: () => fetchTableData(),
    isCluster: false,
    isQueryAttrs: false,
  });

  /**
   * 近 7 天
   */
  const initDate = () => {
    const end = new Date();
    const start = new Date();
    start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
    return [start.toISOString(), end.toISOString()] as [string, string];
  };

  // 可查看结果文件类型
  const includesResultFiles: TicketTypesStrings[] = [TicketTypes.REDIS_KEYS_EXTRACT, TicketTypes.REDIS_KEYS_DELETE];

  const tableRef = ref();
  const state = reactive<ListState>({
    data: [],
    ticketTypes: [],
    filter: {
      daterange: initDate(),
    },
  });
  /** 查看结果文件功能 */
  const resultFileState = reactive({
    isShow: false,
    rootId: '',
  });

  const searchData = computed(() => [
    {
      name: 'ID',
      id: 'root_ids',
    },
    {
      name: t('任务类型'),
      id: 'ticket_type',
      multiple: true,
      children: state.ticketTypes,
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: Object.keys(TaskFlowModel.STATUS_TEXT_MAP).map((id: string) => ({
        id,
        name: t(TaskFlowModel.STATUS_TEXT_MAP[id]),
      })),
    },
    {
      name: t('关联单据'),
      id: 'uid',
    },
    {
      name: t('执行人'),
      id: 'created_by',
    },
  ]);

  const columns = computed(() => [
    {
      label: 'ID',
      field: 'root_id',
      fixed: 'left',
      render: ({ data }: { data: TaskFlowModel }) => (
        <auth-router-link
          action-id="flow_detail"
          resource={data.root_id}
          permission={data.permission.flow_detail}
          to={{
            name: 'taskHistoryDetail',
            params: {
              root_id: data.root_id,
            },
            query: {
              from: route.name,
            },
          }}>
          { data.root_id }
        </auth-router-link>
      ),
    },
    {
      label: t('任务类型'),
      field: 'ticket_type',
      filter: {
        list: state.ticketTypes.map(item => ({
          text: item.name, value: item.id,
        })),
        checked: columnCheckedMap.value.ticket_type,
      },
      render: ({ data }: { data: TaskFlowModel }) => <span>{data.ticket_type_display || '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      filter: {
        list: Object.keys(TaskFlowModel.STATUS_TEXT_MAP).map(id => ({
          text: t(TaskFlowModel.STATUS_TEXT_MAP[id]), value: id,
        })),
        checked: columnCheckedMap.value.status,
      },
      width: 160,
      render: ({ data }: { data: TaskFlowModel }) => (
        <DbStatus
          type="linear"
          theme={data.statusTheme}>
          {t(data.statusText)}
        </DbStatus>
      ),
    },
    {
      label: t('关联单据'),
      field: 'uid',
      width: 100,
      render: ({ data }: { data: TaskFlowModel }) => (
        data.uid ? <auth-router-link
          action-id="ticket_view"
          permission={data.permission.ticket_view}
          resource={data.uid}
          to={{
            name: 'bizTicketManage',
            query: {
              id: data.uid,
            }
          }}
          target="_blank">
          { data.uid }
        </auth-router-link> : '--'
      ),
    },
    {
      label: t('执行人'),
      field: 'created_by',
      width: 120,
    },
    {
      label: t('执行时间'),
      field: 'created_at',
      width: 250,
      render: ({ data }: { data: TaskFlowModel }) => data.createAtDisplay,
    },
    {
      label: t('耗时'),
      field: 'cost_time',
      width: 150,
      render: ({ cell }: { cell: number }) => getCostTimeDisplay(cell),
    },
    {
      label: t('操作'),
      fixed: 'right',
      width: 120,
      render: ({ data }: { data: TaskFlowModel }) => (
        <div class="table-operations">
          <auth-router-link
            action-id="flow_detail"
            resource={data.root_id}
            permission={data.permission.flow_detail}
            to={{
              name: 'taskHistoryDetail',
              params: {
                root_id: data.root_id,
              },
            }}>
            { t('查看详情') }
          </auth-router-link>
          {includesResultFiles.includes(data.ticket_type) && data.status === 'FINISHED'
            ? <bk-button
                class="ml-6"
                text
                theme="primary"
                onClick={() => handleShowResultFiles(data.root_id)}>
                { t('查看结果文件') }
              </bk-button>
            : null
          }
        </div>
      ),
    },
  ]);

  useRequest(getTicketTypes, {
    onSuccess(data) {
      state.ticketTypes = data.map(item => ({
        id: item.key,
        name: item.value,
      }));
    },
  });

  const fetchTableData = () => {
    const { daterange } = state.filter;
    const dateParams = daterange.filter(item => item).length === 0
      ? {}
      : {
        created_at__gte: format(new Date(daterange[0]), 'yyyy-MM-dd HH:mm:ss'),
        created_at__lte: format(new Date(daterange[1]), 'yyyy-MM-dd HH:mm:ss'),
      };

    tableRef.value.fetchData({
      ...dateParams,
      ...getSearchSelectorParams(searchValue.value),
    }, {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
  };


  async function getMenuList(item: ISearchItem | undefined, keyword: string) {
    if (item?.id !== 'created_by' && keyword) {
      return getMenuListSearch(item, keyword, searchData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
      return searchData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'created_by') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      })
        .then(res => res.results.map(item => ({
          id: item.username,
          name: item.username,
        })));
    }

    // 不需要远层加载
    return searchData.value.find(set => set.id === item.id)?.children || [];
  }

  const handleClearSearch = () => {
    state.filter.daterange = ['', ''];
    clearSearchValue();
  };


  const handleShowResultFiles = (id: string) => {
    resultFileState.isShow = true;
    resultFileState.rootId = id;
  };
</script>

<style lang="less" scoped>
  @import '@/styles/mixins.less';

  .task-history-list-page {
    .header-action {
      display: flex;
      padding-bottom: 16px;
    }
  }
</style>
