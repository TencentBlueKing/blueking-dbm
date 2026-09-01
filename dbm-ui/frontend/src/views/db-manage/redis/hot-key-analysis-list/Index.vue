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
  <div class="redis-hot-key-analysis-list">
    <div class="header-action">
      <!-- <span
        v-bk-tooltips="{
          disabled: selected.length > 0,
          content: t('请选择任务'),
        }">
        <BkButton
          :disabled="selected.length === 0"
          @click="() => handleExport()">
          {{ t('批量导出') }}
        </BkButton>
      </span> -->
      <BkDatePicker
        v-model="daterange"
        :placeholder="t('选择日期范围')"
        style="width: 350px; margin-left: auto"
        type="datetimerange"
        @change="fetchTableData" />
      <DbQuickSearch
        v-model="searchValue"
        class="ml-8"
        :data="searchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="queryAnalysisRecords"
      :filter-value="searchValue"
      releate-url-query
      row-key="id"
      @clear-search="handleClearSearch"
      @filter-change="handleFilterChange">
      <TableColumn
        col-key="root_id"
        fixed="left"
        :min-width="180"
        :title="t('任务 ID')">
        <template #default="{ row: data }: { row: RedisHotKeyAnalysisModel }">
          <div
            v-if="data.root_id"
            class="hot-key-task-id">
            <BkButton
              text
              theme="primary"
              @click="handleShowDetail(data)">
              {{ data.root_id }}
            </BkButton>
            <BkButton
              v-bk-tooltips="t('跳转查看任务')"
              class="link-icon ml-4"
              text
              theme="primary"
              @click="handleToTaskDetail(data)">
              <DbIcon type="link" />
            </BkButton>
          </div>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="ins_list"
        min-width="200"
        :show-overflow="false"
        :title="t('目标实例')">
        <template #default="{ row: data }: { row: RedisHotKeyAnalysisModel }">
          <div
            v-if="data.ins_list"
            style="line-height: 20px">
            <div
              v-for="item in data.ins_list.slice(0, 6)"
              :key="item">
              {{ item }}
            </div>
            <div v-if="data.ins_list.length > 6">
              <span>...</span>
              <BkTag
                v-bk-tooltips="{
                  content: data.ins_list.join('\n'),
                }"
                class="ml-4"
                size="small">
                <I18nT
                  keypath="共n个"
                  scope="global">
                  {{ data.ins_list.length }}
                </I18nT>
              </BkTag>
            </div>
          </div>
          <template v-if="data.ins_list.length < 1"> -- </template>
        </template>
      </TableColumn>
      <TableColumn
        col-key="immute_domain"
        :min-width="200"
        :title="t('所属集群')">
        <template #default="{ row: data }: { row: RedisHotKeyAnalysisModel }">
          <BkButton
            text
            theme="primary"
            @click="handleToClusterList(data)">
            {{ data.immute_domain }}
          </BkButton>
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :filter="{
          list: statusFilterList,
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :title="t('任务状态')"
        :width="120">
        <template #default="{ row: data }: { row: RedisHotKeyAnalysisModel }">
          <DbStatus
            :theme="data.statusTheme"
            type="linear">
            {{ t(data.statusText) }}
          </DbStatus>
        </template>
      </TableColumn>
      <TableColumn
        col-key="analysis_time"
        :title="t('分析时长')"
        :width="80">
        <template #default="{ row: data }: { row: RedisHotKeyAnalysisModel }">
          {{ `${data.analysis_time}s` }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="creator"
        :title="t('创建人')"
        :width="150"></TableColumn>
      <TableColumn
        col-key="ticket_id"
        :title="t('关联单据')"
        :width="100">
        <template #default="{ row: data }: { row: RedisHotKeyAnalysisModel }">
          <BkButton
            text
            theme="primary"
            @click="handleGoTicketDetail(data)">
            {{ data.ticket_id }}
          </BkButton>
        </template>
      </TableColumn>
      <TableColumn
        col-key="createAtDisplay"
        :title="t('开始时间')"
        :width="180"></TableColumn>
      <TableColumn
        col-key="updateAtDisplay"
        :title="t('结束时间')"
        :width="180"></TableColumn>
      <TableColumn
        col-key="operations"
        fixed="right"
        :title="t('操作')"
        :width="100">
        <template #default="{ row: data }: { row: RedisHotKeyAnalysisModel }">
          <template v-if="data.status === 'FINISHED'">
            <BkButton
              text
              theme="primary"
              @click="handleShowDetail(data)">
              {{ t('查看') }}
            </BkButton>
            <BkButton
              class="ml-12"
              text
              theme="primary"
              @click="handleExport(data)">
              {{ t('导出') }}
            </BkButton>
          </template>
          <template v-else>--</template>
        </template>
      </TableColumn>
    </DbTable>
    <Detail
      v-model:current-index="currentDetailIndex"
      v-model:is-show="isDetailShow"
      :record-list="recordList"
      @refresh="fetchTableData" />
  </div>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import RedisHotKeyAnalysisModel from '@services/model/redis/redis-hot-key-analysis';
  import { exportHotKeyAnalysis, queryAnalysisRecords } from '@services/source/redisAnalysis';
  import { getUserList } from '@services/source/user';

  import { ClusterTypes } from '@common/const';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { getBusinessHref, transfromDataToQuery } from '@utils';

  import Detail from './components/detail/Index.vue';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const searchValue = ref<Record<string, string>>({});

  const statusFilterList = Object.keys(RedisHotKeyAnalysisModel.STATUS_TEXT_MAP).map((id) => ({
    label: t(RedisHotKeyAnalysisModel.STATUS_TEXT_MAP[id]),
    value: id,
  }));

  /**
   * 近 15 天
   */
  const initDate = () => {
    if (route.query.from) {
      return ['', ''] as [string, string];
    }
    return [dayjs().subtract(15, 'day').toDate(), dayjs().toDate()] as [Date, Date];
  };

  const tableRef = useTemplateRef('tableRef');

  const isDetailShow = ref(false);
  const currentDetailIndex = ref(0);
  const daterange = ref(initDate());

  // const selected = shallowRef<RedisHotKeyAnalysisModel[]>([]);
  const recordList = shallowRef<RedisHotKeyAnalysisModel[]>([]);

  const searchData = computed(
    () =>
      [
        {
          id: 'instance_addresses',
          name: t('目标实例'),
          type: 'multiple-input',
        },
        {
          id: 'immute_domain',
          name: t('所属集群'),
          type: 'multiple-input',
        },
        {
          id: 'status',
          list: statusFilterList,
          name: t('任务状态'),
          type: 'multiple',
        },
        {
          id: 'operator',
          name: t('创建人'),
          remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
            const requestParams = {};
            if (params.defaultValue) {
              Object.assign(requestParams, { exact_lookups: params.defaultValue });
            }
            if (params.keyword) {
              Object.assign(requestParams, { fuzzy_lookups: params.keyword });
            }

            return getUserList(requestParams).then((data) =>
              data.results.map((item) => ({
                label: item.username,
                value: item.username,
              })),
            );
          },
          remoteSearch: true,
          type: 'multiple',
        },
      ] as QuickSearchProps['data'],
  );

  const fetchTableData = () => {
    const dateParams =
      daterange.value.filter((item) => item).length === 0
        ? {}
        : {
            create_at__gte: dayjs(daterange.value[0]).format('YYYY-MM-DD HH:mm:ss'),
            create_at__lte: dayjs(daterange.value[1]).format('YYYY-MM-DD HH:mm:ss'),
          };
    tableRef.value!.fetchData({
      ...dateParams,
      ...transfromDataToQuery(searchValue.value),
    });
  };

  const handleSearchValueChange = () => {
    fetchTableData();
  };

  // const handleSelection = (key: any, list: Record<number, RedisHotKeyAnalysisModel>[]) => {
  //   selected.value = list as unknown as RedisHotKeyAnalysisModel[];
  // };

  const handleClearSearch = () => {
    daterange.value = ['', ''];
    searchValue.value = {};
    fetchTableData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchTableData();
  };

  const handleShowDetail = (data: RedisHotKeyAnalysisModel) => {
    if (data.status !== 'FINISHED') {
      return;
    }
    isDetailShow.value = true;
    recordList.value = tableRef.value!.getData<RedisHotKeyAnalysisModel>().filter((item) => item.status === 'FINISHED');
    currentDetailIndex.value = recordList.value.findIndex((item) => item.id === data.id);
  };

  const handleGoTicketDetail = (data: RedisHotKeyAnalysisModel) => {
    const { href } = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: data.ticket_id,
      },
    });

    window.open(getBusinessHref(href), '_blank');
  };

  const handleToClusterList = (data: RedisHotKeyAnalysisModel) => {
    const routeName = data.cluster_type === ClusterTypes.REDIS_INSTANCE ? 'DatabaseRedisHaList' : 'DatabaseRedisList';
    const { href } = router.resolve({
      name: routeName,
      query: {
        domain: data.immute_domain,
      },
    });

    window.open(getBusinessHref(href), '_blank');
  };

  const handleToTaskDetail = (row: RedisHotKeyAnalysisModel) => {
    const { href } = router.resolve({
      name: 'taskHistoryDetail',
      params: {
        root_id: row.root_id,
      },
      query: {
        from: route.name as string,
      },
    });

    window.open(getBusinessHref(href), '_blank');
  };

  // const handleExport = (row?: RedisHotKeyAnalysisModel) => {
  //   const data = row ? [row] : selected.value;
  //   exportHotKeyAnalysis({ record_ids: data.map((item) => item.id).join(',') }).then(() => {
  //     tableRef.value!.clearSelected();
  //   });
  // };

  const handleExport = (row: RedisHotKeyAnalysisModel) => {
    exportHotKeyAnalysis({ record_ids: `${row.id}` });
  };
</script>

<style lang="less">
  .redis-hot-key-analysis-list {
    .header-action {
      display: flex;
      padding-bottom: 16px;
    }

    .hot-key-task-id {
      .link-icon {
        display: none;
      }

      &:hover {
        .link-icon {
          display: inline;
        }
      }
    }
  }
</style>
