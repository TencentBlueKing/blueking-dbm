<template>
  <div class="inspection-manage-page">
    <div
      v-show="!isEmptyShow"
      class="page-content">
      <BkLoading :loading="overviewLoading">
        <DbaDbTab
          v-if="isTodoPage"
          v-model="tabType"
          :count-config="dbCountConfig"
          :include="availableDbs" />
        <DbTab
          v-else-if="isPlatform"
          v-model="tabType"
          :exclude="excludeDbs"
          :label-config="labelConfig" />
        <DbTabForBiz
          v-else
          v-model="tabType"
          v-model:is-show="isTabShow"
          :exclude="excludeDbs"
          :label-config="labelConfig" />
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
          <SearchBox
            :is-assist="isTodoAssist"
            :is-show-all="isPlatform"
            :is-todos="!isInspectionReport"
            :show-only-abnormal="!isTodoPage"
            style="margin-bottom: 16px"
            @change="handleSearchChange" />
        </div>
        <RenderDynamicTable
          v-for="url in serviceList"
          :key="url"
          ref="dynamicTablesRef"
          :is-only-abnormal="isOnlyAbnormal"
          :is-platform="isPlatform"
          :is-show-state-count="!isTodoPage"
          :search-params="searchParams"
          :service-url="url" />
      </div>
    </div>
    <BkException
      v-show="isEmptyShow"
      class="empty-exception"
      :description="t('暂无巡检待办')"
      scene="page"
      type="empty" />
  </div>
</template>
<script setup lang="ts">
  import BkLoading from 'bkui-vue/lib/loading';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import * as XLSX from 'xlsx';

  import { getReportOverview } from '@services/source/report';

  import { useReportCount } from '@hooks';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';
  import DbTabForBiz from '@components/db-tab-for-biz/Index.vue';
  import DbaDbTab from '@components/dba-db-tab/Index.vue';

  import RenderDynamicTable from './components/render-dynamic-table/Index.vue';
  import SearchBox from './components/SearchBox.vue';

  const { dbReportCountMap } = useReportCount();
  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const exportLoading = ref(false);
  const tabType = ref((route.query.tabType as DBTypes) || DBTypes.MYSQL);
  const searchParams = ref<Record<string, any>>({});
  const excludeDbs = ref<DBTypes[]>([]);
  const availableDbs = ref<DBTypes[]>([]);
  const dynamicTablesRef = ref<InstanceType<typeof RenderDynamicTable>[]>([]);
  const isTabShow = ref(true);
  const isOnlyAbnormal = ref(false);

  const isTodoAssist = computed(() => route.query.manage === 'assist');
  const isPlatform = computed(() => route.name === 'inspectionReportGlobal');
  const isInspectionReport = computed(() => route.name === 'inspectionReport');
  const isTodoPage = computed(() => route.name === 'inspectionTodosGlobal');
  const isEmptyShow = computed(() => {
    if (!isTodoPage.value) return false;
    if (!dbCountConfig.value) return false;
    const totalCount = Object.values(dbCountConfig.value).reduce((sum, val) => sum + (val || 0), 0);
    return totalCount === 0;
  });

  // 为 DbaDbTab 提供计数配置，内部自动选中第一个计数 > 0 的 Tab
  // 待我处理取 manageCount，待我协助取 assistCount
  const dbCountConfig = computed(() => {
    if (!dbReportCountMap.value || !Object.keys(dbReportCountMap.value).length) {
      return undefined;
    }
    return Object.entries(dbReportCountMap.value).reduce(
      (result, [key, val]) => {
        Object.assign(result, { [key]: isTodoAssist.value ? val.assistCount || 0 : val.manageCount || 0 });
        return result;
      },
      {} as Record<string, number>,
    );
  });

  const serviceList = computed(() => {
    if (!dbOverviewConfig.value?.[tabType.value]) {
      return [];
    }

    const pathList = dbOverviewConfig.value[tabType.value]!;
    return pathList.map((path) => `/db_report/${tabType.value}/${path}/`);
  });

  const labelConfig = computed(() => {
    if (
      isInspectionReport.value ||
      isPlatform.value ||
      !dbOverviewConfig.value ||
      !Object.keys(dbReportCountMap.value).length
    ) {
      return undefined;
    }

    return Object.keys(dbOverviewConfig.value).reduce(
      (results, item) => {
        Object.assign(results, {
          [item]: `${item}(${dbReportCountMap.value[item]?.manageCount || 0})`,
        });
        return results;
      },
      {} as Record<DBTypes, string>,
    );
  });

  const { data: dbOverviewConfig, loading: overviewLoading } = useRequest(getReportOverview, {
    onSuccess: (data) => {
      const dbs = Object.keys(data) as DBTypes[];
      const totalDbs = Object.keys(DBTypeInfos);
      availableDbs.value = dbs;
      excludeDbs.value = _.difference(totalDbs, dbs) as DBTypes[];
    },
  });

  watch(
    () => route.query,
    () => {
      if (!Object.keys(route.query).length) {
        return;
      }

      const queryObj = _.cloneDeep(route.query);
      delete queryObj.tabType;
      searchParams.value = queryObj;
    },
    {
      immediate: true,
    },
  );

  watch(tabType, () => {
    updateRouteQuery();
  });

  const updateRouteQuery = (payload?: Record<string, string>) => {
    const query = payload
      ? {
          ...payload,
          tabType: tabType.value,
        }
      : {
          ...searchParams.value,
          tabType: tabType.value,
        };
    if (route.query.manage) {
      Object.assign(query, { manage: route.query.manage });
    }
    if (isInspectionReport.value) {
      Object.assign(query, { bk_biz_id: window.PROJECT_CONFIG.BIZ_ID });
    }

    if (!isInspectionReport.value && !isPlatform.value) {
      if (!route.query.manage) {
        Object.assign(query, { manage: 'todo' });
      }
    }
    router.replace({
      name: route.name,
      query,
    });
  };

  const handleSearchChange = (payload: Record<string, any>) => {
    isOnlyAbnormal.value = payload.isOnlyAbnormal;
    updateRouteQuery(payload);
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
      XLSX.writeFile(workbook, `${tabType.value}_${t('巡检报告')}.xlsx`);
    } finally {
      exportLoading.value = false;
    }
  };
</script>
<style lang="less">
  .inspection-manage-page {
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

    .list-type-box {
      padding: 0 24px;
      background-color: #fff;

      .bk-tab-content {
        display: none;
      }

      .bk-tab-header {
        border: none;
        box-shadow: 0 3px 4px 0 #0000000a;
      }
    }

    .content-wrapper {
      padding: 20px;
      flex: 1;
      overflow-y: auto;

      .operation-main {
        display: flex;
        justify-content: space-between;
      }
    }

    .empty-exception {
      display: flex;
      height: 100%;
      background-color: #fff;
      align-items: center;
      justify-content: center;

      .bk-exception-description {
        font-size: 24px;
      }
    }
  }
</style>
