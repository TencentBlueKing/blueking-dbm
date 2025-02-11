<template>
  <div class="inspection-manage-page">
    <BkLoading :loading="overviewLoading">
      <DbTab
        v-model="tabType"
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
          :is-show-all="isInspectionReportGlobal"
          :is-todos="!isInspectionReport"
          style="margin-bottom: 16px"
          @change="handleSearchChange" />
      </div>
      <RenderDynamicTable
        v-for="url in serviceList"
        :key="url"
        ref="dynamicTablesRef"
        :is-platform="isPlatform"
        :search-params="searchParams"
        :service-url="url" />
    </div>
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
  const dynamicTablesRef = ref<InstanceType<typeof RenderDynamicTable>[]>([]);

  const isTodoAssist = computed(() => route.query.manage === 'assist');
  const isPlatform = computed(() => route.name === 'inspectionReportGlobal');

  const serviceList = computed(() => {
    if (!dbOverviewConfig.value || !dbOverviewConfig.value[tabType.value]) {
      return [];
    }

    const pathList = dbOverviewConfig.value[tabType.value];
    return pathList.map((path) => `/db_report/${tabType.value}/${path}/`);
  });

  const labelConfig = computed(() => {
    if (isInspectionReport || !dbOverviewConfig.value || !Object.keys(dbReportCountMap.value).length) {
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
      const availableDbs = Object.keys(data);
      const totalDbs = Object.keys(DBTypeInfos);
      excludeDbs.value = _.difference(totalDbs, availableDbs) as DBTypes[];
    },
  });

  const isInspectionReport = route.name === 'inspectionReport';
  const isInspectionReportGlobal = route.name === 'inspectionReportGlobal';

  watch(
    () => route.query,
    () => {
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
    if (isInspectionReport) {
      Object.assign(query, { bk_biz_id: window.PROJECT_CONFIG.BIZ_ID });
    }

    if (!isInspectionReport && !isInspectionReportGlobal) {
      Object.assign(query, { status: 0 });

      if (!route.query.manage) {
        Object.assign(query, { manage: 'todo' });
      }
    }
    router.replace({
      name: route.name,
      query,
    });
  };

  const handleSearchChange = (payload: Record<string, string>) => {
    updateRouteQuery(payload);
  };

  const handleExport = async () => {
    exportLoading.value = true;
    try {
      const sheetDataList = await Promise.all(dynamicTablesRef.value.map((item) => item.getExportExcelSheetData()));
      const workbook = XLSX.utils.book_new();
      sheetDataList.forEach((item) => {
        const { headerList, colWidthList, fileName, dataList } = item;
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
    display: flex;
    height: 100%;
    overflow: hidden;
    flex-direction: column;

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
  }
</style>
