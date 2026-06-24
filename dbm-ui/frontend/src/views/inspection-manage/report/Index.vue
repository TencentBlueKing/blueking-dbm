<template>
  <div class="inspection-report-page">
    <Teleport to="#dbContentHeaderAppend">
      <DbDayQuickSelect
        v-model="timeRange"
        class="ml-20" />
    </Teleport>
    <div class="page-content">
      <BkLoading :loading="overviewLoading">
        <DbTab
          v-if="isPlatform"
          v-model="tabType"
          :exclude="excludeDbs" />
        <DbTabForBiz
          v-else
          v-model="tabType"
          v-model:is-show="isTabShow"
          :exclude="excludeDbs" />
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
            <BkCheckbox v-model="isOnlyAbnormal">
              {{ t('仅显示预警 / 异常') }}
            </BkCheckbox>
            <DbQuickSearch
              v-model="searchValue"
              class="search-select-main"
              :data="searchData"
              unique-select
              value-split-code="," />
          </div>
        </div>
        <RenderDynamicTable
          v-for="url in serviceList"
          :key="url"
          ref="dynamicTablesRef"
          :is-only-abnormal="isOnlyAbnormal"
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

  import { useGlobalBizs } from '@stores';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import DbDayQuickSelect from '@components/db-day-quick-select/Index.vue';
  import DbQuickSearch from '@components/db-quick-search/Index.vue';
  import DbTab from '@components/db-tab/Index.vue';
  import DbTabForBiz from '@components/db-tab-for-biz/Index.vue';

  import RenderDynamicTable from '../components/render-dynamic-table/Index.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();

  const isPlatform = computed(() => route.name === 'inspectionReportGlobal');

  const tabType = ref<DBTypes | undefined>();
  const searchParams = ref<Record<string, any>>({});
  const timeRange = ref('');
  const isOnlyAbnormal = ref(true);
  const excludeDbs = ref<DBTypes[]>([]);
  const isTabShow = ref(true);
  const searchValue = ref<Record<string, any>>({});
  const exportLoading = ref(false);
  const dynamicTablesRef = ref<InstanceType<typeof RenderDynamicTable>[]>([]);

  const { data: dbOverviewConfig, loading: overviewLoading } = useRequest(getReportOverview, {
    onSuccess: (data) => {
      excludeDbs.value = _.difference(Object.keys(DBTypeInfos), Object.keys(data)) as DBTypes[];
    },
  });

  const serviceList = computed(() => {
    if (!tabType.value || !dbOverviewConfig.value?.[tabType.value]) {
      return [];
    }
    return dbOverviewConfig.value[tabType.value]!.map((path) => `/db_report/${tabType.value}/${path}/`);
  });

  // 平台视角支持按业务、主 DBA 过滤；业务视角仅支持集群、状态过滤
  const searchData = computed(() => {
    return _.filter(
      [
        isPlatform.value && {
          id: 'select_biz_id',
          list: globalBizsStore.bizs.map((biz) => ({
            label: biz.name,
            value: biz.bk_biz_id,
          })),
          name: t('业务'),
          type: 'single',
        },
        isPlatform.value && {
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
        !isOnlyAbnormal.value && {
          id: 'state',
          list: [
            {
              label: t('正常'),
              value: 'normal',
            },
            {
              label: t('异常'),
              value: 'abnormal',
            },
            {
              label: t('预警'),
              value: 'warning',
            },
          ],
          name: t('状态'),
          type: 'single',
        },
      ],
      (item) => item,
    ) as ComponentProps<typeof DbQuickSearch>['data'];
  });

  const requestParams = computed(() => {
    const params: Record<string, any> = {
      ..._.cloneDeep(searchValue.value),
      isOnlyAbnormal: String(isOnlyAbnormal.value),
      platform: isPlatform.value,
      tabType: tabType.value,
      time_range: timeRange.value,
    };
    // 业务视角下的巡检报告需要携带业务 ID
    if (!isPlatform.value) {
      Object.assign(params, { bk_biz_id: window.PROJECT_CONFIG.BIZ_ID });
    }
    return params;
  });

  watch(
    () => route.query,
    () => {
      const routerQuery = _.cloneDeep(route.query) as Record<string, string>;

      searchParams.value = {};
      ['bk_biz_id', 'cluster', 'dba', 'state'].forEach((item) => {
        if (routerQuery[item]) {
          searchValue.value[item] = routerQuery[item];
        }
      });

      timeRange.value = routerQuery.time_range || 'now -1d';
      isOnlyAbnormal.value = routerQuery.isOnlyAbnormal ? routerQuery.isOnlyAbnormal === 'true' : true;
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
      XLSX.writeFile(workbook, `${tabType.value}_${t('巡检报告')}.xlsx`);
    } finally {
      exportLoading.value = false;
    }
  };
</script>
<style lang="less">
  .inspection-report-page {
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
</style>
