<template>
  <BkLoading
    class="ticket-table-mode"
    :loading="isLoading">
    <div ref="tableWrapper">
      <BkTable
        :data="dataList"
        :max-height="tableMaxHeight"
        :pagination="pagination"
        remote-pagination
        :row-class="rowClass"
        :show-overflow="false"
        @page-limit-change="handlePageLimitChange"
        @page-value-change="handlePageValueChange">
        <template
          v-if="Object.keys(rowSelectMemo).length > 0"
          #prepend>
          <div style="display: flex; justify-content: center; height: 30px; background: #ebecf0; align-items: center">
            <I18nT keypath="已选n条，">
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
          :label="renderSelectionColumnHead"
          :min-width="80"
          :width="80">
          <template #default="{ row }: { row: IRowData}">
            <BkCheckbox
              label
              :model-value="Boolean(rowSelectMemo[row.id])"
              @change="handleSelectionChange(row)" />
          </template>
        </BkTableColumn>
        <slot name="prepend" />
        <BkTableColumn
          field="bk_biz_id"
          :label="t('业务')"
          :min-width="150">
          <template #default="{ data }: { data: IRowData }">
            {{ data.bk_biz_name }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="ticket_type_display"
          :label="t('单据类型')"
          :min-width="200" />
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
                <RouterLink
                  v-if="flowItem.flow_id"
                  target="_blank"
                  :to="{
                    name: 'taskHistoryDetail',
                    params: {
                      root_id: flowItem.flow_id,
                    },
                  }">
                  {{ flowItem.flow_alias }}
                </RouterLink>
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
          min-width="250">
          <template #default="{ data }: { data: IRowData }">
            <div
              v-if="data.related_object.objects && !isStretchLayoutOpen"
              style="padding: 8px 0; line-height: 20px">
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
                  <I18nT keypath="共n个">
                    {{ data.related_object.objects.length }}
                  </I18nT>
                </BkTag>
              </div>
            </div>
            <template v-else> -- </template>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="status__in"
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
          field="createAtDisplay"
          :label="t('当前处理人')"
          sort
          width="250">
          <template #default="{ data }: { data: IRowData }">
            <BkTag
              v-for="(item, index) in data.todo_operators"
              :key="index">
              {{ item }}
            </BkTag>
            <span v-if="data.todo_operators.length < 1">--</span>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="creator"
          :label="t('申请人')"
          width="250" />
        <BkTableColumn
          field="createAtDisplay"
          :label="t('申请时间')"
          sort
          width="250" />
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
  import { onActivated, shallowRef, useTemplateRef } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRequest } from 'vue-request'

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';
  import {getInnerFlowInfo} from '@services/source/ticketFlow'

  import { useEventBus, useStretchLayout  } from '@hooks';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { getOffset } from '@utils'

  import useDatePicker from './hooks/use-date-picker';
  import useFetchData from './hooks/use-fetch-data';
  import useSearchSelect from './hooks/use-search-select';

  type IRowData = TicketModel<unknown>

  interface Props {
    dataSource: typeof getTickets;
    selectable?: boolean,
    rowClass: (params: TicketModel) => string
  }

  interface Emits {
    (e: 'selection', data: TicketModel<unknown>[]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    selectable: false,
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    prepend?: () => VNode;
    action?: () => VNode;
  }>()

  const { t } = useI18n();
  const eventBus = useEventBus();
  const { isSplited: isStretchLayoutOpen } = useStretchLayout();

  let isInited = false;

  const { value: datePickerValue, formatValue: formatDateValue } = useDatePicker();
  const { loading: isLoading, pagination, fetchTicketList, dataList } = useFetchData(props.dataSource);
  const { value: searchSelectValue, formatSearchValue } = useSearchSelect();

  const rootRef = useTemplateRef('tableWrapper')
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const isWholeChecked = ref(false);
  const isCurrentPageAllSelected = ref(false);
  const rowSelectMemo = ref<Record<number, TicketModel<unknown>>>({});

  const ticketInnerFlowInfo = shallowRef<ServiceReturnType<typeof getInnerFlowInfo>>({})

  const isSearching = computed(
    () =>
      Object.keys(formatSearchValue.value).length > 0 ||
      formatDateValue.value.create_at__gte !== '' ||
      formatDateValue.value.create_at__lte !== '',
  );

  const fetchData = () => {
    fetchTicketList({
      ...formatDateValue.value,
      ...formatSearchValue.value,
    });
  };

  const renderSelectionColumnHead = () => {
    const renderCheckbox = () => {
      if (isWholeChecked.value) {
      return (
        <div class="db-table-whole-check" onClick={handleClearWholeSelect} />
      );
    }
    return (
      <bk-checkbox
        label={true}
        model-value={Object.keys(rowSelectMemo.value).length > 0}
        onChange={handleTogglePageSelect} />
    );
    }
    return (
      <div class="table-selection-head">
        {renderCheckbox()}
        <bk-popover
          placement="bottom-start"
          theme="light ticket-table-select-menu"
          arrow={ false }
          trigger='hover'
          v-slots={{
            default: () => <db-icon class="select-menu-flag" type="down-big" />,
            content: () => (
              <div class="select-menu">
                <div class="item" onClick={handlePageSelect}>{t('本页全选')}</div>
                <div class="item" onClick={handleWholeSelect}>{t('跨页全选')}</div>
              </div>
            ),
          }}>
        </bk-popover>
      </div>
    )
  }

  const {run: fetchInnerFlowInfo} = useRequest(getInnerFlowInfo, {
    manual: true,
    onSuccess(data) {
      ticketInnerFlowInfo.value = data
    }
  })
  const triggerSelection = () => {
    emits('selection', Object.values(rowSelectMemo.value));
  }

  const { pause: pauseFetchData, resume: resumeFetchData } = watch([formatDateValue, formatSearchValue], () => {
    if (!isInited){
      isInited = true;
    } else {
      pagination.current = 1;
    }

    fetchData();
  });

  watch(() => [dataList, rowSelectMemo], () => {
    isCurrentPageAllSelected.value = dataList.value.every((item) => rowSelectMemo.value[item.id]);
  })

  const {pause: pauseFetchInnerFlowInfo, resume: resumeFetchInnerFlowInfo } = watch(dataList, () => {
    if (dataList.value.length < 1){
      return
    }
    fetchInnerFlowInfo({
      ticket_ids: dataList.value.map(item => item.id).join(',')
    })
  })

  const handleSelectionChange = (data: IRowData) => {
    const rowSelect = { ...rowSelectMemo.value }
    if (rowSelectMemo.value[data.id]){
      delete rowSelect[data.id];
    } else {
      rowSelect[data.id] = data;
    }
    rowSelectMemo.value = rowSelect;
    triggerSelection();
  }

  const handlePageSelect = () => {
    const rowSelect = { ...rowSelectMemo.value }
    dataList.value.forEach((item) => {
      rowSelectMemo.value[item.id] = item;
    })
    rowSelectMemo.value = rowSelect;
    triggerSelection();
  }

  const handleTogglePageSelect = (checked: boolean) => {
    const rowSelect = { ...rowSelectMemo.value }
    dataList.value.forEach((item) => {
      if (checked){
        rowSelect[item.id] = item;
      } else {
        delete rowSelect[item.id]
      }
    })
    rowSelectMemo.value = rowSelect;
    triggerSelection();
  }

  const handleWholeSelect = () => {
    const rowSelect = { ...rowSelectMemo.value }
    props.dataSource({
      ...formatDateValue.value,
      ...formatSearchValue.value,
      limit: -1
    }).then(result => {
      result.results.forEach((item) => {
        rowSelect[item.id] = item;
      })
      rowSelectMemo.value = rowSelect;
      triggerSelection();
    })
  }

  const handleClearWholeSelect = () => {
    rowSelectMemo.value = {}
    triggerSelection();
  }

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
    searchSelectValue.value = []
    datePickerValue.value = ['', '']
  }

  const fetchRefresh = () => {
    rowSelectMemo.value = {}
    triggerSelection();
    fetchData();
  }

  onActivated(() => {
    resumeFetchData();
    resumeFetchInnerFlowInfo();
    eventBus.on('refreshTicketStatus', fetchRefresh);
  })

  onDeactivated(() => {
    pauseFetchData();
    pauseFetchInnerFlowInfo();
    eventBus.off('refreshTicketStatus', fetchRefresh);
  })

  onMounted(() => {
    tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 20
  })

  defineExpose({
    fetchData(){
      fetchData()
    },
    resetSelection(){
      rowSelectMemo.value = {}
      triggerSelection();
    }
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
