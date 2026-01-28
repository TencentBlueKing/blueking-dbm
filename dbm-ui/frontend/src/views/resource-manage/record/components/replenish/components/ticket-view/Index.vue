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
        :placeholder="t('搜索单号，单据状态，申请人，申请时间')"
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
        :title="t('单号')">
        <template #default="{ row }: { row: IRowData }">
          <AuthRouterLink
            action-id="ticket_view"
            :permission="row.permission.ticket_view"
            :resource="row.id"
            target="_blank"
            :to="{
              name: 'ticketDetail',
              params: {
                ticketId: row.id,
              },
            }"
            @click="(event: MouseEvent) => handleGoDetail(row, event)">
            {{ row.id }}
          </AuthRouterLink>
        </template>
      </TableColumn>
      <TableColumn
        col-key="ticket_type__in"
        :min-width="120"
        :title="t('子任务')">
        <template #default="{ row }: { row: IRowData }">
          <template v-if="ticketInnerFlowInfo[row.id]">
            <div
              v-for="(flowItem, index) in ticketInnerFlowInfo[row.id]"
              :key="index"
              style="line-height: 26px">
              <BkButton
                text
                theme="primary"
                @click="() => handleGoTaskHistoryDetail(row, flowItem)">
                {{ flowItem.flow_alias }}
              </BkButton>
            </div>
            <span v-if="ticketInnerFlowInfo[row.id]!.length < 1">--</span>
          </template>
          <div
            v-else
            class="rotate-loading"
            style="display: inline-block">
            <DbIcon
              svg
              type="sync-pending" />
          </div>
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :min-width="120"
        :title="t('状态')">
        <template #default="{ row }: { row: IRowData }">
          <TicketStatusTag
            v-if="row"
            :data="row" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="record_id"
        :min-width="120"
        :title="t('补货操作 ID')">
        <template #default="{ row }: { row: IRowData }">
          {{ row?.record_id || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="db_type"
        :min-width="120"
        :title="t('DB 类型')">
        <template #default="{ row }: { row: IRowData }">
          {{ dbNameMap[row?.db_type] || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="spec.spec_machine_type"
        :min-width="120"
        :title="t('规格类型')">
        <template #default="{ row }: { row: IRowData }">
          {{ machineTypeMap[row?.spec?.spec_machine_type] || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="spec.spec_name"
        :min-width="180"
        :title="t('规格')">
        <template #default="{ row }: { row: IRowData }">
          {{ row?.spec?.spec_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="city"
        :min-width="120"
        :title="t('地域')">
        <template #default="{ row }: { row: IRowData }">
          {{ row?.city || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="subzone"
        :min-width="120"
        :title="t('园区')">
        <template #default="{ row }: { row: IRowData }">
          {{ row?.subzone || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="os_name"
        :min-width="120"
        :title="t('操作系统')">
        <template #default="{ row }: { row: IRowData }">
          {{ row?.os_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="count"
        :min-width="120"
        :title="t('申请数量')">
        <template #default="{ row }: { row: IRowData }">
          <span class="bold-number">{{ row?.count || 0 }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="apply_count"
        :min-width="120"
        :title="t('已交付')">
        <template #default="{ row }: { row: IRowData }">
          <span
            class="bold-number"
            :class="{
              'green-number': row?.delivery_count === row?.apply_count,
              'red-number': row?.delivery_count < row?.apply_count,
            }">
            {{ row?.delivery_count || 0 }}
          </span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="creator"
        :min-width="150"
        :title="t('申请人')">
        <template #default="{ row }: { row: IRowData }">
          <span>{{ row?.operator || '--' }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="create_at"
        :min-width="220"
        :title="t('申请时间')">
        <template #default="{ row }: { row: IRowData }">
          <span>{{ row.create_at ? utcDisplayTime(row.create_at) : '--' }}</span>
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
    <TableDetailDialog
      v-model="isShowDetail"
      :default-offset-left="300"
      :min-width="900"
      @close="handleDetailDialogClose">
      <TicketDetail
        v-if="ticketId"
        :ticket-id="ticketId" />
    </TableDetailDialog>
  </div>
</template>
<script setup lang="tsx">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { listTicketApplyInfo } from '@services/source/dbresourceReplenish';
  import { getInnerFlowInfo } from '@services/source/ticketFlow';

  import { useUrlSearch } from '@hooks';

  import { DBTypeInfos } from '@common/const';

  import TicketDetail from '@components/ticket-detail/index.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { getBusinessHref, getOffset, utcDisplayTime } from '@utils';

  import ViewController from '../common/ViewController.vue';

  import useFetchData from './hooks/use-fetch-data';
  import useSearchSelect from './hooks/use-search-select';

  interface IRowData extends TicketModel {
    apply_count: number;
    city: string;
    count: number;
    create_at: string;
    db_type: string;
    delivery_count: number;
    operator: string;
    os_name: string;
    record_id: number;
    spec: {
      spec_machine_type: string;
      spec_name: string;
    };
    subzone: string;
  }

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const rootRef = useTemplateRef('tableWrapper');
  const { getSearchParams } = useUrlSearch();

  const { quickSearchData, quickSearchValue } = useSearchSelect();

  const {
    dataList,
    fetchData,
    handlePageLimitChange,
    handlePageValueChange,
    loading: isLoading,
    pagination,
  } = useFetchData();

  const dbNameMap: Record<string, string> = {};
  const machineTypeMap: Record<string, string> = {};
  Object.values(DBTypeInfos).forEach((db) => {
    dbNameMap[db.id] = db.name;
    db.machineList.forEach((machine) => {
      machineTypeMap[`${machine.value}`] = `${machine.label}`;
    });
  });

  const URL_REPLENISH_MEMO_KEY = '__replenish_ticket_view_payload__';

  const filterDateRange = ref<[string, string]>([
    dayjs().subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
    dayjs().format('YYYY-MM-DD HH:mm:ss'),
  ]);
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const ticketId = ref<number>();
  const isShowDetail = ref(false);
  const ticketInnerFlowInfo = shallowRef<ServiceReturnType<typeof getInnerFlowInfo>>({});
  const tableData = shallowRef<IRowData[]>([]);

  const handleGoDetail = (ticketData: TicketModel, event: MouseEvent) => {
    if (event.ctrlKey || event.metaKey) {
      return true;
    }

    event.preventDefault();
    event.stopPropagation();

    ticketId.value = ticketData.id;
    isShowDetail.value = true;
    router.replace({
      params: {
        id: ticketData.id,
      },
      query: getSearchParams(),
    });
    return false;
  };

  const handleGoTaskHistoryDetail = (
    ticketData: TicketModel,
    data: ServiceReturnType<typeof getInnerFlowInfo>[number][number],
  ) => {
    const { href } = router.resolve({
      name: 'taskHistoryDetail',
      params: {
        root_id: data.flow_id,
      },
    });

    window.open(getBusinessHref(href, ticketData.bk_biz_id));
  };

  const handleDetailDialogClose = () => {
    ticketId.value = 0;
  };

  const handleDateRangeChange = (value: [string, string]) => {
    filterDateRange.value = value;
  };

  watch(dataList, () => {
    if (dataList.value.length < 1) {
      ticketInnerFlowInfo.value = {};
      tableData.value = [];
      return;
    }
    const ticketIds = dataList.value.map((item) => item.id).join(',');

    Promise.all([getInnerFlowInfo({ ticket_ids: ticketIds }), listTicketApplyInfo({ ticket_ids: ticketIds })]).then(
      ([innerFlowInfo, applyInfo]) => {
        // 更新子任务信息
        ticketInnerFlowInfo.value = innerFlowInfo;

        tableData.value = dataList.value.map((item) => {
          const applyInfoItem = applyInfo[item.id];
          return Object.assign(item, applyInfoItem, applyInfoItem.details);
        });
      },
    );
  });

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
      ticketId.value = Number(route.params.id);
      isShowDetail.value = true;
      urlParams.ids = route.params.id;
    }
    if (urlParams?.ids) {
      filterDateRange.value = ['', '']; // 从“补货操作视角”跳转时因为带了过滤字段ids，需要去掉时间区间
    }
    quickSearchValue.value = urlParams;
  });
</script>
