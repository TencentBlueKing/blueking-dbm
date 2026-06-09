<template>
  <div class="inspection-page inspection-todo-page">
    <Teleport to="#dbContentTitleAppend">
      <div class="inspection-todo-page-title-icon">
        <DbIcon
          v-bk-tooltips="titleTooltip"
          type="attention" />
      </div>
    </Teleport>
    <Teleport to="#dbContentHeaderAppend">
      <div class="inspection-todo-page-head-controls-main">
        <div
          class="tab-item tab-item-todo"
          :class="{ 'tab-item-active': currentActiveTab === 'todo' }"
          @click="() => handleClickTab('todo')">
          <DbIcon
            class="control-icon"
            type="wodedaiban" />
          <span>{{ t('待我处理') }}</span>
          <span> （{{ manageCount }}）</span>
        </div>
        <div
          class="tab-item tab-item-assist"
          :class="{ 'tab-item-active': currentActiveTab !== 'todo' }"
          @click="() => handleClickTab('assist')">
          <DbIcon
            class="control-icon"
            type="yonghu-2" />
          <span>{{ t('待我协助') }}</span>
          <span>（{{ assistCount }}）</span>
        </div>
      </div>
      <DbDayQuickSelect
        v-model="timeRange"
        class="ml-20" />
    </Teleport>
    <div class="page-content">
      <BkLoading :loading="overviewLoading">
        <DbaDbTab
          v-model="tabType"
          :count-config="dbCountConfig"
          :include="availableDbs" />
      </BkLoading>
      <div class="content-wrapper">
        <div class="operation-main">
          <BkButton
            :loading="exportLoading"
            style="width: 64px"
            theme="primary"
            @click="handleExport">
            {{ t('导出') }}
          </BkButton>
          <div class="inspection-search-operations">
            <DbQuickSearch
              v-model="searchValue"
              class="search-select-main"
              :data="searchData"
              unique-select />
          </div>
        </div>
        <RenderDynamicTable
          v-for="url in serviceList"
          :key="url"
          ref="dynamicTablesRef"
          is-only-abnormal
          is-todo
          :search-params="requestParams"
          :service-url="url" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import * as XLSX from 'xlsx';

  import { getReportOverview } from '@services/source/report';
  import { getUserList } from '@services/source/user';

  import { useReportCount } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { DBTypes } from '@common/const';

  import DbDayQuickSelect from '@components/db-day-quick-select/Index.vue';
  import DbQuickSearch from '@components/db-quick-search/Index.vue';
  import DbaDbTab from '@components/dba-db-tab/Index.vue';

  import RenderDynamicTable from '../components/render-dynamic-table/Index.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const { assistCount, dbReportCountMap, manageCount } = useReportCount();
  const titleTooltip = `${t('待我处理')}：${t('展示我作为主 DBA 的业务，当日所产生的巡检异常，一般每日更新一次')}\n${t('待我协助')}：${t('展示我作为备 DBA、二线 DBA 的业务，当日所产生的巡检异常，一般每日更新一次')}`;

  const currentActiveTab = ref('');
  const tabType = ref<DBTypes | undefined>();
  const searchParams = ref<Record<string, any>>({});
  const timeRange = ref('');
  const availableDbs = ref<DBTypes[]>([]);
  const searchValue = ref<Record<string, any>>({});
  const exportLoading = ref(false);
  const dynamicTablesRef = ref<InstanceType<typeof RenderDynamicTable>[]>([]);

  const { data: dbOverviewConfig, loading: overviewLoading } = useRequest(getReportOverview, {
    onSuccess: (data) => {
      availableDbs.value = Object.keys(data) as DBTypes[];
    },
  });

  const isAssist = computed(() => currentActiveTab.value === 'assist');

  const serviceList = computed(() => {
    if (!tabType.value || !dbOverviewConfig.value?.[tabType.value]) {
      return [];
    }
    return dbOverviewConfig.value[tabType.value]!.map((path) => `/db_report/${tabType.value}/${path}/`);
  });

  // 为 DbaDbTab 提供计数配置，内部自动选中第一个计数 > 0 的 Tab
  // 待我处理取 manageCount，待我协助取 assistCount
  const dbCountConfig = computed(() => {
    if (!dbReportCountMap.value || !Object.keys(dbReportCountMap.value).length) {
      return undefined;
    }
    return Object.entries(dbReportCountMap.value).reduce(
      (result, [key, val]) => {
        Object.assign(result, { [key]: isAssist.value ? val.assistCount || 0 : val.manageCount || 0 });
        return result;
      },
      {} as Record<string, number>,
    );
  });

  // 待我协助场景下额外支持按主 DBA 过滤
  const searchData = computed(() => {
    return _.filter(
      [
        {
          id: 'select_biz_id',
          list: globalBizsStore.bizs.map((biz) => ({
            label: biz.name,
            value: biz.bk_biz_id,
          })),
          name: t('业务'),
          type: 'single',
        },
        isAssist.value && {
          id: 'dba',
          name: t('主DBA'),
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
        },
        {
          id: 'cluster',
          name: t('集群'),
        },
      ],
      (item) => item,
    ) as ComponentProps<typeof DbQuickSearch>['data'];
  });

  const requestParams = computed(() => {
    return {
      ..._.cloneDeep(searchValue.value),
      isOnlyAbnormal: 'true',
      manage: currentActiveTab.value,
      platform: true,
      tabType: tabType.value,
      time_range: timeRange.value,
    };
  });

  watch(
    () => route.query,
    () => {
      const routerQuery = _.cloneDeep(route.query) as Record<string, string>;

      searchParams.value = {};
      ['select_biz_id', 'cluster', 'dba'].forEach((item) => {
        if (routerQuery[item]) {
          searchValue.value[item] = routerQuery[item];
        }
      });

      timeRange.value = routerQuery.time_range || 'now -1d';
      currentActiveTab.value = routerQuery.manage || 'todo';
      tabType.value = routerQuery.tabType as DBTypes;
    },
    {
      immediate: true,
    },
  );

  watch(requestParams, () => {
    const routerQuery = _.omit({ ...requestParams.value }, ['platform']) as Record<string, string>;
    router.replace({
      name: route.name as string,
      query: routerQuery,
    });
  });

  const handleClickTab = (tab: string) => {
    currentActiveTab.value = tab;
  };

  const handleExport = async () => {
    exportLoading.value = true;
    try {
      const sheetDataList = await Promise.all(dynamicTablesRef.value.map((item) => item.getExportExcelSheetData()));
      const workbook = XLSX.utils.book_new();
      sheetDataList.forEach((item) => {
        const { colWidthList, dataList, fileName, headerList } = item;
        const worksheet = XLSX.utils.aoa_to_sheet([headerList, ...dataList]);
        XLSX.utils.book_append_sheet(workbook, worksheet, `${tabType.value}-${fileName}`);
        worksheet['!cols'] = colWidthList;
      });
      XLSX.writeFile(workbook, `${tabType.value}_${t('巡检待办')}.xlsx`);
    } finally {
      exportLoading.value = false;
    }
  };
