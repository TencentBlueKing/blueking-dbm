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
      <div class="right-operation">
        <SearchOperation
          ref="searchOperationRef"
          :show-bizs="isTodoPage"
          @search="handleSearchChange" />
      </div>
    </div>
    <DbTable
      ref="tableRef"
      :data-source="getAlarmEventsList"
      :line-height="56"
      :row-config="{
        useKey: true,
        keyField: 'id',
      }"
      selectable
      :settings="tableSetting"
      :show-overflow="false"
      :show-prepend="false"
      :show-select-all-page="false"
      show-settings
      @clear-search="handleClearSearchValue"
      @column-filter="handleColumnFilterChange"
      @column-sort="handleColumnSortChange"
      @request-success="handleRequestSuccess"
      @selection="handleSelection">
      <BkTableColumn
        field="alert_name"
        fixed="left"
        :label="t('告警名称')"
        :min-width="220"
        show-overflow="tooltip">
        <template #default="{ data }: { data: RowData }">
          <div class="alert-name-main">
            <div
              class="sign-bar"
              :style="{ background: data.severityColor }"></div>
            <div
              v-overflow-tips
              class="alert-name">
              {{ data.alert_name }}
            </div>
          </div>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="bk_biz_id"
        :label="t('所属业务')"
        :min-width="160"
        show-overflow="tooltip">
        <template #default="{ data }: { data: RowData }">
          <span>{{ bizsMap[data.bk_biz_id] || '--' }}</span>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="cluster"
        :label="t('所属集群')"
        show-overflow="tooltip"
        :width="220">
      </BkTableColumn>
      <BkTableColumn
        field="instance"
        :label="t('告警主机/实例')"
        :min-width="130"
        show-overflow="tooltip">
      </BkTableColumn>
      <BkTableColumn
        field="description"
        :label="t('告警内容')"
        show-overflow="tooltip"
        :width="380">
      </BkTableColumn>
      <BkTableColumn
        field="firstAnomalyTimeDisplay"
        :label="t('首次异常时间')"
        :min-width="200"
        :show-overflow="false">
      </BkTableColumn>
      <BkTableColumn
        field="beginTimeDisplay"
        :label="t('告警产生时间')"
        :min-width="200"
        :show-overflow="false">
      </BkTableColumn>
      <BkTableColumn
        field="appointee"
        :label="t('负责人')"
        show-overflow="tooltip"
        :width="160">
        <template #default="{ data }: { data: RowData }">
          <span>{{ data.appointee?.join(',') }}</span>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="status"
        :filters="statusFilterList"
        :label="t('状态')"
        :show-overflow="false"
        :width="100">
        <template #default="{ data }: { data: RowData }">
          <BkTag
            v-if="data.status === 'RECOVERED'"
            theme="success"
            type="filled">
            {{ t('已恢复') }}
          </BkTag>
          <BkTag
            v-else-if="data.status === 'ABNORMAL'"
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
      </BkTableColumn>
      <BkTableColumn
        field="stage"
        :filters="phaseFilterList"
        :label="t('处理阶段')"
        :show-overflow="false"
        :width="100">
        <template #default="{ data }: { data: RowData }">
          <BkTag
            v-if="data.is_shielded"
            theme="danger">
            {{ t('已屏蔽') }}
          </BkTag>
          <BkTag
            v-else-if="data.is_blocked"
            theme="warning">
            {{ t('已流控') }}
          </BkTag>
          <BkTag
            v-else-if="data.is_ack"
            theme="success">
            {{ t('已确认') }}
          </BkTag>
          <BkTag
            v-else
            theme="info">
            {{ t('已通知') }}
          </BkTag>
        </template>
      </BkTableColumn>
      <BkTableColumn
        fixed="right"
        :label="t('操作')"
        :min-width="150"
        :show-overflow="false">
        <template #default="{ data }: { data: RowData }">
          <BkButton
            v-if="data.is_shielded"
            text
            theme="primary"
            @click="() => handleOpenShieldAlarms(false, data)">
            {{ t('查看屏蔽') }}
          </BkButton>
          <BkButton
            v-else
            text
            theme="primary"
            @click="() => handleOpenShieldAlarms(true, data)">
            {{ t('屏蔽告警') }}
          </BkButton>
          <BkButton
            class="ml-8"
            disabled
            text
            theme="primary"
            @click="handleOpenDetailPage">
            {{ t('更多信息') }}
          </BkButton>
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
  <DbSideslider
    v-model:is-show="showShieldAlarm"
    :before-close="handleBeforeClose"
    class="shiled-alarm-page"
    :disabled-confirm="currentEvent?.is_shielded"
    width="960"
    @closed="handleClosed">
    <template #header>
      <span>{{ t('屏蔽告警') }}</span>
    </template>
    <ShieldAlarms
      ref="createShieldAlarmsRef"
      :data="currentEvent"
      @success="handleShieldSuccess" />
  </DbSideslider>
