<template>
  <div class="alarm-events-page">
    <div class="operation-main">
      <div class="left-operation">
        <BkButton
          :disabled="!selectionList.length"
          style="width: 64px; margin-right: 8px"
          theme="primary"
          @click="handleExport">
          {{ t('导出') }}
        </BkButton>
        <div class="level-filter-main">
          <div
            v-for="(item, index) in severityList"
            :key="index"
            class="filter-item"
            :class="{ 'filter-item-active': activeLevel === item.value }"
            @click="() => handleSelectLevel(item.value)">
            <div
              v-if="item.iconColor"
              class="icon"
              :style="{ backgroundColor: item.iconColor }"></div>
            <div>{{ `${item.name}(${item.count})` }}</div>
          </div>
        </div>
      </div>
    </div>
    <div class="mb-20">
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        :placeholder="t('搜索DB类型，告警产生时间，告警名称，告警内容，所属集群…')"
        style="width: 560px"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      :bk-ui-settings="tableSetting"
      :data-source="getAlarmEventsList"
      :filter-value="quickSearchValue"
      releate-url-query
      row-key="id"
      selectable
      :show-select-all-page="false"
      @clear-search="handleClearSearchValue"
      @filter-change="handleTableFilterChange"
      @request-success="handleRequestSuccess"
      @selection="handleSelection">
      <TableColumn
        col-key="alert_name"
        fixed="left"
        :min-width="220"
        :title="t('告警名称')">
        <template #default="{ row }: { row: RowData }">
          <div class="alert-name-main">
            <div
              class="sign-bar"
              :style="{ background: row.severityColor }"></div>
            <div
              v-overflow-tips
              class="alert-name">
              {{ row.alert_name }}
            </div>
          </div>
        </template>
      </TableColumn>
      <TableColumn
        v-if="isTodoPage || isGlobalPage"
        col-key="bk_biz_id"
        :min-width="160"
        :title="t('所属业务')">
        <template #default="{ row }: { row: RowData }">
          <span>{{ row.alarmBizId !== undefined ? bizsMap[row.alarmBizId] || '--' : '--' }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="cluster"
        :title="t('所属集群')"
        :width="220">
      </TableColumn>
      <TableColumn
        col-key="instance"
        :min-width="130"
        :title="t('告警主机/实例')">
      </TableColumn>
      <TableColumn
        col-key="description"
        :title="t('告警内容')"
        :width="380">
      </TableColumn>
      <TableColumn
        col-key="stage"
        :filter="columnFilterConfig.stage"
        :title="t('处理阶段')"
        :width="100">
        <template #default="{ row }: { row: RowData }">
          <BkTag
            v-if="row.is_shielded"
            theme="danger">
            {{ t('已屏蔽') }}
          </BkTag>
          <BkTag
            v-else-if="row.is_blocked"
            theme="warning">
            {{ t('已流控') }}
          </BkTag>
          <BkTag
            v-else-if="row.is_ack"
            theme="success">
            {{ t('已确认') }}
          </BkTag>
          <BkTag
            v-else
            theme="info">
            {{ t('已通知') }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="dbm_policy"
        :title="t('关联策略')"
        :width="240">
        <template #default="{ row }: { row: RowData }">
          <BkButton
            v-if="row.dbm_policy.id"
            text
            theme="primary"
            @click="() => handleToMonitorStrategy(row.dbm_policy, row.dimensions)">
            {{ row.policyNameDisplay }}
          </BkButton>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="createTimeDisplay"
        :min-width="200"
        :title="t('告警产生时间')">
      </TableColumn>
      <TableColumn
        col-key="firstAnomalyTimeDisplay"
        :min-width="200"
        :title="t('首次异常时间')">
      </TableColumn>
      <TableColumn
        col-key="status"
        :filter="columnFilterConfig.status"
        :title="t('状态')"
        :width="100">
        <template #default="{ row }: { row: RowData }">
          <BkTag
            v-if="row.status === 'RECOVERED'"
            theme="success"
            type="filled">
            {{ t('已恢复') }}
          </BkTag>
          <BkTag
            v-else-if="row.status === 'ABNORMAL'"
            theme="danger"
            type="filled">
            {{ t('未恢复') }}
          </BkTag>
          <BkTag
            v-else
            type="filled">
            {{ t('已失效') }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="240">
        <template #default="{ row }: { row: RowData }">
          <BkButton
            v-if="row.is_shielded"
            text
            theme="primary"
            @click="() => handleOpenShieldAlarms(false, row)">
            {{ t('查看屏蔽') }}
          </BkButton>
          <AuthButton
            v-else
            v-bk-tooltips="{
              disabled: row.dbm_event,
              content: t('暂不支持，请去监控平台操作'),
            }"
            action-id="alert_shield_manage"
            :biz-id="row.alarmBizId"
            :disabled="!row.dbm_event"
            :permission="row.dbm_event ? row.permission.alert_shield_manage : true"
            text
            theme="primary"
            @click="() => handleOpenShieldAlarms(true, row)">
            {{ t('屏蔽告警') }}
          </AuthButton>
          <ToAlarmPolicy
            v-if="row.dbm_policy.id"
            :data="row.dbm_policy"
            :name="row.policyNameDisplay"
            @confirm="(editType: string) => handleToMonitorStrategy(row.dbm_policy, row.dimensions, editType)" />
          <BkButton
            class="ml-16"
            :disabled="!urls.BKMONITOR_URL"
            text
            theme="primary"
            @click="() => handleOpenDetailPage(row)">
            {{ t('跳转监控') }}
          </BkButton>
        </template>
      </TableColumn>
    </DbTable>
  </div>
  <DbSideslider
    v-model:is-show="showShieldAlarm"
    :before-close="handleBeforeClose"
    :cancel-text="isCurrentEventShielded ? t('关闭') : t('取消')"
    class="shiled-alarm-page"
    :disabled-confirm="isCurrentEventShielded"
    :show-confirm="!isCurrentEventShielded"
    :show-leave-confirm="false"
    width="960"
    @closed="handleClosed">
    <template #header>
      <span>{{ isCurrentEventShielded ? t('查看屏蔽') : t('屏蔽告警') }}</span>
    </template>
    <ShieldAlarms
      ref="createShieldAlarmsRef"
      :data="currentEvent"
      @success="handleShieldSuccess" />
  </DbSideslider>
</template>
<script setup lang="tsx">
  import BkButton from 'bkui-vue/lib/button';
  import { useI18n } from 'vue-i18n';

  import { getAlarmEventsList } from '@services/source/monitor';

  import { useBeforeClose } from '@hooks';

  import { useGlobalBizs, useSystemEnviron } from '@stores';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { exportExcelFile, getBusinessHref } from '@utils';

  import ShieldAlarms from './components/ShieldAlarms.vue';
  import ToAlarmPolicy from './components/ToAlarmPolicy.vue';
  import { columnFilterConfig, dbTypeSearchId, timeRangeSearchId, useQuickSearch } from './useQuickSearch';

  export type RowData = ServiceReturnType<typeof getAlarmEventsList>['results'][number];

  interface Exposes {
    customUpdate: (param: Record<string, any>) => void;
    getSearchValue: () => Record<string, any>;
  }

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const globalBizStore = useGlobalBizs();
  const { urls } = useSystemEnviron();

  const isEditable = ref(true);
  const showShieldAlarm = ref(false);
  const tableRef = ref<InstanceType<typeof DbTable>>();
  // 告警级别只由这个筛选条负责，不放进快捷搜索
  const activeLevel = ref(Number(route.query.severity) || 0);
  const createShieldAlarmsRef = ref<InstanceType<typeof ShieldAlarms>>();
  const severityList = ref([
    {
      count: 0,
      iconColor: '',
      name: t('全部'),
      value: 0,
    },
    {
      count: 0,
      iconColor: '#3A84FF',
      name: t('提醒'),
      value: 3,
    },
    {
      count: 0,
      iconColor: '#F59500',
      name: t('预警'),
      value: 2,
    },
    {
      count: 0,
      iconColor: '#EA3636',
      name: t('致命'),
      value: 1,
    },
  ]);

  const selectionList = shallowRef<RowData[]>([]);
  const currentEvent = shallowRef<RowData>();

  const bizsMap = computed(() =>
    globalBizStore.bizs.reduce<Record<number, string>>((results, item) => {
      Object.assign(results, {
        [item.bk_biz_id]: item.name,
      });
      return results;
    }, {}),
  );
  const isCurrentEventShielded = computed(() => currentEvent.value?.is_shielded);
  const isTodoPage = computed(() => route.name === 'platformAlarmEventsTodo');
  const isGlobalPage = computed(() => route.name === 'platformAlarmEvents');

  const { defaultEndTime, defaultStartTime, quickSearchData, quickSearchValue } = useQuickSearch({
    isGlobalPage,
    isTodoPage,
  });

  const tableSetting = {
    checked: [
      'alert_name',
      'description',
      'status',
      'stage',
      'cluster',
      'instance',
      'strategy_name',
      'firstAnomalyTimeDisplay',
      'createTimeDisplay',
      'bk_biz_id',
      'appointee',
      'dbm_policy',
    ],
    disabled: ['alert_name'],
  };

  let searchValue: Record<string, string> = {};

  const triggerSearch = () => {
    tableRef.value?.fetchData({
      bk_biz_id: undefined,
      ...searchValue,
    });
  };

  const initURLParmasToSearchValue = () => {
    if (!isTodoPage.value && !isGlobalPage.value) {
      Object.assign(searchValue, {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      });
    }
    // 平台管理页鉴权标记
    if (isGlobalPage.value) {
      Object.assign(searchValue, {
        platform: true,
      });
    }
    if (route.query.self_assist) {
      Object.assign(searchValue, {
        self_assist: true,
      });
    }
    if (route.query.self_manage || (!route.query.self_manage && !route.query.self_assist && isTodoPage.value)) {
      Object.assign(searchValue, {
        self_manage: true,
      });
    }
    if (route.query.bk_biz_id) {
      Object.assign(searchValue, {
        bk_biz_id: Number(route.query.bk_biz_id),
      });
    }
    if (activeLevel.value) {
      Object.assign(searchValue, {
        severity: activeLevel.value,
      });
    }
  };

  initURLParmasToSearchValue();

  const handleRequestSuccess = (data: ServiceReturnType<typeof getAlarmEventsList>) => {
    const severityInfo = data.aggs.find((item) => item.id === 'severity');
    if (!severityInfo) {
      return;
    }

    const severityMap = severityInfo.children.reduce<Record<string, number>>((result, item) => {
      Object.assign(result, {
        [item.id]: item.count,
      });
      return result;
    }, {});
    severityList.value.forEach((item) => {
      // 全部
      if (!item.value) {
        Object.assign(item, {
          count: severityInfo.count,
        });
      } else {
        Object.assign(item, {
          count: severityMap[item.value],
        });
      }
    });
  };

  const handleSelectLevel = (level: number) => {
    activeLevel.value = level;
    Object.assign(searchValue, {
      severity: level ? level : undefined,
    });

    triggerSearch();
  };

  const handleOpenShieldAlarms = (isEnable = true, data: RowData) => {
    currentEvent.value = data;
    isEditable.value = isEnable;
    showShieldAlarm.value = true;
  };

  const handleOpenDetailPage = (data: RowData) => {
    const url = `${urls.BKMONITOR_URL}/?bizId=${urls.DBA_APP_BK_BIZ_ID}#/event-center/detail/${data.id}`;
    window.open(url);
  };

  const handleClearSearchValue = () => {
    quickSearchValue.value = {
      status: 'ABNORMAL',
      [timeRangeSearchId]: `${defaultStartTime},${defaultEndTime}`,
    };
  };

  const handleSelection = (_: any, list: RowData[]) => {
    selectionList.value = list;
  };

  // 表头筛选与快捷搜索共用 quickSearchValue，写回后由快捷搜索的 change 统一触发请求。
  // 只取有表头筛选的列，避免整体替换时丢掉其他搜索条件
  const handleTableFilterChange = (filterValue: Record<string, string>) => {
    const nextValue = { ...quickSearchValue.value };
    Object.keys(columnFilterConfig).forEach((key) => {
      if (filterValue[key]) {
        Object.assign(nextValue, {
          [key]: filterValue[key],
        });
      } else {
        delete nextValue[key];
      }
    });

    quickSearchValue.value = nextValue;
  };

  const handleQuickSearchChange = (value: Record<string, string>) => {
    // 先清掉上一次快捷搜索产生的条件，避免搜索项被删除后条件残留。
    // 业务页的 bk_biz_id 不在快捷搜索里，会保留页面上下文的业务
    ['start_time', 'end_time', ...quickSearchData.value.map((item) => item.id)].forEach((key) => {
      delete searchValue[key];
    });

    const [startTime, endTime] = (value[timeRangeSearchId] || '').split(',');
    Object.assign(searchValue, {
      // 接口的 db_types 只接受数组
      db_types: value[dbTypeSearchId] ? value[dbTypeSearchId].split(',') : [],
      // 接口的 start_time / end_time 必填，时间范围被删除时回退到默认区间
      end_time: endTime || defaultEndTime,
      start_time: startTime || defaultStartTime,
    });

    quickSearchData.value.forEach((item) => {
      if (item.id === dbTypeSearchId || item.id === timeRangeSearchId || value[item.id] === undefined) {
        return;
      }
      Object.assign(searchValue, {
        [item.id]: item.id === 'bk_biz_id' ? Number(value[item.id]) : value[item.id],
      });
    });

    triggerSearch();
  };

  const handleClosed = () => {
    createShieldAlarmsRef.value!.reset();
  };

  const handleExport = () => {
    const formatData = selectionList.value.map((item) => {
      const row: Record<string, string | undefined> = {
        [t('告警 ID')]: item.id,
        [t('告警主机/实例')]: item.instance,
        [t('告警产生时间')]: item.createTimeDisplay,
        [t('告警内容')]: item.description,
        [t('告警名称')]: item.alert_name,
        [t('告警等级')]: item.severityDisplayName,
        [t('处理阶段')]: item.stage_display,
        [t('所属集群')]: item.cluster,
        [t('状态')]: item.statusDisplay,
        [t('负责人')]: item.appointee?.join(','),
        [t('首次异常时间')]: item.firstAnomalyTimeDisplay,
      };
      // 业务上下文不导出所属业务列
      if (isTodoPage.value || isGlobalPage.value) {
        row[t('所属业务')] = bizsMap.value[item.bk_biz_id];
      }
      return row;
    });
    const colCount = formatData[0] ? Object.keys(formatData[0]).length : 0;
    const colsWidths = Array(Math.max(colCount, 1))
      .fill(15)
      .map((width) => ({ width }));
    exportExcelFile(formatData, colsWidths, 'Sheet1', `${route.meta.navName}.xlsx`);
  };

  const handleBeforeClose = () => {
    const beforeClose = useBeforeClose();
    const isValueChange = createShieldAlarmsRef.value!.checkValueChange();
    return beforeClose(isValueChange);
  };

  const handleShieldSuccess = () => {
    currentEvent.value!.is_shielded = true;
  };

  const handleToMonitorStrategy = (
    data: RowData['dbm_policy'],
    dimensions: RowData['dimensions'],
    editType?: string,
  ) => {
    const { href } = router.resolve({
      name: 'monitorStrategy',
      query: {
        db_type: data.db_type,
        edit_type: editType,
        id: data.id,
      },
    });
    const bizDimension = dimensions.find((item) => item.key === 'appid' || item.display_key === 'appid');
    const bizId = bizDimension?.value || 0;
    window.open(isTodoPage || isGlobalPage ? getBusinessHref(href, Number(bizId)) : href, '_blank');
  };

  defineExpose<Exposes>({
    customUpdate(params: Record<string, any>) {
      searchValue = params;
      triggerSearch();
    },
    getSearchValue() {
      return searchValue;
    },
  });
</script>
<style lang="less" scoped>
  .alarm-events-page {
    padding: 20px 24px;

    .operation-main {
      display: flex;
      flex-wrap: wrap;

      .left-operation {
        display: flex;
        min-width: 430px;
        margin-bottom: 16px;
        flex: 1;

        .level-filter-main {
          display: flex;
          height: 32px;
          padding: 4px;
          font-size: 12px;
          cursor: pointer;
          background: #eaebf0;
          border-radius: 2px;

          .filter-item {
            display: flex;
            align-items: center;
            padding: 0 12px;
            border-radius: 2px;

            &.filter-item-active {
              color: #3a84ff;
              background: #fff;
            }

            .icon {
              width: 8px;
              height: 8px;
              margin-right: 4px;
            }
          }
        }
      }

      .right-operation {
        margin-bottom: 16px;

        .search-select {
          width: 560px;
        }
      }
    }
  }
</style>
<style lang="less">
  .alert-name-main {
    display: flex;
    width: 100%;
    align-items: center;

    .sign-bar {
      width: 4px;
      height: 12px;
      margin-right: 4px;
      background: #f59500;
      border-radius: 1px;
    }

    .alert-name {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
