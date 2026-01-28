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
  <div class="header-action">
    <ViewController />
    <div class="header-filters">
      <DbDateTimePicker
        class="date-time-picker mr-8"
        clearable
        mode="previous"
        :model-value="filterDateRange"
        @change="handleDateRangeChange" />
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        :placeholder="t('搜索 ID，DB 类型，申请人')"
        style="width: 450px" />
    </div>
  </div>
  <div
    ref="tableWrapper"
    class="replenish-record-list">
    <PrimaryTable
      :data="tableData"
      ellipsis
      :loading="isLoading"
      :max-height="tableMaxHeight"
      resizable
      row-key="id"
      title-ellipsis>
      <TableColumn
        col-key="id"
        fixed="left"
        :min-width="80"
        title="ID">
        <template #default="{ row }: { row: IRowData }">
          <BkButton
            text
            theme="primary"
            @click="handleViewDetail(row)">
            {{ row.id }}
          </BkButton>
        </template>
      </TableColumn>
      <TableColumn
        col-key="details"
        :min-width="200"
        :title="t('补货数量')">
        <template #default="{ row }: { row: IRowData }">
          <BkTag
            v-for="[db, value] in Object.entries(row.details).slice(0, MAX_DISPLAY_NUM)"
            :key="db"
            class="mr-4">
            {{ dbNameMap[db] }} : {{ value }}
          </BkTag>
          <BkTag
            v-if="Object.keys(row.details).length > MAX_DISPLAY_NUM"
            v-bk-tooltips="{
              content: Object.entries(row.details)
                .slice(MAX_DISPLAY_NUM)
                .map(([db, value]) => `${dbNameMap[db]} : ${value}`)
                .join(', '),
              placement: 'top',
            }"
            class="mr-4">
            {{ `+${Object.keys(row.details).length - MAX_DISPLAY_NUM}` }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="creator"
        :min-width="120"
        :title="t('申请人')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.creator || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="create_at"
        :min-width="200"
        :title="t('申请时间')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.create_at ? utcDisplayTime(row.create_at) : '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :min-width="200"
        :title="t('关联单据状态')">
        <template #default="{ row }: { row: IRowData }">
          <div class="ticket-status">
            <div
              v-bk-tooltips="{
                content: generateStatusCount(row.status)
                  .map((item) => `${item.text} ${item.count}`)
                  .join('，'),
                placement: 'top',
                disabled: generateStatusCount(row.status).length <= MAX_DISPLAY_NUM,
              }"
              class="ticket-status-list">
              <span
                v-for="(item, index) in generateStatusCount(row.status)"
                :key="item.text">
                {{ item.text }}
                <span
                  class="bold-number"
                  :style="{ color: item.color }">
                  {{ item.count }}
                </span>
                <span v-if="index < generateStatusCount(row.status).length - 1">，</span>
              </span>
            </div>
            <BkButton
              class="forward-btn"
              text
              theme="primary"
              @click="() => handleForward(row.ticket_ids)">
              <DbIcon
                class="ml-6"
                type="bk-dbm-icon db-icon-link" />
            </BkButton>
          </div>
        </template>
      </TableColumn>
      <TableColumn
        col-key="operate"
        fixed="right"
        :title="t('操作')"
        width="100">
        <template #default="{ row }: { row: IRowData }">
          <BkButton
            text
            theme="primary"
            @click="handleViewDetail(row)">
            {{ t('查看明细') }}
          </BkButton>
        </template>
      </TableColumn>
    </PrimaryTable>
    <div class="table-footer">
      <BkPagination
        v-bind="pagination"
        :layout="['total', 'limit', 'list']"
        @change="handlePageValueChange"
        @limit-change="handlePageLimitChange" />
    </div>
    <Details
      v-if="detailsId"
      :id="detailsId"
      v-model:is-show="isShowDetails" />
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { useUrlSearch } from '@hooks';

  import { DBTypeInfos } from '@common/const';

  import { getOffset, utcDisplayTime } from '@utils';

  import ViewController from '../common/ViewController.vue';

  import Details from './components/Details.vue';
  import useFetchData from './hooks/use-fetch-data';
  import useSearchSelect from './hooks/use-search-select';

  type IRowData = NonNullable<(typeof tableData.value)[0]>;

  const { t } = useI18n();
  const rootRef = useTemplateRef('tableWrapper');

  const route = useRoute();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  const { quickSearchData, quickSearchValue } = useSearchSelect();

  const {
    fetchData,
    handlePageLimitChange,
    handlePageValueChange,
    loading: isLoading,
    pagination,
    tableData,
  } = useFetchData();

  const dbNameMap: Record<string, string> = {};
  const machineTypeMap: Record<string, string> = {};
  Object.values(DBTypeInfos).forEach((db) => {
    dbNameMap[db.id] = db.name;
    db.machineList.forEach((machine) => {
      machineTypeMap[`${machine.value}`] = `${db.name} - ${machine.label}`;
    });
  });

  const MAX_DISPLAY_NUM = 4;

  const URL_REPLENISH_MEMO_KEY = '__replenish_operation_view_payload__';

  const filterDateRange = ref<[string, string]>([
    dayjs().subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
    dayjs().format('YYYY-MM-DD HH:mm:ss'),
  ]);
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const isShowDetails = ref(false);
  const detailsId = ref<number>(0);

  const colorMap = {
    [TicketModel.STATUS_APPROVE]: '#267BCF',
    [TicketModel.STATUS_FAILED]: '#EA3636',
    [TicketModel.STATUS_INNER_TODO]: '#E38B02',
    [TicketModel.STATUS_RESOURCE_REPLENISH]: '#F59500',
    [TicketModel.STATUS_RUNNING]: '#3A84FF',
    [TicketModel.STATUS_SUCCEEDED]: '#2CAF5E',
    [TicketModel.STATUS_TERMINATED]: '#E71818',
    [TicketModel.STATUS_TIMER]: '#3F726F',
    [TicketModel.STATUS_TODO]: '#4D4F56',
  };

  const generateStatusCount = (status: string[]) => {
    return status.reduce<Array<{ color: string; count: number; text: string }>>((acc, curr) => {
      const text = TicketModel.statusTextMap[curr as keyof typeof TicketModel.statusTextMap] || '--';
      const color = colorMap[curr] || '#63656e';
      const existing = acc.find((item) => item.color === color);
      if (existing) {
        existing.count += 1;
      } else {
        acc.push({ color, count: 1, text });
      }
      return acc;
    }, []);
  };

  const handleViewDetail = (data: IRowData) => {
    isShowDetails.value = true;
    detailsId.value = data.id;
    router.replace({
      params: {
        id: data.id,
      },
      query: getSearchParams(),
    });
  };

  const handleDateRangeChange = (value: [string, string]) => {
    filterDateRange.value = value;
  };

  const handleForward = (ticketIds: number[]) => {
    router.push({
      name: 'resourceReplenishRecord',
      params: {
        page: 'ticket-view',
      },
      query: {
        __replenish_ticket_view_payload__: encodeURIComponent(
          JSON.stringify({
            ids: ticketIds.join(','),
          }),
        ),
      },
    });
  };

  watch(
    () => [filterDateRange.value, quickSearchValue.value],
    _.debounce(() => {
      router.replace({
        query: {
          ...getSearchParams(),
          [URL_REPLENISH_MEMO_KEY]: encodeURIComponent(
            JSON.stringify(
              Object.assign(
                {
                  create_at__gte: filterDateRange.value[0] || undefined, // 去除空字符串避免污染url参数
                  create_at__lte: filterDateRange.value[1] || undefined,
                },
                quickSearchValue.value,
              ),
            ),
          ),
        },
      });
      setTimeout(() => {
        fetchData();
      }, 30);
    }, 200),
  );

  onMounted(() => {
    setTimeout(() => {
      tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 80;
    });
    const urlParams = JSON.parse(decodeURIComponent(String(route.query[URL_REPLENISH_MEMO_KEY] || '{}')));
    if (route.params.id) {
      urlParams.id = route.params.id;
      detailsId.value = Number(route.params.id);
      isShowDetails.value = true;
    }
    if (urlParams?.id) {
      filterDateRange.value = ['', '']; // 从“待补货列表”跳转时因为带了ID，需要去掉时间区间
    }
    quickSearchValue.value = urlParams;
  });
</script>
<style lang="less">
  .replenish-record-list {
    .ticket-status {
      display: flex;

      .ticket-status-list {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .forward-btn {
        position: relative;
        top: 0px;
      }
    }
  }
</style>
