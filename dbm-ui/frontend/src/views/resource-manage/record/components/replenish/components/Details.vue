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
    width="65%">
    <template #header>
      <span>{{ t('记录明细详情') }}</span>
      <span class="header-desc">ID：{{ id }}</span>
    </template>
    <div class="replenish-record-details">
      <BkLoading :loading="isLoading">
        <!-- 摘要信息区 -->
        <div class="slide-summary">
          <div class="summary-item">
            <span class="summary-label">{{ t('补货数量') }}：</span>
            <span class="summary-value">
              <template
                v-for="(value, db) in summaryInfo.details"
                :key="db">
                <span class="db-count">
                  {{ dbNameMap[db] }}：<span class="db-count-value">{{ value }}</span>
                </span>
              </template>
            </span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('申请人') }}：</span>
            <span class="summary-value">{{ summaryInfo.creator || '--' }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ t('申请时间') }}：</span>
            <span class="summary-value">{{
              summaryInfo.create_at ? utcDisplayTime(summaryInfo.create_at) : '--'
            }}</span>
          </div>
        </div>

        <!-- 关联单据标题 -->
        <div class="related-tickets-title">{{ t('关联单据') }}</div>

        <!-- 工具栏：状态Tab + 批量终止 + 导出 + 搜索 -->
        <div class="slide-toolbar">
          <BkRadioGroup
            v-model="activeStatusTab"
            type="capsule"
            @change="handleStatusTabChange">
            <BkRadioButton
              v-for="tab in statusTabs"
              :key="tab.key"
              :label="tab.key">
              {{ tab.label }} ( {{ statusCountMap[tab.key] || 0 }} )
            </BkRadioButton>
          </BkRadioGroup>

          <BkButton
            class="batch-terminate-btn"
            :disabled="selectedRows.length === 0"
            :loading="isTerminating"
            @click="handleBatchTerminate">
            <DbIcon
              class="mr-4"
              type="bk-dbm-icon db-icon-stop" />
            {{ t('批量终止') }}
          </BkButton>

          <BkButton
            v-bk-tooltips="t('导出该补货操作关联的所有单据明细，不受当前筛选条件影响')"
            :loading="isExporting"
            @click="handleExportAll">
            <DbIcon
              class="mr-4"
              type="bk-dbm-icon db-icon-daochu-2" />
            {{ t('导出全部') }}
          </BkButton>

          <div class="slide-search-select">
            <DbQuickSearch
              v-model="quickSearchValue"
              :data="slideQuickSearchData"
              :placeholder="t('搜索单号、DB 类型')"
              style="width: 100%" />
          </div>
        </div>

        <!-- 表格 -->
        <BkTable
          ref="tableRef"
          border
          :columns="tableColumns"
          :data="filteredTableData"
          :is-row-select-enable="isRowSelectEnable"
          :max-height="tableMaxHeight"
          @checkbox-all="handleCheckboxAll"
          @checkbox-change="handleCheckboxChange" />
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
          class="mr-8"
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
  import { batchProcessTicket } from '@services/source/ticketFlow';

  import { DBTypeInfos, TicketTypes } from '@common/const';

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

  // 状态图标映射
  const statusIconMap: Record<string, string> = {
    [TicketModel.STATUS_APPROVE]: 'sync-default',
    [TicketModel.STATUS_FAILED]: 'sync-failed',
    [TicketModel.STATUS_INNER_TODO]: 'sync-default',
    [TicketModel.STATUS_PENDING]: 'sync-default',
    [TicketModel.STATUS_RESOURCE_REPLENISH]: 'sync-default',
    [TicketModel.STATUS_REVOKED]: 'sync-failed',
    [TicketModel.STATUS_RUNNING]: 'sync-pending',
    [TicketModel.STATUS_SUCCEEDED]: 'sync-success',
    [TicketModel.STATUS_TERMINATED]: 'sync-failed',
    [TicketModel.STATUS_TIMER]: 'sync-pending',
    [TicketModel.STATUS_TODO]: 'sync-default',
  };

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
    const columns: any[] = [];

    columns.push({
      fixed: 'left',
      type: 'checkbox',
      width: 50,
    });

    columns.push(
      {
        field: 'spec',
        label: t('规格'),
        minWidth: 280,
        render: ({ data }: { data: RowData }) => {
          const dbName = dbNameMap[data.db_type] || '--';
          const machineType = machineTypeMap[data.spec?.spec_machine_type] || '--';
          const specName = data.spec?.spec_name || '--';
          return (
            <span class='spec-cell'>
              {dbName} / {machineType} / {specName}
            </span>
          );
        },
      },
      {
        field: 'subzone',
        label: t('园区'),
        render: ({ data }: { data: RowData }) => {
          const city = data.city || '';
          const subzone = data.subzone || '';
          return city && subzone ? `${city}-${subzone}` : city || subzone || '--';
        },
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
        label: t('补充数量'),
        render: ({ data }: { data: RowData }) => <span class='bold-number'>{data.count || 0}</span>,
        width: 100,
      },
      {
        field: 'id',
        label: t('关联补货单'),
        render: ({ data }: { data: RowData }) => (
          <bk-button
            onClick={() => handleOpenTicketDetail(data)}
            text
            theme='primary'>
            {data.id}
          </bk-button>
        ),
        width: 120,
      },
      {
        field: 'status',
        label: t('操作结果'),
        render: ({ data }: { data: RowData }) => {
          const iconType = statusIconMap[data.status] || 'sync-default';
          const isRunning = iconType === 'sync-pending';
          return (
            <span class='status-cell'>
              <db-icon
                class={{ 'rotate-loading': isRunning }}
                svg
                type={iconType}
              />
              <span class='ml-4'>{data.status_display}</span>
            </span>
          );
        },
        width: 120,
      },
    );

    return columns;
  });

  // 判断行是否可选（只有失败状态的行可选）
  const isRowSelectEnable = ({ row }: { row: RowData }) => {
    return row.status === TicketModel.STATUS_FAILED;
  };

  const handleStatusTabChange = (key: StatusKey) => {
    activeStatusTab.value = key;
    selectedRows.value = [];
    tableRef.value?.clearSelection();
  };

  // 全选/取消全选
  const handleCheckboxAll = ({ checked }: { checked: boolean }) => {
    if (checked) {
      // 只选中失败状态的行
      selectedRows.value = filteredTableData.value.filter((item) => item.status === TicketModel.STATUS_FAILED);
    } else {
      selectedRows.value = [];
    }
  };

  // 单行选择
  const handleCheckboxChange = ({ checked, row }: { checked: boolean; row: RowData }) => {
    if (checked) {
      const index = selectedRows.value.findIndex((item) => item.id === row.id);
      if (index === -1) {
        selectedRows.value.push(row);
      }
    } else {
      selectedRows.value = selectedRows.value.filter((item) => item.id !== row.id);
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
          const [ticketsRes, applyInfo] = await Promise.all([
            getTickets(searchParams),
            listTicketApplyInfo({ ticket_ids: ticketIdsStr }),
          ]);

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
        selectedRows.value = [];
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
      gap: 32px;
      padding: 12px 16px;
      margin-bottom: 24px;
      flex-wrap: wrap;
      background: #f5f7fa;
      border-radius: 2px;

      .summary-item {
        display: flex;
        align-items: center;
        font-size: 12px;
        color: #63656e;
        white-space: nowrap;
      }

      .summary-label {
        color: #979ba5;
      }

      .summary-value {
        color: #313238;

        .db-count {
          display: inline-flex;
          align-items: center;
          margin-right: 12px;
          color: #63656e;

          .db-count-value {
            font-weight: 700;
            color: #313238;
            margin-left: 2px;
          }
        }
      }
    }

    .related-tickets-title {
      font-size: 14px;
      font-weight: 700;
      color: #313238;
      margin-bottom: 16px;
    }

    .slide-toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;

      .batch-terminate-btn {
        margin-left: 8px;

        &:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
      }

      .slide-search-select {
        width: 400px;
        min-width: 200px;
        margin-left: auto;
      }
    }

    .bold-number {
      font-family: MicrosoftYaHei-Bold;
      font-weight: 700;
      font-size: 12px;
      color: #313238;
    }

    .spec-cell {
      color: #313238;
    }

    .status-cell {
      display: inline-flex;
      align-items: center;
      vertical-align: middle;

      .rotate-loading {
        animation: rotate-loading 1s linear infinite;
      }
    }

    @keyframes rotate-loading {
      from {
        transform: rotate(0deg);
      }

      to {
        transform: rotate(360deg);
      }
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
