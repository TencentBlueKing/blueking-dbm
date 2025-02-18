<template>
  <BkLoading
    class="ticket-table-mode"
    :loading="isLoading">
    <div ref="tableWrapper">
      <BkTable
        :data="dataList"
        :max-height="tableMaxHeight"
        :pagination="pagination"
        :row-class="rowClass"
        :row-config="{
          useKey: true,
          keyField: 'id',
        }"
        :show-overflow="false"
        @filter-change="handleFilterChange"
        @page-limit-change="handlePageLimitChange"
        @page-value-change="handlePageValueChange"
        @sort-change="handleSortChange">
        <template
          v-if="Object.keys(rowSelectMemo).length > 0"
          #prepend>
          <div style="display: flex; justify-content: center; height: 30px; background: #ebecf0; align-items: center">
            <I18nT
              keypath="已选n条，"
              scope="global">
              <span class="number">{{ Object.keys(rowSelectMemo).length }}</span>
            </I18nT>
            <BkButton
              text
              theme="primary"
              @click="handleClearWholeSelect">
              {{ t('清除所有勾选') }}
            </BkButton>
          </div>
        </template>
        <BkTableColumn
          v-if="selectable"
          fixed="left"
          :min-width="80"
          :width="80">
          <template #header>
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
                      class="item"
                      @clilck="handlePageSelect">
                      {{ t('本页全选') }}
                    </div>
                    <div
                      class="item"
                      @clilck="handleWholeSelect">
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
        </BkTableColumn>
        <BkTableColumn
          field="id"
          fixed="left"
          :label="t('单号')"
          width="100">
          <template #default="{ data }: { data: IRowData }">
            <AuthRouterLink
              action-id="ticket_view"
              :permission="data.permission.ticket_view"
              :resource="data.id"
              target="_blank"
              :to="{
                name: 'ticketDetail',
                params: {
                  ticketId: data.id,
                },
              }"
              @click="(event: MouseEvent) => handleGoDetail(data, event)">
              {{ data.id }}
            </AuthRouterLink>
          </template>
        </BkTableColumn>
        <BkTableColumn
          v-if="!excludeColumn.includes('bk_biz_id')"
          field="bk_biz_id"
          :filter-multiple="false"
          :filters="searchFieldMap['bk_biz_id']"
          :label="t('业务')"
          :min-width="150">
          <template #default="{ data }: { data: IRowData }">
            {{ data.bk_biz_name }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="ticket_type__in"
          filter-multiple
          :filters="searchFieldMap['ticket_type__in']"
          :label="t('单据类型')"
          :min-width="200">
          <template #default="{ data }: { data: IRowData }">
            {{ data.ticket_type_display }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="ticket_type_display"
          :label="t('子任务')"
          :min-width="200">
          <template #default="{ data }: { data: IRowData }">
            <template v-if="ticketInnerFlowInfo[data.id]">
              <div
                v-for="(flowItem, index) in ticketInnerFlowInfo[data.id]"
                :key="index"
                style="line-height: 26px">
                <BkButton
                  text
                  theme="primary"
                  @click="() => handleGoTaskHistoryDetail(data, flowItem)">
                  {{ flowItem.flow_alias }}
                </BkButton>
              </div>
              <span v-if="ticketInnerFlowInfo[data.id].length < 1">--</span>
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
        </BkTableColumn>
        <BkTableColumn
          field="related_object"
          :label="t('集群')"
          min-width="250"
          :show-overflow="false">
          <template #default="{ data }: { data: IRowData }">
            <div
              v-if="data.related_object.objects && !isStretchLayoutOpen"
              style="line-height: 20px">
              <div
                v-for="item in data.related_object.objects.slice(0, 6)"
                :key="item">
                {{ item }}
              </div>
              <div v-if="data.related_object.objects.length > 6">
                <span>...</span>
                <BkTag
                  v-bk-tooltips="{
                    content: data.related_object.objects.join('\n'),
                  }"
                  class="ml-4"
                  size="small">
                  <I18nT
                    keypath="共n个"
                    scope="global">
                    {{ data.related_object.objects.length }}
                  </I18nT>
                </BkTag>
              </div>
            </div>
            <template v-if="data.related_object.objects.length < 1"> -- </template>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="status"
          filter-multiple
          :filters="searchFieldMap['status']"
          :label="t('单据状态')"
          :min-width="100">
          <template #default="{ data }: { data: IRowData }">
            <TicketStatusTag
              v-if="data"
              :data="data" />
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="remark"
          :label="t('备注')"
          :min-width="250">
          <template #default="{ data }: { data: IRowData }">
            <span>{{ data.remark || '--' }}</span>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="todo_operators"
          :label="t('当前处理人')"
          width="160">
          <template #default="{ data }: { data: IRowData }">
            <TagBlock
              copyenable
              :data="data.todo_operators" />
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="todo_helpers"
          :label="t('当前协助人')"
          width="250">
          <template #default="{ data }: { data: IRowData }">
            <TagBlock
              copyenable
              :data="data.todo_helpers" />
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="creator"
          :label="t('申请人')"
          width="150" />
        <BkTableColumn
          field="create_at"
          :label="t('申请时间')"
          sort
          width="250">
          <template #default="{ data }: { data: IRowData }">
            {{ data.createAtDisplay || '--' }}
          </template>
        </BkTableColumn>
        <slot name="action" />
        <template #empty>
          <EmptyStatus
            :is-anomalies="false"
            :is-searching="isSearching"
            @clear-search="handleClearSearch"
            @refresh="fetchRefresh" />
        </template>
      </BkTable>
    </div>
  </BkLoading>
</template>
<script setup lang="tsx">
  import { getCurrentInstance, onActivated, shallowRef, useTemplateRef, type VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';
  import { getInnerFlowInfo } from '@services/source/ticketFlow';

  import { useEventBus, useStretchLayout, useUrlSearch } from '@hooks';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TagBlock from '@components/tag-block/Index.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { getBusinessHref, getOffset } from '@utils';

  import { type VxeTableDefines } from '@blueking/vxe-table';

  import useDatePicker from './hooks/use-date-picker';
  import useFetchData from './hooks/use-fetch-data';
  import useSearchSelect from './hooks/use-search-select';

  type IRowData = TicketModel<unknown>;

  interface Props {
    dataSource: typeof getTickets;
    selectable?: boolean;
    rowClass: (params: TicketModel) => string;
    excludeColumn?: string[];
  }

  interface Emits {
    (e: 'selection', data: TicketModel<unknown>[]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    selectable: false,
    excludeColumn: () => [],
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    prepend?: () => VNode;
    action?: () => VNode;
  }>();

  const router = useRouter();
  const { t } = useI18n();
  const eventBus = useEventBus();
  const { isSplited: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const { value: datePickerValue, formatValue: formatDateValue } = useDatePicker();
  const { loading: isLoading, pagination, fetchTicketList, dataList, ordering } = useFetchData(props.dataSource);
  const { value: searchSelectValue, formatSearchValue, searchFieldMap } = useSearchSelect();

  const currentInstance = getCurrentInstance();
  const { getSearchParams } = useUrlSearch();

  let isInited = false;

  const rootRef = useTemplateRef('tableWrapper');
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const isWholeChecked = ref(false);
  const isCurrentPageAllSelected = ref(false);
  const rowSelectMemo = ref<Record<number, TicketModel>>({});

  const ticketInnerFlowInfo = shallowRef<ServiceReturnType<typeof getInnerFlowInfo>>({});

  const isSearching = computed(
    () =>
      Object.keys(formatSearchValue.value).length > 0 ||
      Boolean(formatDateValue.value.create_at__gte) ||
      Boolean(formatDateValue.value.create_at__lte),
  );

  const fetchData = () => {
    fetchTicketList({
      ...formatDateValue.value,
      ...formatSearchValue.value,
    });
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

  const { pause: pauseFetchData, resume: resumeFetchData } = watch([formatDateValue, formatSearchValue], () => {
    if (!isInited) {
      isInited = true;
    } else {
      pagination.current = 1;
    }

    fetchData();
  });

  watch(
    () => [dataList, rowSelectMemo],
    () => {
      isCurrentPageAllSelected.value = dataList.value.every((item) => rowSelectMemo.value[item.id]);
    },
  );

  const { pause: pauseFetchInnerFlowInfo, resume: resumeFetchInnerFlowInfo } = watch(dataList, () => {
    if (dataList.value.length < 1) {
      return;
    }
    fetchInnerFlowInfo({
      ticket_ids: dataList.value.map((item) => item.id).join(','),
    });
  });

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
    const rowSelect = { ...rowSelectMemo.value };
    dataList.value.forEach((item) => {
      rowSelectMemo.value[item.id] = item;
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
        ...formatDateValue.value,
        ...formatSearchValue.value,
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

  const handleSortChange = (payload: { field: string; order: string }) => {
    ordering.value = payload.order === 'desc' ? payload.field : `-${payload.field}`;
    fetchData();
  };

  const handleFilterChange = (payload: VxeTableDefines.FilterChangeEventParams) => {
    const result = payload.filterList.map((item) => {
      const nameMap = item.column.filters.reduce<Record<string, string>>(
        (result, item) =>
          Object.assign(result, {
            [item.value]: item.label,
          }),
        {},
      );
      return {
        id: item.field,
        name: item.column.title,
        values: item.values.map((valueItem) => ({
          id: valueItem,
          name: nameMap[valueItem],
        })),
      };
    });

    searchSelectValue.value = result;
  };

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    fetchData();
  };

  // 切换页码
  const handlePageValueChange = (pageValue: number) => {
    pagination.current = pageValue;
    fetchData();
  };

  const handleClearSearch = () => {
    searchSelectValue.value = [];
    datePickerValue.value = ['', ''];
  };

  const fetchRefresh = () => {
    rowSelectMemo.value = {};
    triggerSelection();
    fetchData();
  };

  const handleGoDetail = (ticketData: TicketModel, event: MouseEvent) => {
    if (event.ctrlKey || event.metaKey) {
      return true;
    }

    event.preventDefault();
    event.stopPropagation();
    stretchLayoutSplitScreen();
    setTimeout(() => {
      if (currentInstance!.isUnmounted) {
        return;
      }
      router.replace({
        params: {
          ticketId: ticketData.id,
        },
        query: getSearchParams(),
      });
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

  onActivated(() => {
    resumeFetchData();
    resumeFetchInnerFlowInfo();
    eventBus.on('refreshTicketStatus', fetchRefresh);
  });

  onDeactivated(() => {
    pauseFetchData();
    pauseFetchInnerFlowInfo();
    eventBus.off('refreshTicketStatus', fetchRefresh);
  });

  onMounted(() => {
    tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 20;
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
  }

  [data-theme~='ticket-table-select-menu'] {
    padding: 0 !important;

    .select-menu {
      padding: 5px 0;

      .item {
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
