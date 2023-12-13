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
        v-model="state.filter.searchValues"
        :data="searchData"
        :get-menu-list="getMenuList"
        :placeholder="$t('ID_任务类型_状态_关联单据')"
        style="width: 500px;"
        @change="fetchTableData" />
      <BkDatePicker
        v-model="state.filter.daterange"
        class="ml-8"
        :placeholder="$t('选择日期范围')"
        style="width: 300px;"
        type="daterange"
        @change="fetchTableData" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="getTaskflow"
      @clear-search="handleClearSearch" />
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

  import { getTaskflow } from '@services/source/taskflow';
  import { getTicketTypes } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';
  import type { TaskflowItem } from '@services/types/taskflow';

  import {
    TicketTypes,
    type TicketTypesStrings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import {
    getCostTimeDisplay,
    getMenuListSearch,
    getSearchSelectorParams,
  } from '@utils';

  import type { ListState } from '../common/types';
  import RedisResultFiles from '../components/RedisResultFiles.vue';

  import type { TableColumnRender } from '@/types/bkui-vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  /**
   * 近 7 天
   */
  const initDate = () => {
    const end = new Date();
    const start = new Date();
    start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
    return [start.toISOString(), end.toISOString()] as [string, string];
  };
  const statusMap = {
    CREATED: '等待执行',
    READY: '等待执行',
    RUNNING: '执行中',
    SUSPENDED: '执行中',
    BLOCKED: '执行中',
    FINISHED: '执行成功',
    FAILED: '执行失败',
    REVOKED: '已终止',
  } as Record<string, string>;

  // 可查看结果文件类型
  const includesResultFiles: TicketTypesStrings[] = [TicketTypes.REDIS_KEYS_EXTRACT, TicketTypes.REDIS_KEYS_DELETE];

  const tableRef = ref();
  const state = reactive<ListState>({
    data: [],
    ticketTypes: [],
    filter: {
      daterange: initDate(),
      searchValues: [],
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
      id: 'ticket_type__in',
      multiple: true,
      children: state.ticketTypes,
    },
    {
      name: t('状态'),
      id: 'status__in',
      multiple: true,
      children: Object.keys(statusMap).map((id: string) => ({
        id,
        name: t(statusMap[id]),
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
      width: 240,
      showOverflowTooltip: false,
      render: ({ cell, data }: TableColumnRender) => (
          <div class="text-overflow" v-overflow-tips>
            <router-link
              to={{
                name: 'taskHistoryDetail',
                params: {
                  root_id: data.root_id,
                },
                query: {
                  from: route.name,
                },
              }}>
              { cell }
            </router-link>
          </div>
        ),
    },
    {
      label: t('任务类型'),
      field: 'ticket_type_display',
      filter: {
        list: state.ticketTypes.map(item => ({
          text: item.name, value: item.name,
        })),
      },
    },
    {
      label: t('状态'),
      field: 'status',
      filter: {
        list: Object.keys(statusMap).map(id => ({
          text: t(statusMap[id]), value: id,
        })),
      },
      render: ({ cell }: { cell: string }) => {
        const themes: Partial<Record<string, string>> = {
          RUNNING: 'loading',
          SUSPENDED: 'loading',
          BLOCKED: 'loading',
          CREATED: 'default',
          READY: 'default',
          FINISHED: 'success',
        };
        const text = statusMap[cell] ? t(statusMap[cell]) : '--';
        return <DbStatus type="linear" theme={themes[cell] || 'danger'}>{text}</DbStatus>;
      },
    },
    {
      label: t('关联单据'),
      field: 'uid',
      render: ({ cell }: TableColumnRender) => (
          <bk-button
            text
            theme="primary"
            onClick={() => handleToTicket(cell)}>
            { cell }
          </bk-button>
        ),
    },
    {
      label: t('执行人'),
      field: 'created_by',
    },
    {
      label: t('执行时间'),
      field: 'created_at',
    },
    {
      label: t('耗时'),
      field: 'cost_time',
      render: ({ cell }: { cell: number }) => getCostTimeDisplay(cell),
    },
    {
      label: t('操作'),
      field: 'operation',
      fixed: 'right',
      minWidth: 210,
      render: ({ data }: { data: TaskflowItem }) => (
        <div class="table-operations">
          <router-link
            to={{
              name: 'taskHistoryDetail',
              params: {
                root_id: data.root_id,
              },
            }}>
            { t('查看详情') }
          </router-link>
          {
            includesResultFiles.includes(data.ticket_type) && data.status === 'FINISHED'
              ? (
                <bk-button
                  text
                  theme="primary"
                  onClick={() => handleShowResultFiles(data.root_id)}>
                  { t('查看结果文件') }
                  </bk-button>
              )
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
    const { daterange, searchValues } = state.filter;
    const dateParams = daterange.filter(item => item).length === 0
      ? {}
      : {
        created_at__gte: format(new Date(daterange[0]), 'yyyy-MM-dd HH:mm:ss'),
        created_at__lte: format(new Date(daterange[1]), 'yyyy-MM-dd HH:mm:ss'),
      };

    tableRef.value.fetchData({
      ...dateParams,
      ...getSearchSelectorParams(searchValues),
    }, {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
  };


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
    state.filter.searchValues = [];
    state.filter.daterange = ['', ''];
    fetchTableData();
  };


  /**
   * 跳转到关联单据
   */
  const handleToTicket = (id: string) => {
    const url = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        id,
      },
    });
    window.open(url.href, '_blank');
  };


  const handleShowResultFiles = (id: string) => {
    resultFileState.isShow = true;
    resultFileState.rootId = id;
  };
</script>


<style lang="less" scoped>
  @import "@/styles/mixins.less";

  .task-history-list-page {
    .header-action {
      display: flex;
      padding-bottom: 16px;
    }
  }
</style>
