<template>
  <BkLoading
    class="cluster-host-table"
    :loading="isLoading">
    <div ref="tableWrapper">
      <PrimaryTable
        ref="table"
        :data="dataList"
        :ellipsis="false"
        :filter-row="(null as any)"
        :filter-value="quickSearchValue"
        :max-height="tableMaxHeight"
        row-key="id"
        title-ellipsis
        @change="handleFilterChange">
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
              :model-value="Boolean(rowSelectMemo[row.bk_host_id])"
              @change="handleSelectionChange(row)" />
          </template>
        </TableColumn>
        <slot />
        <template #empty>
          <EmptyStatus
            :is-anomalies="false"
            :is-searching="isSearching"
            @clear-search="handleClearSearch"
            @refresh="fetchRefresh" />
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
  </BkLoading>
</template>
<script setup lang="tsx">
  import type { UnwrapRef, VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { DBTypes } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { getOffset, transfromDataToQuery } from '@utils';

  import { useStorage } from '@vueuse/core';

  import { useFetchData, useHostSearchSelect } from './hooks';

  type IRowData = ServiceReturnType<ReturnType<typeof useClusterMachineList>>['results'][number];

  interface Props {
    dataSource: ReturnType<typeof useClusterMachineList>;
    dbType: DBTypes;
    selectable?: boolean;
  }

  interface Emits {
    <T extends IRowData>(e: 'selection', data: T[]): void;
    <T extends IRowData>(e: 'request-success', data: T[]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    selectable: true,
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    default: () => VNode;
  }>();

  const { t } = useI18n();
  const paginationLimitCache = useStorage('table_pagination_limit', 20);
  const { quickSearchValue } = useHostSearchSelect(props.dbType);

  const {
    dataList,
    fetchHostList,
    loading: isLoading,
    pagination,
  } = useFetchData(props.dataSource, {
    onSuccess(hostList: IRowData[]) {
      emits('request-success', hostList);
    },
  });

  let isInited = false;

  const table = ref();

  const rootRef = useTemplateRef('tableWrapper');
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const isWholeChecked = ref(false);
  const isCurrentPageAllSelected = ref(false);
  const rowSelectMemo = ref<Record<number, IRowData>>({});

  const isSearching = computed(() => Object.keys(quickSearchValue.value).length > 0);
  const selectedCount = computed(() => Object.keys(rowSelectMemo.value).length);

  const fetchData = () => {
    fetchHostList(transfromDataToQuery(quickSearchValue.value));
  };

  const triggerSelection = () => {
    emits('selection', Object.values(rowSelectMemo.value));
  };

  watch([quickSearchValue], () => {
    // 第一次请求不重置页码
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
      dataList.value.every((item) => rowSelectMemo.value[item.bk_host_id]);
  });

  watch(dataList, () => {
    if (dataList.value.length < 1) {
      return;
    }
  });

  const handleSelectionChange = (data: IRowData) => {
    const rowSelect = { ...rowSelectMemo.value };
    if (rowSelectMemo.value[data.bk_host_id]) {
      delete rowSelect[data.bk_host_id];
    } else {
      rowSelect[data.bk_host_id] = data;
    }
    rowSelectMemo.value = rowSelect;
    isWholeChecked.value = false;
    triggerSelection();
  };

  const handlePageSelect = () => {
    const rowSelect: UnwrapRef<typeof rowSelectMemo> = {};
    dataList.value.forEach((item) => {
      rowSelect[item.bk_host_id] = item;
    });
    rowSelectMemo.value = rowSelect;
    triggerSelection();
    isWholeChecked.value = false;
  };

  const handleTogglePageSelect = (checked: boolean) => {
    const rowSelect = { ...rowSelectMemo.value };
    dataList.value.forEach((item) => {
      if (checked) {
        rowSelect[item.bk_host_id] = item;
      } else {
        delete rowSelect[item.bk_host_id];
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
          rowSelect[item.bk_host_id] = item;
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

  onMounted(() => {
    tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 80;
  });

  defineExpose({
    fetchData() {
      fetchData();
    },
    getData() {
      return dataList.value;
    },
    resetSelection() {
      rowSelectMemo.value = {};
      triggerSelection();
    },
  });
</script>
<style lang="less">
  .cluster-host-table {
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