</script>
<style lang="less">
  .inspection-page {
    height: 100%;

    .page-content {
      display: flex;
      height: 100%;
      overflow: hidden;
      flex-direction: column;
    }

    .bk-tab-header {
      width: 100%;

      .bk-tab-header-nav {
        width: 100%;
      }
    }

    .content-wrapper {
      padding: 20px;
      flex: 1;
      overflow-y: auto;

      .operation-main {
        display: flex;
        margin-bottom: 16px;
        justify-content: space-between;
      }

      .inspection-search-operations {
        display: flex;
        gap: 8px;

        .search-select-main {
          width: 580px;
        }
      }
    }
  }

  .inspection-todo-page-title-icon {
    display: flex;
    margin-right: 12px;
    margin-left: 6px;
    font-size: 16px;
    color: #979ba5;
    cursor: pointer;
    align-items: center;
  }

  .inspection-todo-page-head-controls-main {
    position: relative;
    display: flex;
    padding-left: 12px;

    &::before {
      position: absolute;
      top: 9px;
      left: 0;
      width: 1px;
      height: 14px;
      background: #c4c6cc;
      content: '';
    }

    .tab-item {
      display: flex;
      height: 32px;
      padding: 0 5px 0 8px;
      font-size: 14px;
      color: #4d4f56;
      cursor: pointer;
      background: #f0f1f5;
      align-items: center;

      &.tab-item-active {
        color: #3a84ff;
        background: #f0f5ff;
      }

      &.tab-item-todo {
        border-radius: 2px 0 0 2px;
      }

      &.tab-item-assist {
        position: relative;
        border-radius: 0 2px 2px 0;

        &::before {
          position: absolute;
          top: 9px;
          left: 0;
          width: 1px;
          height: 14px;
          background: #c4c6cc;
          content: '';
        }
      }

      .control-icon {
        margin-right: 5px;
        font-size: 14px;
      }
    }
  }
</style>
