<template>
  <BkLoading
    class="render-dynamic-table"
    :loading="loading">
    <BlockCard>
      <template #title>
        <span style="font-weight: 700">{{ tableName }}</span>
        <template v-if="isShowStateCount">
          <span class="ml-6 mr-2">(</span>
          <template v-if="!isOnlyAbnormal">
            <span>{{ t('正常') }}</span>
            <span class="ml-4 mr-4">:</span>
            <span style="font-weight: 700; color: #2caf5e">{{ stateCountsMap.normal }}</span>
            <span class="ml-4 mr-4">,</span>
          </template>
          <span>{{ t('预警') }}</span>
          <span class="ml-4 mr-4">:</span>
          <span style="font-weight: 700; color: #f59500">{{ stateCountsMap.warning }}</span>
          <span class="ml-4 mr-4">,</span>
          <span>{{ t('异常') }}</span>
          <span class="ml-4 mr-4">:</span>
          <span style="font-weight: 700; color: #ea3636">{{ stateCountsMap.abnormal }}</span>
          <span class="ml-2">)</span>
        </template>
      </template>
      <PrimaryTable
        :key="titleList.length"
        class="dynamic-table-main"
        :data="tableData"
        :max-height="485"
        :pagination="pagination"
        resizable
        row-key="instance"
        @page-change="handlePageChange">
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
          resizable
          :title="item.display_name"
          :width="getColumnMinWidth(item.name)">
          <template #default="{ row }: { row: ReportInfo['results'][number] }">
            <template v-if="item.format === 'status'">
              <!-- 兼容旧状态，需要保留 -->
              <DbStatus
                v-if="item.name === 'status'"
                :theme="row[item.name] ? 'success' : 'danger'">
                {{ row[item.name] ? t('成功') : t('失败') }}
              </DbStatus>
              <!-- 新状态 -->
              <DbStatus
                v-if="item.name === 'state'"
                :theme="getStateTheme(row[item.name]!)">
                {{ getStateText(row[item.name]!)}}
              </DbStatus>
            </template>
            <BkButton
              v-else-if="item.format === 'fail_slave_instance'"
              text
              theme="primary"
              @click="() => handleShowFailSlaveInstance(row)">
              {{ row[item.name] }}
            </BkButton>
            <span v-else-if="item.name === 'create_at'">{{ utcDisplayTime(row[item.name]) }}</span>
            <span v-else-if="item.name === 'bk_biz_id'">{{ bizsMap[row[item.name]] || row[item.name] }}</span>
            <span v-else>{{ row[item.name] || '--' }}</span>
          </template>
        </TableColumn>
      </PrimaryTable>
    </BlockCard>
    <FailSlaveInstance
      :id="failSlaveInstanceReportId"
      v-model="isShowFailSlaveInstance" />
  </BkLoading>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getReport } from '@services/source/report';

  import { useGlobalBizs } from '@stores';

  import DbStatus from '@components/db-status/index.vue';

  import { utcDisplayTime } from '@utils';

  import BlockCard from './components/BlockCard.vue';
  import FailSlaveInstance from './components/FailSlaveInstance.vue';

  interface Props {
    isOnlyAbnormal?: boolean;
    isPlatform?: boolean;
    isShowStateCount?: boolean;
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

  type ReportInfo = ServiceReturnType<typeof getReport>;

  const props = withDefaults(defineProps<Props>(), {
    isOnlyAbnormal: false,
    isPlatform: false,
    isShowStateCount: true,
  });

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const pagination = reactive({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  const tableName = ref('');
  const isShowFailSlaveInstance = ref(false);
  const failSlaveInstanceReportId = ref(0);
  const stateCountsMap = ref({
    abnormal: 0,
    normal: 0,
    warning: 0,
  });
  const titleList = ref<ReportInfo['title']>([]);

  const tableData = shallowRef<any[]>([]);

  const bizsMap = computed(() =>
    globalBizsStore.bizs.reduce<Record<number, string>>((results, item) => {
      Object.assign(results, {
        [item.bk_biz_id]: item.name,
      });
      return results;
    }, {}),
  );

  const { loading, run: fetchInspectionData } = useRequest(getReport, {
    manual: true,
    onSuccess(result) {
      stateCountsMap.value = result.state_count;
      pagination.total = result.count;
      tableName.value = result.name;
      const rawTitleList = result.title;
      const failedDaysIndex = rawTitleList.findIndex((item) => item.name === 'failed_days');
      const msgIndex = rawTitleList.findIndex((item) => item.name === 'msg');
      if (failedDaysIndex !== -1 && msgIndex !== -1) {
        [rawTitleList[failedDaysIndex], rawTitleList[msgIndex]] = [
          rawTitleList[msgIndex],
          rawTitleList[failedDaysIndex],
        ];
      }
      titleList.value = rawTitleList;
      tableData.value = result.results;
    },
  });

  const getColumnMinWidth = (name: string) => {
    if (['bk_biz_id', 'cluster_type', 'failed_days', 'state', 'status'].includes(name)) {
      return 80;
    }

    if (name === 'msg') {
      return 220;
    }

    return 150;
  };

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

  const fetchData = () => {
    const searchParams = _.cloneDeep(props.searchParams);
    if (searchParams.isOnlyAbnormal === 'true') {
      searchParams.state__in = 'warning,abnormal';
    }
    delete searchParams.isOnlyAbnormal;
    fetchInspectionData(
      props.serviceUrl,
      {
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
        // 默认排序，优先按失败天数排序，其次按创建时间排序
        ordering: '-failed_days,-create_at',
        platform: props.isPlatform,
        ...searchParams,
      },
      {
        permission: 'page',
      },
    );
  };

  watch(
    () => props.searchParams,
    () => {
      fetchData();
    },
    {
      immediate: true,
    },
  );

  const handleShowFailSlaveInstance = (data: any) => {
    isShowFailSlaveInstance.value = true;
    failSlaveInstanceReportId.value = data.id;
  };

  const handlePageChange = (pageInfo: { current: number; pageSize: number; previous: number }) => {
    if (pagination.pageSize !== pageInfo.pageSize) {
      pagination.pageSize = pageInfo.pageSize;
      pagination.current = 1;
      fetchData();
      return;
    }

    if (pageInfo.current !== pagination.current) {
      pagination.current = pageInfo.current;
      fetchData();
    }
  };

  defineExpose<Exposes>({
    async getExportExcelSheetData() {
      const searchParams = _.cloneDeep(props.searchParams);
      if (searchParams.isOnlyAbnormal === 'true') {
        searchParams.state__in = 'warning,abnormal';
      }
      delete searchParams.isOnlyAbnormal;
      const {
        name: fileName,
        results,
        title,
      } = await getReport(
        props.serviceUrl,
        {
          limit: -1,
          offset: 0,
          ordering: '-failed_days,-create_at',
          platform: props.isPlatform,
          ...searchParams,
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
            value = bizsMap.value[Number(value)]!;
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
    }
  }
</style>
