<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkSideslider
    v-model:is-show="isShow"
    class="replenish-record-details-slider"
    width="75%">
    <template #header>
      <span>{{ t('操作详情') }}</span>
      <span class="header-desc">ID: {{ id }}</span>
    </template>
    <div class="replenish-record-details">
      <BkLoading :loading="isLoading">
        <!-- 摘要信息区 -->
        <div class="slide-summary">
          <div class="summary-item">
            <span class="summary-label">{{ t('补货数量') }}：</span>
            <span class="summary-value">
              <span
                v-for="(value, db) in summaryInfo.details"
                :key="db"
                class="db-count">
                {{ dbNameMap[db] }}: {{ value }}
              </span>
            </span>
          </div>
          <div class="summary-divider" />
          <div class="summary-item">
            <span class="summary-label">{{ t('申请人') }}：</span>
            <span class="summary-value">{{ summaryInfo.creator || '--' }}</span>
          </div>
          <div class="summary-divider" />
          <div class="summary-item">
            <span class="summary-label">{{ t('申请时间') }}：</span>
            <span class="summary-value">{{
              summaryInfo.create_at ? utcDisplayTime(summaryInfo.create_at) : '--'
            }}</span>
          </div>
        </div>

        <!-- 工具栏：状态Tab + 批量终止 + 导出 + 搜索 -->
        <div class="slide-toolbar">
          <div class="status-tab-group">
            <div
              v-for="tab in statusTabs"
              :key="tab.key"
              class="slide-status-tab"
              :class="{ active: activeStatusTab === tab.key }"
              @click="handleStatusTabChange(tab.key)">
              {{ tab.label }}
              <span
                class="tab-count"
                :class="{ active: activeStatusTab === tab.key }">
                {{ statusCountMap[tab.key] || 0 }}
              </span>
            </div>
          </div>

          <BkButton
            v-if="activeStatusTab === 'all' || activeStatusTab === 'FAILED'"
            class="batch-terminate-btn"
            :disabled="selectedRows.length === 0"
            outline
            theme="danger"
            @click="handleBatchTerminate">
            {{ t('批量终止') }}
          </BkButton>

          <span
            v-if="selectedRows.length > 0"
            class="batch-info">
            {{ t('已选') }}
            <span class="batch-count">{{ selectedRows.length }}</span>
            {{ t('条') }}
            <BkButton
              text
              theme="primary"
              @click="handleClearSelection">
              {{ t('取消选择') }}
            </BkButton>
          </span>

          <BkButton
            v-bk-tooltips="t('导出该补货操作关联的所有单据明细，不受当前筛选条件影响')"
            :loading="isExporting"
            @click="handleExportAll">
            <DbIcon
              class="mr-4"
              type="bk-dbm-icon db-icon-import" />
            {{ t('导出全部') }}
          </BkButton>

          <div class="slide-search-select">
            <DbQuickSearch
              v-model="quickSearchValue"
              :data="slideQuickSearchData"
              :placeholder="t('单号 / DB类型')"
              style="width: 100%" />
          </div>
        </div>

        <!-- 表格 -->
        <BkTable
          ref="tableRef"
          border
          :columns="tableColumns"
          :data="filteredTableData"
          :max-height="tableMaxHeight"
          @selection-change="handleSelectionChange" />

        <!-- 底部 -->
        <div class="slide-footer">
          <span class="footer-total">{{ t('共 n 条单据', { n: tableData.length }) }}</span>
        </div>
      </BkLoading>
    </div>

    <!-- 批量终止弹窗 -->
    <BkDialog
      v-model:is-show="isShowTerminateDialog"
      :title="t('批量终止')"
      :width="480">
      <BkForm
        ref="terminateFormRef"
        :model="terminateForm"
        :rules="terminateFormRules">
        <BkFormItem
          :label="t('操作')"
          property="action"
          required>
          <BkRadioGroup v-model="terminateForm.action">
            <BkRadio label="terminate">
              <BkTag theme="warning">{{ t('终止单据') }}</BkTag>
              {{ t('终止后，单据将作废处理') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('备注')"
          property="remark"
          required>
          <BkInput
            v-model="terminateForm.remark"
            :maxlength="100"
            :placeholder="t('请输入')"
            :rows="4"
            show-word-limit
            type="textarea" />
        </BkFormItem>
      </BkForm>
      <template #footer>
        <BkButton
          :loading="isTerminating"
          theme="primary"
          @click="handleConfirmTerminate">
          {{ t('确定') }}
        </BkButton>
        <BkButton @click="isShowTerminateDialog = false">
          {{ t('取消') }}
        </BkButton>
      </template>
    </BkDialog>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { exportReplenishTickets, fetchReplenish, listTicketApplyInfo } from '@services/source/dbresourceReplenish';
  import { getTickets } from '@services/source/ticket';
  import { batchProcessTicket, getInnerFlowInfo } from '@services/source/ticketFlow';

  import { useSystemEnviron } from '@stores';

  import { DBTypeInfos, TicketTypes } from '@common/const';

  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { messageSuccess, utcDisplayTime } from '@utils';

  type StatusKey = 'all' | 'FAILED' | 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'TERMINATED';

  type RowData = {
    apply_count: number;
    city: string;
    count: number;
    create_at: string;
    db_type: string;
    delivery_count: number;
    isRunning: boolean;
    operator: string;
    os_name: string;
    record_id: number;
    spec: {
      spec_machine_type: string;
      spec_name: string;
    };
    status: string;
    statusIcon: string;
    statusText: string;
    subzone: string;
    ticket_id: number;
  } & TicketModel;

  interface Props {
    id: number;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();
  const router = useRouter();
  const systemEnvironStore = useSystemEnviron();

  const tableRef = ref();
  const tableData = shallowRef<RowData[]>([]);
  const isLoading = shallowRef(false);
  const isExporting = ref(false);
  const activeStatusTab = ref<StatusKey>('all');
  const selectedRows = ref<RowData[]>([]);
  const quickSearchValue = ref<Record<string, any>>({});
  const isShowTerminateDialog = ref(false);
  const isTerminating = ref(false);
  const terminateFormRef = ref();
  const ticketInnerFlowInfo = shallowRef<ServiceReturnType<typeof getInnerFlowInfo>>({});

  const summaryInfo = ref({
    create_at: '',
    creator: '',
    details: {} as Record<string, number>,
  });

  const terminateForm = reactive({
    action: 'terminate',
    remark: '',
  });

  const terminateFormRules = {
    remark: [{ message: t('备注不能为空'), required: true, trigger: 'blur' }],
  };

  const tableMaxHeight = computed(() => window.innerHeight - 320);

  const dbNameMap: Record<string, string> = {};
  const machineTypeMap: Record<string, string> = {};
  Object.values(DBTypeInfos).forEach((db) => {
    dbNameMap[db.id] = db.name;
    db.machineList.forEach((machine) => {
      machineTypeMap[`${machine.value}`] = `${machine.label}`;
    });
  });

  const statusTabs = [
    { key: 'all' as const, label: t('全部') },
    { key: 'FAILED' as const, label: t('已失败') },
    { key: 'PENDING' as const, label: t('待确认') },
    { key: 'RUNNING' as const, label: t('执行中') },
    { key: 'SUCCEEDED' as const, label: t('已完成') },
    { key: 'TERMINATED' as const, label: t('已终止') },
  ];

  const slideQuickSearchData = computed(() => [
    {
      id: 'id',
      name: t('单号'),
      type: 'input' as const,
    },
    {
      id: 'db_type',
      list: Object.values(DBTypeInfos).reduce<Record<'label' | 'value', string>[]>((acc, db) => {
        acc.push({
          label: db.name,
          value: db.id,
        });
        return acc;
      }, []),
      name: t('DB 类型'),
      type: 'multiple' as const,
    },
  ]);

  // 状态数量统计
  const statusCountMap = computed(() => {
    const map: Record<string, number> = {
      all: tableData.value.length,
      FAILED: 0,
      PENDING: 0,
      RUNNING: 0,
      SUCCEEDED: 0,
      TERMINATED: 0,
    };
    tableData.value.forEach((item) => {
      // 将 TODO、INNER_TODO、RESOURCE_REPLENISH、TIMER 状态统一映射为 PENDING
      const pendingStatuses = [
        TicketModel.STATUS_TODO,
        TicketModel.STATUS_INNER_TODO,
        TicketModel.STATUS_RESOURCE_REPLENISH,
        TicketModel.STATUS_TIMER,
      ];
      // 将 APPROVE 状态映射为 RUNNING
      if (item.status === TicketModel.STATUS_APPROVE) {
        map.RUNNING++;
      } else if (pendingStatuses.includes(item.status)) {
        map.PENDING++;
      } else if (map[item.status] !== undefined) {
        map[item.status]++;
      }
    });
    return map;
  });

  // 筛选后的表格数据
  const filteredTableData = computed(() => {
    let data = tableData.value;

    // 状态筛选
    if (activeStatusTab.value !== 'all') {
      // 待确认状态需要匹配多个原始状态
      if (activeStatusTab.value === 'PENDING') {
        const pendingStatuses = [
          TicketModel.STATUS_TODO,
          TicketModel.STATUS_INNER_TODO,
          TicketModel.STATUS_RESOURCE_REPLENISH,
          TicketModel.STATUS_TIMER,
        ];
        data = data.filter((item) => pendingStatuses.includes(item.status));
      } else if (activeStatusTab.value === 'RUNNING') {
        // 执行中需要匹配 RUNNING 和 APPROVE 状态
        data = data.filter(
          (item) => item.status === TicketModel.STATUS_RUNNING || item.status === TicketModel.STATUS_APPROVE,
        );
      } else {
        data = data.filter((item) => item.status === activeStatusTab.value);
      }
    }

    // id 和 db_type 的过滤由后端接口处理

    return data;
  });

  // 表格列配置
  const tableColumns = computed(() => {
    const showStatusColumn = activeStatusTab.value === 'all';
    const showCheckboxColumn = activeStatusTab.value === 'all' || activeStatusTab.value === 'FAILED';

    const columns: any[] = [];

    if (showCheckboxColumn) {
      columns.push({
        fixed: 'left',
        selectable: (row: RowData) => row.status === TicketModel.STATUS_FAILED,
        type: 'selection',
        width: 50,
      });
    }

    columns.push(
      {
        field: 'id',
        fixed: 'left',
        label: t('单号'),
        render: ({ data }: { data: RowData }) => (
          <bk-button
            onClick={() => handleOpenTicketDetail(data)}
            text
            theme='primary'>
            {data.id}
          </bk-button>
        ),
        width: 80,
      },
      {
        field: 'inner_flow',
        label: t('子任务'),
        render: ({ data }: { data: RowData }) => {
          const flowInfo = ticketInnerFlowInfo.value[data.id];
          if (!flowInfo) {
            return (
              <div
                class='rotate-loading'
                style='display: inline-block'>
                <db-icon
                  svg
                  type='sync-pending'
                />
              </div>
            );
          }
          if (flowInfo.length < 1) {
            return '--';
          }
          return flowInfo.map((flowItem, index) => (
            <div
              key={index}
              style='line-height: 26px'>
              <bk-button
                onClick={() => handleGoTaskHistoryDetail(data, flowItem)}
                text
                theme='primary'>
                {flowItem.flow_alias}
              </bk-button>
            </div>
          ));
        },
        width: 150,
      },
    );

    if (showStatusColumn) {
      columns.push({
        field: 'status',
        label: t('状态'),
        render: ({ data }: { data: RowData }) => (
          <TicketStatusTag
            data={{
              status: data.status,
              statusText: data.status_display,
            }}
          />
        ),
        width: 120,
      });
    }

    columns.push(
      {
        field: 'db_type',
        label: t('DB 类型'),
        render: ({ data }: { data: RowData }) => dbNameMap[data.db_type] || '--',
        width: 120,
      },
      {
        field: 'spec.spec_machine_type',
        label: t('规格类型'),
        render: ({ data }: { data: RowData }) => machineTypeMap[data.spec?.spec_machine_type] || '--',
        width: 120,
      },
      {
        field: 'spec.spec_name',
        label: t('规格'),
        render: ({ data }: { data: RowData }) => data.spec?.spec_name || '--',
        width: 180,
      },
      {
        field: 'city',
        label: t('地域'),
        render: ({ data }: { data: RowData }) => data.city || '--',
        width: 100,
      },
      {
        field: 'subzone',
        label: t('园区'),
        render: ({ data }: { data: RowData }) => data.subzone || '--',
        width: 120,
      },
      {
        field: 'os_name',
        label: t('操作系统'),
        render: ({ data }: { data: RowData }) => data.os_name || '--',
        width: 120,
      },
      {
        field: 'count',
        label: t('申请数量'),
        render: ({ data }: { data: RowData }) => <span class='bold-number'>{data.count || 0}</span>,
        width: 100,
      },
      {
        field: 'delivery_count',
        label: t('已交付'),
        render: ({ data }: { data: RowData }) => {
          const isSuccess = data.delivery_count === data.count;
          const isFailed = data.delivery_count < data.count;
          return (
            <span
              class={{
                'bold-number': true,
                'green-number': isSuccess,
                'red-number': isFailed,
              }}>
              {data.delivery_count || 0}
            </span>
          );
        },
        width: 100,
      },
    );

    return columns;
  });

  const handleStatusTabChange = (key: StatusKey) => {
    activeStatusTab.value = key;
    selectedRows.value = [];
    tableRef.value?.clearSelection();
  };

  const handleSelectionChange = ({ checked, isAll, row }: { checked: boolean; isAll: boolean; row: RowData }) => {
    if (isAll) {
      // 全选/取消全选
      if (checked) {
        // 只选中失败状态的行
        selectedRows.value = filteredTableData.value.filter((item) => item.status === TicketModel.STATUS_FAILED);
      } else {
        selectedRows.value = [];
      }
    } else {
      // 单行选择
      if (checked) {
        selectedRows.value.push(row);
      } else {
        selectedRows.value = selectedRows.value.filter((item) => item.id !== row.id);
      }
    }
  };

  const handleClearSelection = () => {
    selectedRows.value = [];
    tableRef.value?.clearSelection();
  };

  const handleBatchTerminate = () => {
    if (selectedRows.value.length === 0) return;
    terminateForm.remark = '';
    isShowTerminateDialog.value = true;
  };

  const handleConfirmTerminate = async () => {
    try {
      await terminateFormRef.value?.validate();
      isTerminating.value = true;

      await batchProcessTicket({
        action: 'TERMINATE',
        params: {
          remark: terminateForm.remark,
        },
        ticket_ids: selectedRows.value.map((item) => item.id),
      });

      messageSuccess(t('批量终止成功'));
      isShowTerminateDialog.value = false;
      handleClearSelection();
      fetchData();
    } finally {
      isTerminating.value = false;
    }
  };

  const handleExportAll = async () => {
    if (!props.id) return;

    try {
      isExporting.value = true;
      // 导出所有单据明细，使用后端接口
      await exportReplenishTickets({ replenish_record_ids: [props.id] });

      messageSuccess(t('导出成功'));
    } finally {
      isExporting.value = false;
    }
  };

  const handleOpenTicketDetail = (ticketData: RowData) => {
    const { href } = router.resolve({
      name: 'ticketDetail',
      params: {
        ticketId: ticketData.id,
      },
    });
    window.open(href, '_blank');
  };

  const handleGoTaskHistoryDetail = (
    _ticketData: RowData,
    data: ServiceReturnType<typeof getInnerFlowInfo>[number][number],
  ) => {
    const { href } = router.resolve({
      name: 'taskHistoryDetail',
      params: {
        root_id: data.flow_id,
      },
    });

    const path = href.replace(/^\/(\d+)/, `${systemEnvironStore.urls.RESOURCE_INDEPENDENT_BIZ}`);
    window.open(`${window.location.origin}/${path}`, '_blank');
  };

  const fetchData = async () => {
    if (!props.id) return;

    try {
      isLoading.value = true;

      // 获取补货记录摘要信息
      const replenishData = await fetchReplenish({ id: props.id });
      if (replenishData.results.length > 0) {
        const record = replenishData.results[0];
        summaryInfo.value = {
          create_at: record.create_at,
          creator: record.creator,
          details: record.details,
        };

        // 获取关联单据
        const ticketIds = record.ticket_ids;
        if (ticketIds.length > 0) {
          // 构建搜索参数
          const searchParams: Parameters<typeof getTickets>[0] = {
            ids: ticketIds.join(','),
            limit: 1000,
            offset: 0,
            ticket_type: TicketTypes.RESOURCE_HCM_REPLENISH,
          };

          // 单号筛选
          if (quickSearchValue.value.id) {
            searchParams.ids = quickSearchValue.value.id;
          }

          // DB 类型筛选
          if (quickSearchValue.value.db_type) {
            const dbTypes = Array.isArray(quickSearchValue.value.db_type)
              ? quickSearchValue.value.db_type
              : [quickSearchValue.value.db_type];
            searchParams.replenish_db_type = dbTypes.join(',');
          }

          // 获取单据详情（使用批量接口）
          const ticketIdsStr = ticketIds.join(',');
          const [ticketsRes, innerFlowInfo, applyInfo] = await Promise.all([
            getTickets(searchParams),
            getInnerFlowInfo({ ticket_ids: ticketIdsStr }),
            listTicketApplyInfo({ ticket_ids: ticketIdsStr }),
          ]);

          ticketInnerFlowInfo.value = innerFlowInfo;

          tableData.value = ticketsRes.results.map((item) => {
            const applyInfoItem = applyInfo[item.id] || {};
            return {
              ...item,
              ...applyInfoItem,
              ...applyInfoItem.details,
            } as unknown as RowData;
          });
        }
      }
    } finally {
      isLoading.value = false;
    }
  };

  watch(
    isShow,
    () => {
      if (isShow.value && props.id) {
        fetchData();
      }
    },
    {
      immediate: true,
    },
  );

  // 监听搜索条件变化
  watch(
    quickSearchValue,
    () => {
      if (isShow.value && props.id) {
        fetchData();
      }
    },
    {
      deep: true,
    },
  );
</script>

<style lang="less">
  .replenish-record-details-slider {
    .header-desc {
      position: relative;
      display: inline-flex;
      align-items: center;
      padding-left: 12px;
      margin-left: 8px;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 13px;
      line-height: 22px;
      letter-spacing: 0;
      color: #979ba5;
      font-weight: 400;

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 1px;
        height: 14px;
        background: #dcdee5;
      }
    }

    .replenish-record-details {
      padding: 16px 24px 16px;
    }

    .slide-summary {
      display: flex;
      align-items: center;
      gap: 24px;
      padding: 12px 16px;
      background: #f5f7fa;
      border-radius: 4px;
      margin-bottom: 16px;
      flex-wrap: wrap;

      .summary-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: #63656e;
        white-space: nowrap;
      }

      .summary-label {
        color: #979ba5;
      }

      .summary-value {
        color: #313238;
        font-weight: 500;

        .db-count {
          display: inline-flex;
          align-items: center;
          gap: 2px;
          margin-right: 8px;
        }
      }

      .summary-divider {
        width: 1px;
        height: 16px;
        background: #dcdee5;
      }
    }

    .slide-toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;

      .status-tab-group {
        display: inline-flex;
        align-items: center;
        flex-shrink: 0;
      }

      .slide-status-tab {
        padding: 4px 12px;
        font-size: 13px;
        color: #63656e;
        cursor: pointer;
        border: 1px solid #dcdee5;
        transition: all 0.15s;
        white-space: nowrap;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: #fff;
        margin-right: -1px;
        height: 32px;
        box-sizing: border-box;

        &:first-child {
          border-radius: 2px 0 0 2px;
        }

        &:last-child {
          border-radius: 0 2px 2px 0;
          margin-right: 0;
        }

        &:hover {
          color: #3a84ff;
          border-color: #3a84ff;
          z-index: 1;
          position: relative;
        }

        &.active {
          color: #3a84ff;
          border-color: #3a84ff;
          background: #e1ecff;
          font-weight: 500;
          z-index: 1;
          position: relative;
        }

        .tab-count {
          display: inline-block;
          min-width: 16px;
          height: 16px;
          padding: 0 4px;
          border-radius: 8px;
          font-size: 11px;
          font-weight: 500;
          background: #f0f1f5;
          color: #979ba5;
          line-height: 16px;
          text-align: center;
          box-sizing: border-box;
          vertical-align: middle;

          &.active {
            background: #3a84ff;
            color: #fff;
          }
        }
      }

      .batch-terminate-btn {
        margin-left: 12px;

        &:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
      }

      .batch-info {
        font-size: 12px;
        color: #63656e;
        display: flex;
        align-items: center;
        gap: 6px;

        .batch-count {
          color: #3a84ff;
          font-weight: 500;
        }
      }

      .slide-search-select {
        width: 400px;
        min-width: 200px;
        margin-left: auto;
      }
    }

    .slide-footer {
      padding: 12px 0;
      border-top: 1px solid #f0f1f5;
      margin-top: 12px;

      .footer-total {
        font-size: 12px;
        color: #979ba5;
      }
    }

    .bold-number {
      font-family: MicrosoftYaHei-Bold;
      font-weight: 700;
      font-size: 12px;
      color: #4d4f56;
    }

    .green-number {
      color: #2caf5e;
    }

    .red-number {
      color: #ea3636;
    }

    // 表格内单元格间距优化
    .bk-table {
      .bk-table-head th {
        font-size: 12px;
        font-weight: 500;
        color: #313238;
        background: #f5f7fa;
        white-space: nowrap;
      }

      .bk-table-body td {
        font-size: 13px;
        color: #313238;
        white-space: nowrap;
      }

      // 复选框列居中
      .bk-checkbox {
        vertical-align: middle;
      }
    }
  }
</style>
