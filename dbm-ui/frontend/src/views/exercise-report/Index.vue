<template>
  <div class="exercise-report-page">
    <div
      v-show="!isEmptyShow"
      class="page-content">
      <BkLoading :loading="overviewLoading">
        <DbTab
          v-model="tabType"
          :exclude="excludeDbs" />
      </BkLoading>
      <div class="content-wrapper">
        <div class="operation-main">
          <BkButton
            class="export-tables"
            :loading="exportLoading"
            theme="primary"
            @click="handleExport">
            {{ t('导出') }}
          </BkButton>
          <BkCheckbox
            v-model="isOnlyAbnormal"
            class="only-abnormal-checkbox">
            {{ t('仅显示异常') }}
          </BkCheckbox>
          <BkDatePicker
            append-to-body
            class="date-picker-main"
            clearable
            :model-value="dateValue"
            :placeholder="t('请选择日期范围')"
            type="datetimerange"
            @change="handleDatePickerChange"
            @clear="handleDatePickerClear"
            @pick-success="handleDatePickerSuccess" />
        </div>
        <RenderDynamicTable
          v-for="url in serviceList"
          :key="url"
          ref="dynamicTablesRef"
          :search-params="searchParams"
          :service-url="url" />
      </div>
    </div>
    <BkException
      v-show="isEmptyShow"
      class="empty-exception"
      :description="t('暂无数据')"
      scene="part"
      type="empty" />
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import * as XLSX from 'xlsx';

  import { getReportOverview } from '@services/source/report';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';

  import RenderDynamicTable from './components/render-dynamic-table/Index.vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const exportLoading = ref(false);
  const tabType = ref(DBTypes.MYSQL);
  const excludeDbs = ref<DBTypes[]>([]);
  const dynamicTablesRef = ref<InstanceType<typeof RenderDynamicTable>[]>([]);
  const isTabShow = ref(true);
  const isOnlyAbnormal = ref(true);
  const dateValue = ref<[string, string]>(['', '']);
  const searchParams = ref<Record<string, any>>({});

  const isEmptyShow = computed(() => !isTabShow.value);
  const serviceList = computed(() => {
    if (!dbOverviewConfig.value?.[tabType.value]) {
      return [];
    }

    const pathList = dbOverviewConfig.value[tabType.value]!;
    return pathList.map((path) => `/db_report/${tabType.value}/${path}/`);
  });

  const { data: dbOverviewConfig, loading: overviewLoading } = useRequest(getReportOverview, {
    defaultParams: [
      {
        kind: 'drill',
      },
    ],
    onSuccess: (data) => {
      const availableDbs = Object.keys(data);
      const totalDbs = Object.keys(DBTypeInfos);
      excludeDbs.value = _.difference(totalDbs, availableDbs) as DBTypes[];
    },
  });

  let tmpDateValue: [string, string] = ['', ''];

  const updateRouteQuery = () => {
    const query = {
      create_at__gte: dateValue.value[0],
      create_at__lte: dateValue.value[1],
      isOnlyAbnormal: `${isOnlyAbnormal.value}`,
      tabType: tabType.value,
    };
    searchParams.value = {};

    if (dateValue.value[0] && dateValue.value[1]) {
      searchParams.value = {
        create_at__gte: dateValue.value[0],
        create_at__lte: dateValue.value[1],
      };
    }
    if (isOnlyAbnormal.value) {
      searchParams.value.state__in = 'abnormal';
    }
    router.replace({
      name: route.name,
      query,
    });
  };

  watch(
    tabType,
    () => {
      isOnlyAbnormal.value = true;
      dateValue.value = [
        dayjs().subtract(1, 'day').startOf('day').format('YYYY-MM-DD HH:mm:ss'),
        dayjs().format('YYYY-MM-DD HH:mm:ss'),
      ];
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [tabType.value, isOnlyAbnormal.value, dateValue.value],
    () => {
      updateRouteQuery();
    },
    {
      immediate: true,
    },
  );

  const initSearchData = () => {
    if (route.query.tabType) {
      tabType.value = route.query.tabType as DBTypes;
    }
    if (route.query.isOnlyAbnormal) {
      isOnlyAbnormal.value = route.query.isOnlyAbnormal === 'true';
    }
    if (route.query.create_at__gte && route.query.create_at__lte) {
      dateValue.value = [
        dayjs(route.query.create_at__gte as string).format('YYYY-MM-DD HH:mm:ss'),
        dayjs(route.query.create_at__lte as string).format('YYYY-MM-DD HH:mm:ss'),
      ];
    }
  };

  const handleDatePickerChange = (value: [string, string]) => {
    tmpDateValue = value;
  };

  const handleDatePickerSuccess = () => {
    dateValue.value = tmpDateValue;
  };

  const handleDatePickerClear = () => {
    tmpDateValue = ['', ''];
    dateValue.value = ['', ''];
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
      XLSX.writeFile(workbook, `${tabType.value}_${t('演练报告')}.xlsx`);
    } finally {
      exportLoading.value = false;
    }
  };

  initSearchData();
</script>
<style lang="less">
  .exercise-report-page {
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
        align-items: center;
        margin-bottom: 16px;

        .export-tables {
          width: 64px;
        }

        .only-abnormal-checkbox {
          margin-right: 8px;
          margin-left: auto;
        }

        .date-picker-main {
          width: 340px;
        }
      }
    }

    .empty-exception {
      display: flex;
      height: 100%;
      background-color: #fff;
      align-items: center;
      justify-content: center;
    }
  }
</style>
