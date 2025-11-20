<template>
  <BkLoading
    class="ticket-table-mode"
    :loading="isLoading">
    <div ref="tableWrapper">
      <PrimaryTable
        :key="tableKey"
        ref="table"
        :bk-ui-settings="tableSettings"
        :data="dataList"
        :ellipsis="false"
        :filter-row="(null as any)"
        :filter-value="quickSearchValue"
        :max-height="tableMaxHeight"
        resizable
        :row-class-name="rowClass"
        row-key="id"
        title-ellipsis
        @bk-ui-settings-change="handleDisplayColumnsChange"
        @change="handleFilterChange"
        @sort-change="handleSortChange">
        <TableColumn
          v-if="selectable"
          col-key="row-select"
          fixed="left"
          :min-width="80"
          :width="80">
          <template #title>
            <div class="table-selection-head">
              <div
                v-if="isWholeChecked"
                class="db-table-whole-check"
                @click="handleClearWholeSelect" />
              <template v-else>
                <BkCheckbox
                  v-if="isCurrentPageAllSelected"
                  key="page"
                  label
                  model-value
                  @change="handleTogglePageSelect" />
                <BkCheckbox
                  v-else
                  key="all"
                  @change="handleWholeSelect" />
              </template>
              <BkPopover
                :arrow="false"
                placement="bottom-start"
                theme="light ticket-table-select-menu"
                trigger="hover">
                <DbIcon
                  class="select-menu-flag"
                  type="down-big" />
                <template #content>
                  <div class="select-menu">
                    <div
                      class="select-menu-item"
                      :class="{ 'is-selected': isCurrentPageAllSelected }"
                      @click="handlePageSelect">
                      {{ t('本页全选') }}
                    </div>
                    <div
                      class="select-menu-item"
                      :class="{ 'is-selected': isWholeChecked }"
                      @click="handleWholeSelect">
                      {{ t('跨页全选') }}
                    </div>
                  </div>
                </template>
              </BkPopover>
            </div>
          </template>
          <template #default="{ row }: { row: IRowData}">
            <BkCheckbox
              label
              :model-value="Boolean(rowSelectMemo[row.id])"
              @change="handleSelectionChange(row)" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="ids"
          :filter="tableFilter['ids']"
          fixed="left"
          :title="t('单号')"
          width="100">
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
          v-if="!excludeColumn.includes('bk_biz_id')"
          col-key="bk_biz_ids"
          :filter="excludeFilterField.includes('bk_biz_ids') ? undefined : tableFilter['bk_biz_ids']"
          :min-width="150"
          :title="t('业务')">
          <template #default="{ row }: { row: IRowData }">
            {{ row.bk_biz_name }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="ticket_type_search"
          :filter="tableFilter['ticket_type_search']"
          :min-width="200"
          :title="t('单据类型')">
          <template #default="{ row }: { row: IRowData }">
            {{ row.ticket_type_display }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="ticket_type_display"
          :min-width="200"
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
          col-key="cluster"
          :filter="tableFilter['cluster']"
          min-width="300"
          :title="t('集群')">
          <template #default="{ row }: { row: IRowData }">
            <div
              v-if="row.related_object.objects"
              style="line-height: 20px">
              <div
                v-for="item in row.related_object.objects.slice(0, 6)"
                :key="item">
                {{ item }}
              </div>
              <div v-if="row.related_object.objects.length > 6">
                <span>...</span>
                <BkTag
                  v-bk-tooltips="{
                    content: row.related_object.objects.join('\n'),
                  }"
                  class="ml-4"
                  size="small">
                  <I18nT
                    keypath="共n个"
                    scope="global">
                    {{ row.related_object.objects.length }}
                  </I18nT>
                </BkTag>
              </div>
            </div>
            <template v-if="row.related_object.objects.length < 1"> -- </template>
          </template>
        </TableColumn>
        <TableColumn
          col-key="status"
          :filter="excludeFilterField.includes('status') ? undefined : tableFilter['status']"
          :min-width="140"
          :title="t('单据状态')">
          <template #default="{ row }: { row: IRowData }">
            <TicketStatusTag
              v-if="row"
              :data="row" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="remark"
          :filter="tableFilter['remark']"
          :min-width="250"
          :title="t('备注')">
          <template #default="{ row }: { row: IRowData }">
            <span>{{ row.remark || '--' }}</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="todo_operators"
          :title="t('当前处理人')"
          width="160">
          <template #default="{ row }: { row: IRowData }">
            <TagBlock
              copyenable
              :data="row.todo_operators" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="todo_helpers"
          :title="t('当前协助人')"
          width="250">
          <template #default="{ row }: { row: IRowData }">
            <TagBlock
              copyenable
              :data="row.todo_helpers" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="creator__in"
          :filter="tableFilter['creator__in']"
          :title="t('申请人')"
          width="150">
          <template #default="{ row }: { row: IRowData }">
            {{ row.creator || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="create_at"
          :filter="tableFilter['create_at']"
          sorter
          :title="t('申请时间')"
          width="250">
          <template #default="{ row }: { row: IRowData }">
            {{ row.createAtDisplay || '--' }}
          </template>
        </TableColumn>
        <slot name="action" />
        <template #empty>
          <EmptyStatus
            :is-anomalies="false"
            :is-searching="isSearching"
            @clear-search="handleClearSearch"
            @refresh="fetchRefresh" />
        </template>
        <template #bkUiAppearanceSettings>
          <div>
            <div class="mb-8">{{ t('详情打开方式') }}</div>
            <BkRadioGroup
              v-model="viewMode"
              style="display: flex">
              <BkRadioButton
                label="drawer"
                style="flex: 1">
                {{ t('抽屉侧滑') }}
              </BkRadioButton>
              <BkRadioButton
                label="jump"
                style="flex: 1">
                {{ t('新窗口') }}
              </BkRadioButton>
            </BkRadioGroup>
          </div>
        </template>
      </PrimaryTable>
      <div class="table-footer">
        <BkPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          @change="handlePageValueChange"
          @limit-change="handlePageLimitChange">
          <template
            v-if="selectedCount > 0"
            #limitAppend>
            <I18nT
              class="ml-8"
              keypath="已选择n条"
              scope="global"
              tag="span">
              <span class="number">{{ selectedCount }}</span>
            </I18nT>
          </template>
        </BkPagination>
      </div>
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
  </BkLoading>
</template>
<script setup lang="tsx">
  import { type TableSort } from 'tdesign-vue-next';
  import { onBeforeUnmount, shallowRef, type UnwrapRef, useTemplateRef, type VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';
  import { getInnerFlowInfo } from '@services/source/ticketFlow';

  import { useEventBus, useUrlSearch } from '@hooks';

  import { useUserProfile } from '@stores';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TagBlock from '@components/tag-block/Index.vue';
  import TicketDetail from '@components/ticket-detail/index.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { getBusinessHref, getOffset, transfromDataToQuery } from '@utils';

  import { useStorage } from '@vueuse/core';

  import useFetchData from '../hooks/use-fetch-data';
  import useSearchSelect from '../hooks/use-search-select';

  import useTableFilter from './use-table-filter';

  type IRowData = TicketModel<unknown>;

  interface Props {
    dataSource: typeof getTickets;
    excludeColumn?: string[];
    excludeFilterField?: string[];
    selectable?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    excludeColumn: () => [],
    excludeFilterField: () => [],
    selectable: false,
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    action?: () => VNode;
    prepend?: () => VNode;
  }>();

  type Emits = (e: 'selection', data: TicketModel<unknown>[]) => void;

  const TABLE_SETTING_KEY = 'TICKET_TABLE_SETTINGS_v1';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();
  const eventBus = useEventBus();
  const paginationLimitCache = useStorage('table_pagination_limit', 20);
  const userProfileStore = useUserProfile();
  const tableFilter = useTableFilter();

  const { dataList, fetchTicketList, loading: isLoading, ordering, pagination } = useFetchData(props.dataSource);
  const { quickSearchValue } = useSearchSelect();

  const { getSearchParams } = useUrlSearch();

  let isInited = false;

  const table = ref();

  const rootRef = useTemplateRef('tableWrapper');
  const tableKey = ref(Date.now().toString());
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const isWholeChecked = ref(false);
  const isCurrentPageAllSelected = ref(false);
  const rowSelectMemo = ref<Record<number, TicketModel>>({});
  const ticketId = ref<number>();
  const isShowDetail = ref(false);
  const ticketInnerFlowInfo = shallowRef<ServiceReturnType<typeof getInnerFlowInfo>>({});
  const viewMode = ref<'drawer' | 'jump'>(userProfileStore.profile[TABLE_SETTING_KEY]?.view_mode || 'drawer');

  const tableSettings = ref({
    checked: userProfileStore.profile[TABLE_SETTING_KEY]?.checked,
    disabled: ['ids', 'ticket_type__in'],
    size: userProfileStore.profile[TABLE_SETTING_KEY]?.size || 'small',
  });

  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);
  const selectedCount = computed(() => Object.keys(rowSelectMemo.value).length);

  const rowClass = ({ row }: { row: TicketModel<unknown> }) => {
    return row.id === ticketId.value ? 'select-row' : '';
  };

  const fetchData = () => {
    fetchTicketList(transfromDataToQuery(quickSearchValue.value));
    tableKey.value = Date.now().toString();
  };

  const { run: fetchInnerFlowInfo } = useRequest(getInnerFlowInfo, {
    manual: true,
    onSuccess(data) {
      ticketInnerFlowInfo.value = data;
    },
  });
  const triggerSelection = () => {
    emits('selection', Object.values(rowSelectMemo.value));
  };

  watch([quickSearchValue], () => {
    // 第一次请求不充值页码
    if (!isInited) {
      isInited = true;
    } else {
      pagination.current = 1;
    }

    if (props.selectable) {
      handleClearWholeSelect();
    }
    fetchData();
  });

  watch([dataList, rowSelectMemo], () => {
    isCurrentPageAllSelected.value =
      !isWholeChecked.value &&
      dataList.value.length > 0 &&
      dataList.value.every((item) => rowSelectMemo.value[item.id]);
  });

  watch(dataList, () => {
    if (dataList.value.length < 1) {
      return;
    }
    fetchInnerFlowInfo({
      ticket_ids: dataList.value.map((item) => item.id).join(','),
    });
  });

  const handleDisplayColumnsChange = (payload: { columns: string[]; fontSize: string; rowSize: string }) => {
    userProfileStore.updateProfile({
      label: TABLE_SETTING_KEY,
      values: {
        checked: payload.columns,
        fontSize: payload.fontSize,
        rowSize: payload.rowSize,
        view_mode: viewMode.value,
      },
    });
  };

  const handleSelectionChange = (data: IRowData) => {
    const rowSelect = { ...rowSelectMemo.value };
    if (rowSelectMemo.value[data.id]) {
      delete rowSelect[data.id];
    } else {
      rowSelect[data.id] = data;
    }
    rowSelectMemo.value = rowSelect;
    isWholeChecked.value = false;
    triggerSelection();
  };

  const handlePageSelect = () => {
    const rowSelect: UnwrapRef<typeof rowSelectMemo> = {};
    dataList.value.forEach((item) => {
      rowSelect[item.id] = item;
    });
    rowSelectMemo.value = rowSelect;
    triggerSelection();
    isWholeChecked.value = false;
  };

  const handleTogglePageSelect = (checked: boolean) => {
    const rowSelect = { ...rowSelectMemo.value };
    dataList.value.forEach((item) => {
      if (checked) {
        rowSelect[item.id] = item;
      } else {
        delete rowSelect[item.id];
      }
    });
    rowSelectMemo.value = rowSelect;
    isWholeChecked.value = false;
    triggerSelection();
  };

  const handleWholeSelect = () => {
    const rowSelect = { ...rowSelectMemo.value };
    props
      .dataSource({
        ...transfromDataToQuery(quickSearchValue.value),
        limit: -1,
      })
      .then((result) => {
        result.results.forEach((item) => {
          rowSelect[item.id] = item;
        });
        rowSelectMemo.value = rowSelect;
        isWholeChecked.value = true;
        triggerSelection();
      });
  };

  const handleClearWholeSelect = () => {
    rowSelectMemo.value = {};
    isWholeChecked.value = false;
    triggerSelection();
  };

  const handleSortChange = (payload: TableSort) => {
    if (Array.isArray(payload)) {
      return;
    }
    if (payload) {
      ordering.value = payload.descending ? payload.sortBy : `-${payload.sortBy}`;
    } else {
      ordering.value = '';
    }

    fetchData();
  };

  const handleFilterChange = (payload: { filter?: Record<string, any> }) => {
    if (!payload.filter) {
      return;
    }

    quickSearchValue.value = Object.keys(payload.filter).reduce((result, key) => {
      const valueItem = payload.filter![key];
      Object.assign(result, {
        [key]: Array.isArray(valueItem) ? valueItem.join(',') : valueItem,
      });
      return result;
    }, {});
  };

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    paginationLimitCache.value = pageLimit;
    fetchData();
  };

  // 切换页码
  const handlePageValueChange = (pageValue: number) => {
    pagination.current = pageValue;
    fetchData();
  };

  const handleClearSearch = () => {
    quickSearchValue.value = {};
  };

  const fetchRefresh = () => {
    rowSelectMemo.value = {};
    triggerSelection();
    fetchData();
  };

  const handleGoDetail = (ticketData: TicketModel, event: MouseEvent) => {
    if (event.ctrlKey || event.metaKey || viewMode.value === 'jump') {
      return true;
    }

    event.preventDefault();
    event.stopPropagation();

    ticketId.value = ticketData.id;
    isShowDetail.value = true;
    router.replace({
      params: {
        ticketId: ticketData.id,
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
    router.replace({
      params: {
        ticketId: 0,
      },
      query: getSearchParams(),
    });
  };

  onMounted(() => {
    tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 80;
    eventBus.on('refreshTicketStatus', fetchRefresh);

    if (Number(route.params.ticketId)) {
      ticketId.value = Number(route.params.ticketId);
      isShowDetail.value = true;
    }
  });

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', fetchRefresh);
  });

  defineExpose({
    fetchData() {
      fetchData();
    },
    resetSelection() {
      rowSelectMemo.value = {};
      triggerSelection();
    },
  });
</script>
<style lang="less">
  .ticket-table-mode {
    .table-selection-head {
      position: relative;
      display: flex;
      align-items: center;

      .db-table-whole-check {
        position: relative;
        display: inline-block;
        width: 16px;
        height: 16px;
        vertical-align: middle;
        cursor: pointer;
        background-color: #fff;
        border: 1px solid #3a84ff;
        border-radius: 2px;

        &::after {
          position: absolute;
          top: 1px;
          left: 4px;
          width: 4px;
          height: 8px;
          border: 2px solid #3a84ff;
          border-top: 0;
          border-left: 0;
          content: '';
          transform: rotate(45deg);
        }
      }

      .select-menu-flag {
        margin-left: 4px;
        font-size: 18px;
        color: #63656e;
      }
    }

    .select-row {
      td {
        background: #ebf2ff !important;
      }
    }

    .table-footer {
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

  [data-theme~='ticket-table-select-menu'] {
    padding: 0 !important;

    .select-menu {
      padding: 5px 0;

      .select-menu-item {
        padding: 0 10px;
        font-size: 12px;
        line-height: 26px;
        cursor: pointer;

        &:hover {
          color: #3a84ff;
          background-color: #eaf3ff;
        }

        &.is-selected {
          color: #3a84ff;
          background-color: #f4f6fa;
        }
      }
    }
  }
</style>
