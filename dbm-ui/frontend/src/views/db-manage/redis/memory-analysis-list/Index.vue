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
  <div class="redis-memory-analysis-list">
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
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        parse-url
        style="width: 550px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="queryKeystatRecords"
      :filter-value="quickSearchValue"
      releate-url-query
      row-key="record_id"
      @filter-change="handleFilterChange">
      <TableColumn
        col-key="root_id"
        fixed="left"
        :min-width="180"
        :title="t('任务 ID')">
        <template #default="{ row }: { row : RedisKeystatAnalysisModel }">
          <div
            v-if="row.root_id"
            class="hot-key-task-id">
            <BkButton
              text
              theme="primary"
              @click="handleShowDetail(row)">
              {{ row.root_id }}
            </BkButton>
            <BkButton
              v-bk-tooltips="t('跳转查看任务')"
              class="link-icon ml-4"
              text
              theme="primary"
              @click="handleToTaskDetail(row)">
              <DbIcon type="link" />
            </BkButton>
          </div>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="immute_domain"
        :filter="tableFilter?.['immute_domain']"
        :min-width="200"
        :title="t('所属集群')">
        <template #default="{ row }: { row : RedisKeystatAnalysisModel }">
          <BkButton
            text
            theme="primary"
            @click="handleToClusterList(row)">
            {{ row.immute_domain }}
          </BkButton>
        </template>
      </TableColumn>
      <TableColumn
        col-key="ins_list"
        :filter="tableFilter?.['instance_addresses']"
        min-width="200"
        :show-overflow="false"
        :title="t('目标实例')">
        <template #default="{ row }: { row: RedisKeystatAnalysisModel }">
          <div
            v-if="row.source_addr_list"
            style="line-height: 20px">
            <div
              v-for="item in row.source_addr_list.slice(0, 6)"
              :key="item.addr">
              {{ item.addr }}
            </div>
            <div v-if="row.source_addr_list.length > 6">
              <span>...</span>
              <BkTag
                v-bk-tooltips="{
                  content: row.source_addr_list.map((item) => item.addr).join('\n'),
                }"
                class="ml-4"
                size="small">
                <I18nT
                  keypath="共n个"
                  scope="global">
                  {{ row.source_addr_list.length }}
                </I18nT>
              </BkTag>
            </div>
          </div>
          <template v-if="row.source_addr_list.length < 1"> -- </template>
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :filter="tableFilter?.['status']"
        :title="t('任务状态')"
        :width="120">
        <template #default="{ row }: { row : RedisKeystatAnalysisModel }">
          <DbStatus
            :theme="row.statusTheme"
            type="linear">
            {{ row.statusText }}
          </DbStatus>
        </template>
      </TableColumn>
      <TableColumn
        col-key="creator"
        :filter="tableFilter?.['creator']"
        :title="t('创建人')"
        :width="150">
      </TableColumn>
      <TableColumn
        col-key="ticket_id"
        :filter="tableFilter?.['ticket_id']"
        :title="t('关联单据')"
        :width="100">
        <template #default="{ row }: { row : RedisKeystatAnalysisModel }">
          <BkButton
            text
            theme="primary"
            @click="handleGoTicketDetail(row)">
            {{ row.ticket_id }}
          </BkButton>
        </template>
      </TableColumn>
      <TableColumn
        col-key="create_at"
        :filter="tableFilter?.['create_at']"
        :title="t('提单时间')"
        :width="180">
        <template #default="{ row }: { row : RedisKeystatAnalysisModel }">
          {{ row.createAtDisplay }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="operations"
        fixed="right"
        :title="t('操作')"
        :width="100">
        <template #default="{ row }: { row : RedisKeystatAnalysisModel }">
          <template v-if="row.status === 'FINISHED'">
            <BkButton
              text
              theme="primary"
              @click="handleShowDetail(row)">
              {{ t('查看') }}
            </BkButton>
            <BkButton
              class="ml-12"
              text
              theme="primary"
              @click="handleExport(row)">
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
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import RedisKeystatAnalysisModel from '@services/model/redis/redis-keystat-analysis';
  import { exportKeystatAnalysis, queryKeystatRecords } from '@services/source/redisKeystat';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { getBusinessHref, transfromDataToQuery } from '@utils';

  import Detail from './components/detail/Index.vue';
  import useSearchSelect from './useSearchSelect';
  import useTableFilter from './useTableFilter';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { quickSearchData, quickSearchValue } = useSearchSelect();
  const tableFilter = useTableFilter();

  const tableRef = useTemplateRef('tableRef');

  const isDetailShow = ref(false);
  const currentDetailIndex = ref(0);

  // const selected = shallowRef<RedisKeystatAnalysisModel[]>([]);
  const recordList = shallowRef<RedisKeystatAnalysisModel[]>([]);

  const handleQuickSearchChange = () => {
    fetchTableData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchTableData();
  };

  const fetchTableData = () => {
    tableRef.value!.fetchData(transfromDataToQuery(quickSearchValue.value));
  };

  // const handleSelection = (key: any, list: Record<number, RedisKeystatAnalysisModel>[]) => {
  //   selected.value = list as unknown as RedisKeystatAnalysisModel[];
  // };

  const handleShowDetail = (data: RedisKeystatAnalysisModel) => {
    if (data.status !== 'FINISHED') {
      return;
    }
    isDetailShow.value = true;
    recordList.value = tableRef
      .value!.getData<RedisKeystatAnalysisModel>()
      .filter((item) => item.status === 'FINISHED');
    currentDetailIndex.value = recordList.value.findIndex((item) => item.record_id === data.record_id);
  };

  const handleGoTicketDetail = (data: RedisKeystatAnalysisModel) => {
    const { href } = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: data.ticket_id,
      },
    });

    window.open(getBusinessHref(href), '_blank');
  };

  const handleToClusterList = (data: RedisKeystatAnalysisModel) => {
    const routeName = data.cluster_type === ClusterTypes.REDIS_INSTANCE ? 'DatabaseRedisHaList' : 'DatabaseRedisList';
    const { href } = router.resolve({
      name: routeName,
      query: {
        domain: data.immute_domain,
      },
    });

    window.open(getBusinessHref(href), '_blank');
  };

  const handleToTaskDetail = (row: RedisKeystatAnalysisModel) => {
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

  // const handleExport = (row?: RedisKeystatAnalysisModel) => {
  //   const data = row ? [row] : selected.value;
  //   exportHotKeyAnalysis({ record_ids: data.map((item) => item.id).join(',') }).then(() => {
  //     tableRef.value!.clearSelected();
  //   });
  // };

  const handleExport = (row: RedisKeystatAnalysisModel) => {
    exportKeystatAnalysis({ record_ids: `${row.record_id}` });
  };

  onMounted(() => {
    fetchTableData();
  });
</script>

<style lang="less">
  .redis-memory-analysis-list {
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