</template>
<script setup lang="tsx">
  import BkButton from 'bkui-vue/lib/button';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getAlarmEventsList } from '@services/source/monitor';

  import { useBeforeClose } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import DbTable from '@components/db-table/index.vue';

  import { exportExcelFile } from '@utils';

  import SearchOperation from './components/SearchOperation.vue';
  import ShieldAlarms from './components/ShieldAlarms.vue';

  export type RowData = ServiceReturnType<typeof getAlarmEventsList>['results'][number];

  const { t } = useI18n();
  const globalBizStore = useGlobalBizs();
  const router = useRouter();
  const route = useRoute();

  const isEditable = ref(true);
  const showShieldAlarm = ref(false);
  const tableRef = ref<InstanceType<typeof DbTable>>();
  const activeLevel = ref(0);
  const searchOperationRef = ref<InstanceType<typeof SearchOperation>>();
  const createShieldAlarmsRef = ref<InstanceType<typeof ShieldAlarms>>();

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

  const isTodoPage = computed(() => route.name === 'AlarmEventsTodo');

  const statusFilterList = [
    {
      label: t('已恢复'),
      value: 'RECOVERED',
    },
    {
      label: t('未恢复'),
      value: 'ABNORMAL',
    },
    {
      label: t('已失效'),
      value: 'CLOSED',
    },
  ];

  const phaseFilterList = [
    {
      label: t('已通知'),
      value: 'is_handled',
    },
    {
      label: t('已屏蔽'),
      value: 'is_shielded',
    },
    {
      label: t('已流控'),
      value: 'is_blocked',
    },
    {
      label: t('已确认'),
      value: 'is_ack',
    },
  ];

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
      'beginTimeDisplay',
      'bk_biz_id',
      'appointee',
    ],
    disabled: ['alert_name'],
  };

  const searchDataKeys = [
    'alert_name',
    'description',
    'cluster_domain',
    'bk_biz_id',
    'stage',
    'status',
    'instance',
    'ip',
    'severity',
  ];

  const columnFilterParams: Record<string, any> = {};

  watch(
    () => route.query,
    () => {
      updateTableData();
    },
    {
      deep: true,
    },
  );

  const updateTableData = () => {
    const params = route.query;
    if (!isTodoPage.value) {
      Object.assign(params, {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      });
    }
    if (route.query.self_assist) {
      Object.assign(params, {
        self_assist: true,
      });
    }
    if (route.query.self_manage || (!route.query.self_manage && !route.query.self_assist && isTodoPage.value)) {
      Object.assign(params, {
        self_manage: true,
      });
    }
    if (!route.query.status) {
      // 未选，默认设置未恢复状态
      Object.assign(params, {
        status: 'ABNORMAL',
      });
    }
    setTimeout(() => {
      tableRef.value?.fetchData({
        bk_biz_id: undefined,
        ...params,
      });
    });
  };

  const handleRequestSuccess = (data: ServiceReturnType<typeof getAlarmEventsList>) => {
    const severityInfo = data.aggs.find((item) => item.id === 'severity')!;
    const severityMap = severityInfo.children.reduce<Record<string, number>>((result, item) => {
      Object.assign(result, {
        [item.id]: item.count,
      });
      return result;
    }, {});
    severityList.value.forEach((item) => {
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
    router.push({
      name: route.name,
      query: {
        ...route.query,
        severity: level ? level : undefined,
      },
    });
  };

  const handleOpenShieldAlarms = (isEnable = true, data: RowData) => {
    currentEvent.value = data;
    isEditable.value = isEnable;
    showShieldAlarm.value = true;
  };

  const handleOpenDetailPage = () => {
    console.log('handleOpenDetailPage');
  };

  const handleClearSearchValue = () => {
    searchOperationRef.value!.reset();
  };

  const handleSelection = (_: any, list: RowData[]) => {
    selectionList.value = list;
  };

  const handleColumnFilterChange = (data: { checked: string[]; field: string }) => {
    if (data.checked.length) {
      columnFilterParams[data.field] = data.checked.join(',');
    } else {
      delete columnFilterParams[data.field];
    }
    tableRef.value?.fetchData({
      bk_biz_id: undefined,
      ...route.query,
      ...columnFilterParams,
    });
  };

  const handleColumnSortChange = (data: { checked: boolean; field: string }) => {
    console.log('column sort = ', data);
  };

  const handleSearchChange = (data: Record<string, string>) => {
    const searchData = _.cloneDeep(data);
    const query = _.cloneDeep(route.query);
    Object.keys(route.query).forEach((key) => {
      if (!searchData[key] && searchDataKeys.includes(key)) {
        // searchselect 删除的项
        delete query[key];
      } else if (searchData[key]) {
        query[key] = searchData[key];
        delete searchData[key];
      }
    });
    Object.assign(query, searchData);
    router.push({
      name: route.name,
      query,
    });
  };

  const handleClosed = () => {
    createShieldAlarmsRef.value!.reset();
  };

  const handleExport = () => {
    const formatData = selectionList.value.map((item) => ({
      [t('告警 ID')]: item.id,
      [t('告警主机/实例')]: item.instance,
      [t('告警产生时间')]: item.beginTimeDisplay,
      [t('告警内容')]: item.description,
      [t('告警名称')]: item.alert_name,
      [t('告警等级')]: item.severityDisplayName,
      [t('处理阶段')]: item.stage_display,
      [t('所属业务')]: bizsMap.value[item.bk_biz_id],
      [t('所属集群')]: item.cluster,
      [t('状态')]: item.statusDisplay,
      [t('负责人')]: item.appointee?.join(','),
      [t('首次异常时间')]: item.firstAnomalyTimeDisplay,
    }));
    const colsWidths = Array(11)
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
    updateTableData();
  };
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
