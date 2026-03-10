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
  <div class="replenish-record-page">
    <div class="header-action">
      <div class="header-filters">
        <DbQuickSearch
          v-model="quickSearchValue"
          :data="quickSearchData"
          :placeholder="t('ID / DB类型 / 申请人 / 申请时间')"
          style="width: 500px" />
      </div>
      <a
        class="jump-link"
        @click="handleForward">
        <span class="jump-link-text">{{ t('跳转待补货列表') }}</span>
        <DbIcon type="bk-dbm-icon db-icon-right-big" />
      </a>
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
          title="ID"
          width="120">
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
          :title="t('申请人')"
          width="200">
          <template #default="{ row }: { row: IRowData }">
            {{ row.creator || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="create_at"
          :title="t('申请时间')"
          width="300">
          <template #default="{ row }: { row: IRowData }">
            {{ row.create_at ? utcDisplayTime(row.create_at) : '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="status"
          :min-width="300"
          :title="t('关联单据状态')">
          <template #default="{ row }: { row: IRowData }">
            <div class="ticket-status-summary">
              <span
                v-for="item in generateStatusCount(row.status)"
                :key="item.text"
                class="ticket-status-item"
                :class="`ts-${item.statusKey}`">
                <span class="ts-dot" />
                {{ item.text }} {{ item.count }}
              </span>
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
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { useUrlSearch } from '@hooks';

  import { DBTypeInfos } from '@common/const';

  import { getOffset, utcDisplayTime } from '@utils';

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
  Object.values(DBTypeInfos).forEach((db) => {
    dbNameMap[db.id] = db.name;
  });

  const MAX_DISPLAY_NUM = 4;

  const URL_REPLENISH_MEMO_KEY = '__replenish_operation_view_payload__';

  const tableMaxHeight = ref<number | 'auto'>('auto');
  const isShowDetails = ref(false);
  const detailsId = ref<number>(0);

  const statusKeyMap: Record<string, string> = {
    [TicketModel.STATUS_APPROVE]: 'running',
    [TicketModel.STATUS_FAILED]: 'failed',
    [TicketModel.STATUS_INNER_TODO]: 'pending',
    [TicketModel.STATUS_RESOURCE_REPLENISH]: 'pending',
    [TicketModel.STATUS_RUNNING]: 'running',
    [TicketModel.STATUS_SUCCEEDED]: 'success',
    [TicketModel.STATUS_TERMINATED]: 'terminated',
    [TicketModel.STATUS_TIMER]: 'pending',
    [TicketModel.STATUS_TODO]: 'pending',
  };

  const generateStatusCount = (status: string[]) => {
    return status.reduce<Array<{ count: number; statusKey: string; text: string }>>((acc, curr) => {
      const text = TicketModel.statusTextMap[curr as keyof typeof TicketModel.statusTextMap] || '--';
      const statusKey = statusKeyMap[curr] || 'pending';
      const existing = acc.find((item) => item.statusKey === statusKey);
      if (existing) {
        existing.count += 1;
      } else {
        acc.push({ count: 1, statusKey, text });
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

  const handleForward = () => {
    router.push({
      name: 'resourcePool',
      params: {
        page: 'replenish-list',
      },
    });
  };

  watch(
    () => quickSearchValue.value,
    _.debounce(() => {
      router.replace({
        query: {
          ...getSearchParams(),
          [URL_REPLENISH_MEMO_KEY]: encodeURIComponent(JSON.stringify(quickSearchValue.value)),
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
    quickSearchValue.value = urlParams;
  });
</script>
<style lang="less">
  .replenish-record-page {
    .bk-radio-button-label {
      font-size: 12px;
      line-height: 20px;
      display: flex;
      align-items: center;
    }

    .header-action {
      display: flex;
      align-items: center;
      padding-bottom: 16px;
      gap: 12px;
    }

    .header-filters {
      display: flex;
      align-items: center;

      .date-time-picker {
        width: 320px !important;
      }
    }

    .jump-link {
      margin-left: auto;
      font-size: 13px;
      color: #3a84ff;
      cursor: pointer;
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 4px;

      .jump-link-text:hover {
        text-decoration: underline;
      }

      .db-icon-youjiantou {
        font-size: 12px;
      }
    }

    .replenish-record-list {
      font-family: MicrosoftYaHei;
      background: #fff;
      box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);

      .bold-number {
        font-family: MicrosoftYaHei-Bold;
        font-weight: 700;
        font-size: 12px;
        color: #4d4f56;
        letter-spacing: 0;
        line-height: 20px;
        margin: 0px 2px;
      }

      .green-number {
        color: #2caf5e;
      }

      .red-number {
        color: #ea3636;
      }

      .table-footer {
        padding: 14px 16px;
        position: relative;
        z-index: 1;
        display: flex;
        height: 60px;
        padding: 0 16px;
        margin-top: -1px;
        background: #fff;
        border-top: 1px solid var(--td-component-border);
        align-items: center;

        .bk-pagination {
          width: 100%;

          & > .is-last {
            margin-left: auto;
          }
        }
      }
    }

    .ticket-status-summary {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;

      .ticket-status-item {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        white-space: nowrap;

        .ts-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
        }

        &.ts-failed {
          color: #ea3636;

          .ts-dot {
            background: #ea3636;
          }
        }

        &.ts-running {
          color: #3a84ff;

          .ts-dot {
            background: #3a84ff;
          }
        }

        &.ts-pending {
          color: #ff9c01;

          .ts-dot {
            background: #ff9c01;
          }
        }

        &.ts-success {
          color: #2dcb56;

          .ts-dot {
            background: #2dcb56;
          }
        }

        &.ts-terminated {
          color: #979ba5;

          .ts-dot {
            background: #979ba5;
          }
        }
      }
    }
  }
</style>
