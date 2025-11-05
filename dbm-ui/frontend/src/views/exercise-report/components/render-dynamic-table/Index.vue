<template>
  <BkLoading
    class="render-dynamic-table"
    :loading="loading">
    <CollapseCard>
      <template #title>
        <div class="title-operate-main">
          <div class="title-main">
            <span style="font-weight: 700">{{ tableName }}</span>
            <span class="ml-6 mr-2">(</span>
            <span>{{ t('正常') }}</span>
            <span class="ml-4 mr-4">:</span>
            <span style="font-weight: 700; color: #2caf5e">{{ stateCountsMap.normal }}</span>
            <span class="ml-4 mr-4">,</span>
            <span>{{ t('异常') }}</span>
            <span class="ml-4 mr-4">:</span>
            <span style="font-weight: 700; color: #ea3636">{{ stateCountsMap.abnormal }}</span>
            <span class="ml-2">)</span>
          </div>
          <DbQuickSearch
            :key="renderSearchKey"
            v-model="searchValue"
            class="search-select-main"
            :data="searchSelectData"
            :placeholder="placeholder"
            unique-select
            value-split-code="," />
        </div>
      </template>
      <PrimaryTable
        v-model:filter-value="filterValue"
        class="dynamic-table-main"
        :data="tableData"
        :max-height="485"
        :pagination="pagination"
        resizable
        @filter-change="handleFilterChange"
        @page-change="handlePageChange"
        @sort-change="handleSortChange">
        <template #empty>
          <slot name="empty">
            <BkException
              :description="t('搜索结果为空')"
              scene="part"
              type="empty" />
          </slot>
        </template>
        <TableColumn
          v-for="(item, index) in titleList"
          :key="index"
          :col-key="item.name"
          ellipsis
          ellipsis-title
          :filter="item.filterList"
          resizable
          :sorter="item.ordering"
          :title="item.display_name"
          :width="columnWidthMap[item.name] || 120">
          <template #default="{ row }: { row: ReportInfo['results'][number] }">
            <DbStatus
              v-if="item.format === 'status' && item.name === 'state'"
              :theme="getStateTheme(row[item.name]!)">
              {{ getStateText(row[item.name]!)}}
            </DbStatus>
            <a
              v-else-if="item.format === 'link'"
              :href="row[item.name]"
              target="_blank">
              {{ row[item.name] }}
            </a>
            <span v-else-if="item.format === 'time'">{{ utcDisplayTime(row[item.name]) }}</span>
            <span v-else-if="item.filter?.type === 'biz'">
              {{ bizIdMap.get(row[item.name])?.name || row[item.name] }}
            </span>
            <span v-else>{{ row[item.name] || '--' }}</span>
          </template>
        </TableColumn>
      </PrimaryTable>
    </CollapseCard>
  </BkLoading>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getReport } from '@services/source/report';

  import { useGlobalBizs } from '@stores';

  import CollapseCard from '@components/collapse-card/Index.vue';
  import DbStatus from '@components/db-status/index.vue';

  import { utcDisplayTime } from '@utils';

  import { useTableData } from './hooks/useTableData';

  export interface Props {
    searchParams: Record<string, any>;
    serviceUrl: string;
  }

  interface Exposes {
    getExportExcelSheetData: () => Promise<{
      colWidthList: { wch: number }[];
      dataList: string[][];
      fileName: string;
      headerList: string[];
    }>;
  }

  export type ReportInfo = ServiceReturnType<typeof getReport>;

  const props = defineProps<Props>();

  const { locale, t } = useI18n();
  const { bizIdMap } = useGlobalBizs();

  const placeholder = computed(() => {
    const split = locale.value === 'en' ? ',' : '、';
    return `${t('搜索')}${searchSelectData.value.map((item) => item.name).join(split)}`;
  });

  const {
    columnWidthMap,
    filterValue,
    handleFilterChange,
    handlePageChange,
    handleSortChange,
    loading,
    pagination,
    renderSearchKey,
    searchSelectData,
    searchValue,
    stateCountsMap,
    tableData,
    tableName,
    titleList,
  } = useTableData(props);

  const getStateTheme = (state: string) => {
    let theme = 'default';
    switch (state) {
      case 'abnormal':
        theme = 'danger';
        break;
      case 'warning':
        theme = 'warning';
        break;
      case 'normal':
        theme = 'success';
        break;
      default:
        break;
    }
    return theme;
  };

  const getStateText = (state: string) => {
    let text = '--';
    switch (state) {
      case 'abnormal':
        text = t('异常');
        break;
      case 'warning':
        text = t('预警');
        break;
      case 'normal':
        text = t('正常');
        break;
      default:
        break;
    }
    return text;
  };

  defineExpose<Exposes>({
    async getExportExcelSheetData() {
      const {
        name: fileName,
        results,
        title,
      } = await getReport(
        props.serviceUrl,
        {
          limit: -1,
          offset: 0,
          ...searchValue.value,
          ...props.searchParams,
        },
        {
          permission: 'page',
        },
      );
      const headerList: string[] = [];
      const columnIds: string[] = [];
      title.forEach((item) => {
        headerList.push(item.display_name);
        columnIds.push(item.name);
      });
      const colWidthList = Array(headerList.length)
        .fill(20)
        .map((width) => ({ wch: width }));
      const dataList = results.map((item) =>
        columnIds.reduce<string[]>((results, columnId) => {
          let value = item[columnId]!;
          if (columnId === 'bk_biz_id') {
            value = bizIdMap.get(Number(value))?.name || value;
          }
          results.push(value);
          return results;
        }, []),
      );
      return {
        colWidthList,
        dataList,
        fileName,
        headerList,
      };
    },
  });
</script>
<style lang="less">
  .render-dynamic-table {
    & ~ .render-dynamic-table {
      margin-top: 16px;
    }

    .title-operate-main {
      display: flex;
      width: 100%;
      align-items: center;
      justify-content: space-between;

      .search-select-main {
        width: 560px;
      }
    }

    .dynamic-table-main {
      .t-table__header {
        th {
          background-color: #fafbfd;
          border-top: none !important;
          border-right: none !important;

          &:hover {
            background-color: #eaebf0;
          }
        }
      }

      .t-table__filter-pop {
        .t-table__filter-pop-content {
          max-width: 160px;

          .t-table__filter-pop-content-inner {
            max-height: 100px;
            padding: 8px 16px;
            overflow-y: auto;

            .t-radio {
              display: flex;
              overflow: hidden;

              .t-radio__label {
                flex: 1;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
              }
            }
          }

          .t-table__filter--bottom-buttons {
            padding: 8px 16px;
          }
        }
      }
    }
  }
</style>
