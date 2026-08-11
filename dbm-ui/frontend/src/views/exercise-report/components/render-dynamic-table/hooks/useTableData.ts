import type { SortInfo, TableColumnFilter, TableSort } from 'tdesign-vue-next';
import type { ComponentProps } from 'vue-component-type-helpers';
import { useRequest } from 'vue-request';

import { getReport } from '@services/source/report';
import { getUserList } from '@services/source/user';

import { useGlobalBizs } from '@stores';

import DbQuickSearch from '@components/db-quick-search/Index.vue';

import { calcTextWidth, random } from '@utils';

import type { Props, ReportInfo } from '../Index.vue';

export const useTableData = (props: Props) => {
  const { bizs } = useGlobalBizs();

  const searchValue = ref<Record<string, any>>({});
  const filterValue = ref<Record<string, any>>({});
  const renderSearchKey = ref(0);
  const tableName = ref('');
  const stateCountsMap = ref({
    abnormal: 0,
    normal: 0,
  });
  const titleList = ref<
    Array<
      {
        filterList?: TableColumnFilter;
      } & ReportInfo['title'][number]
    >
  >([]);
  const columnWidthMap = ref<Record<string, number>>({});

  const tableData = shallowRef<any[]>([]);

  const pagination = reactive({
    align: 'right',
    count: 0,
    current: 1,
    layout: ['total', 'limit', 'list'],
    limit: 10,
    limitList: [10, 20, 50, 100, 200, 500],
  });

  const searchSelectData = computed(() => {
    if (!reportData.value) {
      return [];
    }

    const searchList = reportData.value.title.reduce<ComponentProps<typeof DbQuickSearch>['data']>((results, item) => {
      if (item.filter) {
        const searchItem = {
          id: item.name,
          name: item.display_name,
        };
        if (item.filter.type === 'enum') {
          Object.assign(searchItem, {
            list: item.filter.enums,
            type: 'single',
          });
        }
        if (item.filter.type === 'biz') {
          Object.assign(searchItem, {
            list: bizs.map((item) => ({
              label: item.name,
              value: item.bk_biz_id,
            })),
            type: 'single',
          });
        }
        results.push(searchItem);
      }
      return results;
    }, []);
    if (props.serviceUrl.includes('backup_recover_drill')) {
      // 只有回档演练需要DBA过滤
      searchList.unshift({
        id: 'dba',
        name: 'DBA',
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
              label: `${item.username} (${item.display_name})`,
              value: item.username,
            })),
          );
        },
        remoteSearch: true,
        type: 'single',
      });
    }

    return searchList;
  });

  let sortParams: Record<string, string> = {};

  const {
    data: reportData,
    loading,
    run: fetchInspectionData,
  } = useRequest(getReport, {
    manual: true,
    onSuccess(result) {
      stateCountsMap.value = result.state_count;
      pagination.count = result.count;
      tableName.value = result.name;
      const rawTitleList: typeof titleList.value = result.title;
      if (result.count > 0 && !Object.keys(columnWidthMap.value).length) {
        const titleMap = result.title.reduce<Record<string, ReportInfo['title'][number]>>(
          (results, item) => Object.assign(results, { [item.name]: item }),
          {},
        );
        Object.entries(result.results[0]).forEach(([key, value]) => {
          const width = calcTextWidth(value);
          const isFixedWidth = ['link', 'log'].includes(titleMap[key]?.format);
          columnWidthMap.value[key] = isFixedWidth ? 120 : width > 120 ? width : 120;
        });
      }
      rawTitleList.forEach((item) => {
        if (item.filter?.enums) {
          Object.assign(item, {
            filterList: {
              list: item.filter.enums!,
              showConfirmAndReset: true,
              type: 'single',
            },
          });
          return;
        }
        if (item.filter?.type === 'biz') {
          Object.assign(item, {
            filterList: {
              list: bizs.map((item) => ({
                label: item.name,
                value: `${item.bk_biz_id}`,
              })),
              showConfirmAndReset: true,
              type: 'single',
            },
          });
          return;
        }
        Object.assign(item, {
          filterList: undefined,
        });
      });
      titleList.value = rawTitleList;
      tableData.value = result.results.map((item) => ({
        ...item,
        __uuid: random(),
      }));
    },
  });

  watch(
    () => [searchValue.value, props.searchParams],
    () => {
      pagination.current = 1;
      // 搜索框到表头filetr联动
      Object.keys(filterValue.value).forEach((key) => {
        if (!searchValue.value[key]) {
          delete filterValue.value[key];
        }
      });

      fetchData(sortParams);
    },
  );

  const fetchData = (sortParams: Record<string, string> = {}) => {
    fetchInspectionData(
      props.serviceUrl,
      {
        limit: pagination.limit,
        offset: (pagination.current - 1) * pagination.limit,
        ...searchValue.value,
        ...props.searchParams,
        ...sortParams,
      },
      {
        permission: 'page',
      },
    );
  };

  const handleFilterChange = (info: Record<string, string>, context: { trigger: string }) => {
    if (context.trigger === 'clear') {
      console.log('clear');
      searchValue.value = {};
      return;
    }

    Object.entries(info).forEach(([key, value]) => {
      if (value) {
        searchValue.value[key] = value;
      } else {
        delete searchValue.value[key];
      }
    });
    renderSearchKey.value++;
  };

  const handleSortChange = (info?: TableSort) => {
    if (!info) {
      sortParams = {};
    } else {
      const sortInfo = info as SortInfo;
      sortParams.ordering = sortInfo.descending ? `-${sortInfo.sortBy}` : sortInfo.sortBy;
    }
    fetchData(sortParams);
  };

  const handlePageValueChange = (pageValue: number) => {
    if (pagination.current === pageValue) {
      return;
    }
    pagination.current = pageValue;
    fetchData(sortParams);
  };

  const handlePageLimitChange = (pageLimit: number) => {
    if (pagination.limit === pageLimit) {
      return;
    }
    pagination.limit = pageLimit;
    pagination.current = 1;
    fetchData(sortParams);
  };

  return {
    columnWidthMap,
    filterValue,
    handleFilterChange,
    handlePageLimitChange,
    handlePageValueChange,
    handleSortChange,
    loading,
    pagination,
    renderSearchKey,
    searchSelectData,
    searchValue,
    sortParams,
    stateCountsMap,
    tableData,
    tableName,
    titleList,
  };
};
