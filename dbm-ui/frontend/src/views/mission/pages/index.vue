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
  <div class="history-mission">
    <div class="history-mission__operations flex-align">
      <DbSearchSelect
        v-model="state.filter.searchValues"
        :data="searchData"
        :get-menu-list="getMenuList"
        :placeholder="$t('ID_任务类型_状态_关联单据')"
        style="width: 500px;"
        unique-select
        @change="handeChangePage(1)" />
      <BkDatePicker
        v-model="state.filter.daterange"
        class="ml-8"
        :placeholder="$t('选择日期范围')"
        style="width: 300px;"
        type="daterange"
        @change="handleChangeDate" />
    </div>
    <div class="history-mission__content">
      <BkLoading :loading="state.isLoading">
        <DbOriginalTable
          class="history-mission-table"
          :columns="columns"
          :data="state.data"
          :is-anomalies="state.isAnomalies"
          :is-searching="isSearching"
          :max-height="tableMaxHeight"
          :min-height="0"
          :pagination="state.pagination"
          remote-pagination
          @clear-search="handleClearSearch"
          @page-limit-change="handeChangeLimit"
          @page-value-change="handeChangePage"
          @refresh="fetchTaskflow" />
      </BkLoading>
    </div>
  </div>
  <!-- 结果文件功能 -->
  <RedisResultFiles
    :id="resultFileState.rootId"
    v-model:is-show="resultFileState.isShow" />
</template>

