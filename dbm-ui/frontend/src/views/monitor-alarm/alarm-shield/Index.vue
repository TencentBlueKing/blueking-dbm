<template>
  <div class="alarm-events-page">
    <div class="operation-main">
      <div class="left-operation">
        <AuthButton
          action-id="alert_shield_manage"
          :biz-id="currentBizId"
          class="w-64 mr-8"
          theme="primary"
          @click="() => handleOpenShieldAlarms('create')">
          {{ t('新建') }}
        </AuthButton>
        <BkRadioGroup
          v-model="filterValue"
          style="background: #eaebf0"
          type="capsule"
          @change="handleFilterChange">
          <BkRadioButton
            v-for="item in filterList"
            :key="item.name"
            :label="item.value">
            {{ item.name }}
          </BkRadioButton>
        </BkRadioGroup>
      </div>
      <div class="right-operation">
        <SearchOperation
          ref="searchOperationRef"
          @search="handleSearchChange" />
      </div>
    </div>
    <DbTable
      ref="tableRef"
      :data-source="getAlarmShieldList"
      releate-url-query
      row-key="id"
      size="large"
      @clear-search="handleClearSearchValue"
      @filter-change="handleTableFilterChange"
      @request-success="handleRequestFinished"
      @selection="handleSelection">
      <TableColumn
        col-key="id"
        fixed="left"
        :min-width="160"
        title="ID">
        <template #default="{ row }: { row: RowData }">
          <BkButton
            text
            theme="primary"
            @click="() => handleOpenShieldAlarms('edit', row)">
            {{ row.id }}
          </BkButton>
        </template>
      </TableColumn>
      <TableColumn
        col-key="category"
        :filter="{
          list: phaseFilterList,
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :min-width="160"
        :title="t('屏蔽类型')">
        <template #default="{ row }: { row: RowData }">
          <BkTag
            v-if="row.category === 'alert'"
            theme="info">
            {{ t('基于事件屏蔽') }}
          </BkTag>
          <BkTag
            v-else-if="row.category === 'dimension'"
            theme="danger">
            {{ t('基于维度屏蔽') }}
          </BkTag>
          <BkTag
            v-else
            theme="success">
            {{ t('基于策略屏蔽') }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="content"
        :min-width="400"
        :title="t('屏蔽内容')">
        <template #default="{ row }: { row: RowData }">
          <ShieldContent
            :data="row.dimension_config"
            :strategy-map="policyMap" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="description"
        :min-width="160"
        :title="t('屏蔽原因')">
      </TableColumn>
      <TableColumn
        v-if="isExpired"
        col-key="status"
        :title="t('状态')"
        :width="100">
        <template #default="{ row }: { row: RowData }">
          <span :style="{ color: row.status === 2 ? '#c4c6cc' : '#ff9c01' }">{{ row.statusDisplay }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="update_user"
        :min-width="160"
        :title="t('更新人')">
        <template #default="{ row }: { row: RowData }">
          <span>{{ row.update_user }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="shieldTimeDisplay"
        :min-width="420"
        :title="t('屏蔽时间')">
      </TableColumn>
      <TableColumn
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="130">
        <template #default="{ row }: { row: RowData }">
          <AuthButton
            v-bk-tooltips="{
              disabled: !isExpired && row.isEdiatable,
              content: t('暂不支持'),
            }"
            action-id="alert_shield_manage"
            :biz-id="row.bk_biz_id"
            :disabled="isExpired || !row.isEdiatable"
            :permission="isExpired || !row.isEdiatable ? true : row.permission.alert_shield_manage"
            text
            theme="primary"
            @click="() => handleOpenShieldAlarms('edit', row)">
            {{ t('编辑') }}
          </AuthButton>
          <AuthButton
            v-bk-tooltips="{
              disabled: row.isEdiatable,
              content: t('暂不支持'),
            }"
            action-id="alert_shield_manage"
            :biz-id="row.bk_biz_id"
            class="ml-8 mr-8"
            :disabled="!row.isEdiatable"
            :permission="!row.isEdiatable ? true : row.permission.alert_shield_manage"
            text
            theme="primary"
            @click="() => handleOpenShieldAlarms('clone', row)">
            {{ t('克隆') }}
          </AuthButton>
          <!-- 临时方案，PopConfirm需要支持手动控制弹窗 -->
          <BkPopConfirm
            v-if="!isExpired && row.permission.alert_shield_manage"
            :confirm-text="t('解除')"
            :title="t('确认解除该告警屏蔽？')"
            trigger="click"
            :width="280"
            @confirm="() => unlockAlarmShield({ id: row.id })">
            <AuthButton
              action-id="alert_shield_manage"
              :biz-id="row.bk_biz_id"
              :permission="row.permission.alert_shield_manage"
              text
              theme="primary">
              {{ t('解除') }}
            </AuthButton>
            <template #content>
              <div>{{ t('屏蔽 ID') }}：{{ row.id }}</div>
              <div class="mb-16 mt-5">{{ t('解除后，所有的屏蔽内容将同步失效') }}</div>
            </template>
          </BkPopConfirm>
          <AuthButton
            v-else
            action-id="alert_shield_manage"
            :biz-id="row.bk_biz_id"
            :disabled="isExpired"
            :permission="isExpired ? true : row.permission.alert_shield_manage"
            text
            theme="primary">
            {{ t('解除') }}
          </AuthButton>
        </template>
      </TableColumn>
    </DbTable>
  </div>
  <DbSideslider
    v-model:is-show="showShieldAlarm"
    :before-close="handleBeforeClose"
    class="shiled-alarm-page"
    :confirm-text="t('确定')"
    :disabled-confirm="isDisabled"
    width="960"
    @closed="handleClosed">
    <template #header>
      <div class="header-main">
        <div>{{ editModeTitleMap[editMode] }}{{ t('屏蔽告警') }}</div>
        <template v-if="editMode !== 'create'">
          <div class="split-line"></div>
          <div class="name">{{ currentAlarmShield?.id }}</div>
        </template>
      </div>
    </template>
    <EditShieldAlarms
      :data="currentAlarmShield"
      :edit-mode="editMode"
      @success="handleCreateSuccess" />
  </DbSideslider>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { disabledAlarmShield, getAlarmShieldList, getPolicyList } from '@services/source/monitor';

  import { useBeforeClose } from '@hooks';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { messageSuccess } from '@utils';

  import EditShieldAlarms from './components/edit-shield-alarms/Index.vue';
  import SearchOperation from './components/SearchOperation.vue';
  import ShieldContent from './components/ShieldContent.vue';

  type RowData = ServiceReturnType<typeof getAlarmShieldList>['results'][number];

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const handleBeforeClose = useBeforeClose();

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchOperationRef = ref<InstanceType<typeof SearchOperation>>();
  const editMode = ref('edit');
  const showShieldAlarm = ref(false);
  const filterValue = ref(route.query.is_active ? Number(route.query.is_active) : 1);
  const shieldingCount = ref(0);
  const expiredCount = ref(0);
  const currentAlarmShield = ref<RowData>();
  const policyMap = ref<Record<number, string>>({});

  const selectionList = shallowRef<RowData[]>([]);

  const isDisabled = computed(
    () => !!currentAlarmShield.value?.category && ['alert', 'scope'].includes(currentAlarmShield.value.category),
  );
  const filterList = computed(() => [
    {
      name: t('屏蔽中(n)', { n: shieldingCount.value }),
      value: 1,
    },
    {
      name: t('已失效(n)', { n: expiredCount.value }),
      value: 0,
    },
  ]);

  const isExpired = computed(() => filterValue.value === 0);

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const editModeTitleMap: Record<string, string> = {
    clone: t('克隆'),
    create: t('新建'),
    edit: t('编辑'),
  };
  const phaseFilterList = [
    {
      label: t('基于事件屏蔽'),
      value: 'alert',
    },
    {
      label: t('基于维度屏蔽'),
      value: 'dimension',
    },
    {
      label: t('基于策略屏蔽'),
      value: 'strategy',
    },
  ];
  const searchDataKeys = ['category', 'content', 'updator', 'time_range'];

  const { run: unlockAlarmShield } = useRequest(disabledAlarmShield, {
    manual: true,
    onSuccess() {
      messageSuccess(t('解除告警屏蔽成功'));
      const params = route.query;
      tableRef.value?.fetchData({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        ...params,
      });
    },
  });

  const { run: fetchPolicyList } = useRequest(getPolicyList, {
    manual: true,
    onSuccess(data) {
      data.results.forEach((item) => {
        Object.assign(policyMap.value, {
          [item.monitor_policy_id]: item.name,
        });
      });
    },
  });

  watch(showShieldAlarm, () => {
    if (showShieldAlarm.value) {
      setTimeout(() => {
        window.changeConfirm = false;
      });
    }
  });

  watch(
    () => route.query,
    () => {
      const params = route.query;
      setTimeout(() => {
        tableRef.value?.fetchData({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          is_active: filterValue.value,
          ...params,
        });
      });
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const handleRequestFinished = (data: { count: number; results: RowData[] }) => {
    if (filterValue.value) {
      shieldingCount.value = data.count;
    } else {
      expiredCount.value = data.count;
    }
    const list = _.flatMap(data.results.map((item) => item.dimension_config.strategy_id || [])).filter(
      (item) => !!item,
    );
    const strategyList = _.uniq(list);
    fetchPolicyList({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      monitor_policy_ids: strategyList.join(','),
    });
  };

  const handleOpenShieldAlarms = (mode: string, data?: RowData) => {
    editMode.value = mode;
    currentAlarmShield.value = data;
    showShieldAlarm.value = true;
  };

  const handleClearSearchValue = () => {
    searchOperationRef.value!.reset();
  };

  const handleFilterChange = (value: number) => {
    router.push({
      name: route.name,
      query: {
        ...route.query,
        is_active: value,
      },
    });
  };

  const handleSelection = (_: any, list: RowData[]) => {
    selectionList.value = list;
  };

  const handleTableFilterChange = (filterValue: Record<string, string[]>) => {
    const columnFilterParams = Object.keys(filterValue).reduce<Record<string, string>>((result, key) => {
      if (filterValue[key]?.length) {
        Object.assign(result, {
          [key]: filterValue[key].join(','),
        });
      }
      return result;
    }, {});
    tableRef.value?.fetchData({
      ...route.query,
      ...columnFilterParams,
    });
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
    window.changeConfirm = false;
  };

  const handleCreateSuccess = () => {
    const params = route.query;
    tableRef.value?.fetchData({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      ...params,
    });
  };

  const initFilterCount = async () => {
    const data = await Promise.all([
      getAlarmShieldList({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        is_active: true,
      }),
      getAlarmShieldList({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        is_active: false,
      }),
    ]);
    shieldingCount.value = data[0].count;
    expiredCount.value = data[1].count;
  };

  initFilterCount();
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
  .shiled-alarm-page {
    .header-main {
      display: flex;
      width: 100%;
      height: 52px;
      align-items: center;

      .split-line {
        width: 1px;
        height: 14px;
        margin-right: 8px;
        margin-left: 12px;
        background: #dcdee5;
      }

      .name {
        overflow: hidden;
        font-size: 14px;
        color: #979ba5;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
      }
    }
  }
</style>
