<template>
  <BkLoading
    class="render-dynamic-table"
    :class="{ 'is-empty': total === 0 || totalAbnormalCount === 0 }"
    :loading="loading">
    <CollapseCard>
      <template #title>
        <span style="font-weight: 700">{{ tableName }}</span>
        <template v-if="isTodo">
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
      <div
        v-if="emptyDescription"
        style="font-size: 14px; line-height: 40px; color: #999; text-align: center">
        {{ emptyDescription }}
        <I18nT
          v-if="route.query.time_range !== 'now -30d'"
          keypath="若想查看更早结果，请扩大时间范围">
          <BkButton
            text
            theme="primary"
            @click="handleExpandTimeRange">
            {{ t('扩大时间范围') }}
          </BkButton>
        </I18nT>
      </div>
      <PrimaryTable
        v-else
        class="dynamic-table-main"
        :data="tableData"
        :max-height="485"
        resizable
        row-key="__uuid">
        <template #empty>
          <slot name="empty">
            <BkException
              :description="t('搜索为空')"
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
          :width="columnWidthMap[item.name] || 120">
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
      <div
        v-if="!emptyDescription"
        class="table-footer">
        <BkPagination
          v-bind="pagination"
          @change="handlePageValueChange"
          @limit-change="handlePageLimitChange" />
      </div>
    </CollapseCard>
    <FailSlaveInstance
      :id="failSlaveInstanceReportId"
      v-model="isShowFailSlaveInstance" />
  </BkLoading>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getReport } from '@services/source/report';

  import { useGlobalBizs } from '@stores';

  import CollapseCard from '@components/collapse-card/Index.vue';
  import DbStatus from '@components/db-status/index.vue';

  import { calcTextWidth, random, utcDisplayTime } from '@utils';

  import FailSlaveInstance from './components/FailSlaveInstance.vue';

  interface Props {
    isOnlyAbnormal?: boolean;
    isTodo?: boolean;
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
    isTodo: false,
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();

  const pagination = reactive({
    align: 'right',
    count: 0,
    current: 1,
    layout: ['total', 'limit', 'list'],
    limit: 10,
    limitList: [10, 20, 50, 100, 200, 500],
  });

  const tableName = ref('');
  const total = ref(0);
  const totalAbnormalCount = ref(0);
  const isShowFailSlaveInstance = ref(false);
  const failSlaveInstanceReportId = ref(0);
  const stateCountsMap = ref({
    abnormal: 0,
    normal: 0,
    warning: 0,
  });
  const titleList = ref<ReportInfo['title']>([]);
  const columnWidthMap = ref<Record<string, number>>({});

  const tableData = shallowRef<any[]>([]);

  const bizsMap = computed(() =>
    globalBizsStore.bizs.reduce<Record<number, string>>((results, item) => {
      Object.assign(results, {
        [item.bk_biz_id]: item.name,
      });
      return results;
    }, {}),
  );

  const emptyDescription = computed(() => {
    const timeRange = (props.searchParams.time_range as string) || 'now -1d';
    const timeRangeTextMap: Record<string, string> = {
      'now -1d': t('近 24 小时'),
      'now -30d': t('近 30 天'),
      'now -3d': t('近 3 天'),
      'now -7d': t('近 7 天'),
    };

    const timeRangeText = timeRangeTextMap[timeRange] || timeRangeTextMap['now -1d'];
    if (total.value === 0) {
      return t('{timeRange}内无巡检记录', { timeRange: timeRangeText });
    }
    if (props.isOnlyAbnormal && totalAbnormalCount.value === 0) {
      return t('{timeRange}内无预警或异常', { timeRange: timeRangeText });
    }
    return '';
  });

  const { loading, run: fetchInspectionData } = useRequest(getReport, {
    manual: true,
    onSuccess(result) {
      stateCountsMap.value = result.state_count;
      pagination.count = result.count;
      total.value = result.total_count;
      totalAbnormalCount.value = result.total_abnormal_count;
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
      if (result.count > 0 && !Object.keys(columnWidthMap.value).length) {
        Object.entries(result.results[0]).forEach(([key, value]) => {
          const width = calcTextWidth(value);
          columnWidthMap.value[key] = width > 120 ? width : 120;
        });
      }
      titleList.value = rawTitleList;
      tableData.value = result.results.map((item) =>
        Object.assign(item, {
          __uuid: random(),
        }),
      );
    },
  });

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
        limit: pagination.limit,
        offset: (pagination.current - 1) * pagination.limit,
        // 默认排序，优先按失败天数排序，其次按创建时间排序
        ordering: '-failed_days,-create_at',
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

  const handlePageValueChange = (pageValue: number) => {
    if (pagination.current === pageValue) {
      return;
    }
    pagination.current = pageValue;
    fetchData();
  };

  const handlePageLimitChange = (pageLimit: number) => {
    if (pagination.limit === pageLimit) {
      return;
    }
    pagination.limit = pageLimit;
    pagination.current = 1;
    fetchData();
  };

  // 时间范围档位，从小到大排序
  const timeRangeLevels = ['now -1d', 'now -3d', 'now -7d', 'now -30d'];

  const handleExpandTimeRange = () => {
    const currentTimeRange = (route.query.time_range as string) || 'now -1d';
    const currentIndex = timeRangeLevels.indexOf(currentTimeRange);
    // 取下一档位，已是最大档位则保持不变
    const nextTimeRange = timeRangeLevels[currentIndex + 1] || timeRangeLevels[timeRangeLevels.length - 1];
    router.push({
      query: {
        ...route.query,
        time_range: nextTimeRange,
      },
    });
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

    &.is-empty {
      .collapse-card-main.is-toggle {
        padding-bottom: 0;

        .card-content {
          margin-top: 0;
        }
      }
    }

    .dynamic-table-empty {
      display: flex;
      height: 80px;
      align-items: center;
      justify-content: center;
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
</style>