<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import { getUseList } from '@services/common';
  import { getTicketTypes } from '@services/ticket';
  import type { TaskflowItem } from '@services/types/taskflow';

  import { useDefaultPagination, useTableMaxHeight } from '@hooks';

  import { useUserProfile } from '@stores';

  import {
    OccupiedInnerHeight,
    TicketTypes,
    type TicketTypesStrings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { getCostTimeDisplay, getMenuListSearch } from '@utils';

  import {
    STATUS,
    type STATUS_STRING,
  } from '../common/const';
  import type { ListState } from '../common/types';
  import RedisResultFiles from '../components/RedisResultFiles.vue';
  import { useFetchData } from '../hooks/useFetchData';

  import type { DatePickerValues, TableColumnRender, TableProps } from '@/types/bkui-vue';

  const { t } = useI18n();

  // 可查看结果文件类型
  const includesResultFiles: TicketTypesStrings[] = [TicketTypes.REDIS_KEYS_EXTRACT, TicketTypes.REDIS_KEYS_DELETE];
  const state = reactive<ListState>({
    isLoading: false,
    isAnomalies: false,
    data: [],
    ticketTypes: [],
    pagination: useDefaultPagination(),
    filter: {
      daterange: initDate(),
      searchValues: [],
    },
  });
  const isSearching = computed(() => {
    const { daterange, searchValues } = state.filter;
    return daterange.filter(item => item).length > 0 || searchValues.length > 0;
  });
  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.WITH_PAGINATION);
  const userProfileStore = useUserProfile();
  // 默认过滤当前用户
  const { username } = userProfileStore;
  if (username) {
    state.filter.searchValues.push({
      id: 'created_by',
      name: t('执行人'),
      values: [{ id: username, name: username }],
    });
  }

  // 列表操作方法
  const { fetchTaskflow, handeChangeLimit, handeChangePage } = useFetchData(state);
  const columns: TableProps['columns'] = [{
    label: 'ID',
    field: 'root_id',
    fixed: 'left',
    width: 240,
    showOverflowTooltip: false,
    render: ({ cell, data }: TableColumnRender) => (
      <div class="text-overflow" v-overflow-tips>
        <a href="javascript:" onClick={handleToDetails.bind(null, data)}>{ cell }</a>
      </div>
    ),
  }, {
    label: t('任务类型'),
    field: 'ticket_type_display',
  }, {
    label: t('状态'),
    field: 'status',
    render: ({ cell }: { cell: STATUS_STRING }) => {
      const themes: Partial<Record<STATUS_STRING, string>> = {
        RUNNING: 'loading',
        CREATED: 'default',
        FINISHED: 'success',
      };
      return <DbStatus type="linear" theme={themes[cell] || 'danger'}>{t(STATUS[cell])}</DbStatus>;
    },
  }, {
    label: t('关联单据'),
    field: 'uid',
    render: ({ cell }: TableColumnRender) => <bk-button text theme="primary" onClick={handleToTicket.bind(null, cell)}>{ cell }</bk-button>,
  }, {
    label: t('执行人'),
    field: 'created_by',
  }, {
    label: t('执行时间'),
    field: 'created_at',
  }, {
    label: t('耗时'),
    field: 'cost_time',
    render: ({ cell }: { cell: number }) => getCostTimeDisplay(cell),
  }, {
    label: t('操作'),
    field: 'operation',
    fixed: 'right',
    minWidth: 210,
    render: ({ data }: { data: TaskflowItem }) => (
      <div class="table-operations"><bk-button class="mr-8" text theme="primary" onClick={handleToDetails.bind(null, data)}>{ t('查看详情') }</bk-button>
        {
          includesResultFiles.includes(data.ticket_type) && data.status === 'FINISHED'
            ? <bk-button text theme="primary" onClick={handleShowResultFiles.bind(null, data.root_id)}>{ t('查看结果文件') }</bk-button>
            : null
        }
      </div>
    ),
  }];

  const searchData = computed(() => [{
    name: 'ID',
    id: 'root_id',
  }, {
    name: t('任务类型'),
    id: 'ticket_type__in',
    multiple: true,
    children: state.ticketTypes,
  }, {
    name: t('状态'),
    id: 'status__in',
    multiple: true,
    children: Object.keys(STATUS).map((id: string) => ({
      id,
      name: t(STATUS[id as STATUS_STRING]),
    })),
  }, {
    name: t('关联单据'),
    id: 'uid',
  }, {
    name: t('执行人'),
    id: 'created_by',
  }]);

  async function getMenuList(item: ISearchItem | undefined, keyword: string) {
    if (item?.id !== 'created_by' && keyword) {
      return getMenuListSearch(item, keyword, searchData.value, state.filter.searchValues);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (state.filter.searchValues || []).map(value => value.id);
      return searchData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'created_by') {
      return await fetchUseList(keyword);
    }

    // 不需要远层加载
    return searchData.value.find(set => set.id === item.id)?.children;
  }

  /**
   * 近 7 天
   */
  function initDate() {
    const end = new Date();
    const start = new Date();
    start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
    return ['', ''];
  }

  // 获取单据类型
  function fetchTicketTypes() {
    return getTicketTypes().then((res) => {
      state.ticketTypes = res.map(item => ({
        id: item.key,
        name: item.value,
      }));
      return state.ticketTypes;
    });
  }
  fetchTicketTypes();

  /**
   * 获取人员列表
   */
  function fetchUseList(fuzzyLookups: string) {
    if (!fuzzyLookups) return [];

    return getUseList({ fuzzy_lookups: fuzzyLookups }).then(res => res.results.map(item => ({
      id: item.username,
      name: item.username,
    })));
  }

  const handleClearSearch = () => {
    state.filter.searchValues = [];
    state.filter.daterange = ['', ''];
    handeChangePage(1);
  };

  /**
   * change filter date
   */
  const handleChangeDate = () => {
    nextTick(() => {
      handeChangePage(1);
    });
  };

  /**
   * 查看详情
   */
  const router = useRouter();
  const handleToDetails = (row: TaskflowItem) => {
    router.push({
      name: 'DatabaseMissionDetails',
      params: {
        root_id: row.root_id,
      },
    });
  };

  /**
   * 跳转到关联单据
   */
  const handleToTicket = (id: string) => {
    const url = router.resolve({
      name: 'SelfServiceMyTickets',
      query: { filterId: id },
    });
    window.open(url.href, '_blank');
  };

  /** 查看结果文件功能 */
  const resultFileState = reactive({
    isShow: false,
    rootId: '',
  });
  function handleShowResultFiles(id: string) {
    resultFileState.isShow = true;
    resultFileState.rootId = id;
  }
</script>


<style lang="less" scoped>
  @import "@/styles/mixins.less";

  .history-mission {
    &__operations {
      .flex-center();

      padding-bottom: 16px;
    }
  }
</style>
