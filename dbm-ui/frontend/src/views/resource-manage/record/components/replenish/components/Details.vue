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
      <span>{{ t('补货详情') }}</span>
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
            v-if="showBatchOperation"
            :disabled="selectedRows.length === 0"
            :loading="isRetrying"
            @click="handleBatchRetry">
            <DbIcon
              class="mr-4"
              type="bk-dbm-icon db-icon-refresh" />
            {{ t('批量重试') }}
          </BkButton>
          <BkButton
            v-if="showBatchOperation"
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
        <PrimaryTable
          :data="filteredTableData"
          :max-height="tableMaxHeight"
          resizable
          row-key="id"
          title-ellipsis>
          <!-- 勾选列：仅在全部和已失败 tab 下展示 -->
          <TableColumn
            v-if="showBatchOperation"
            align="center"
            col-key="row-select"
            fixed="left"
            :width="50">
            <template #title>
              <BkCheckbox
                :model-value="isPageAllSelected"
                @change="handleTogglePageSelect" />
            </template>
            <template #default="{ row }: { row: RowData }">
              <BkCheckbox
                :disabled="row.status !== TicketModel.STATUS_FAILED"
                :model-value="Boolean(selectedRowMap[row.id])"
                @change="() => handleRowSelect(row)" />
            </template>
          </TableColumn>
          <!-- 单号 -->
          <TableColumn
            col-key="id"
            fixed="left"
            :title="t('单号')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              <BkButton
                text
                theme="primary"
                @click="handleOpenTicketDetail(row)">
                {{ row.id }}
              </BkButton>
            </template>
          </TableColumn>
          <!-- 子任务 -->
          <TableColumn
            col-key="inner_flow"
            :title="t('子任务')"
            :width="150">
            <template #default="{ row }: { row: RowData }">
              <template v-if="ticketInnerFlowInfo[row.id]">
                <div
                  v-for="(flowItem, index) in ticketInnerFlowInfo[row.id]"
                  :key="index"
                  style="line-height: 26px">
                  <BkButton
                    text
                    theme="primary"
                    @click="handleGoTaskHistoryDetail(row, flowItem)">
                    {{ flowItem.flow_alias }}
                  </BkButton>
                </div>
                <span v-if="ticketInnerFlowInfo[row.id]!.length < 1">--</span>
              </template>
              <div
                v-else
                class="rotate-loading"
                style="display: inline-block">
                <DbIcon
                  svg
                  type="sync-pending" />
              </div>
            </template>
          </TableColumn>
          <!-- 状态列：仅在全部 tab 下展示 -->
          <TableColumn
            v-if="activeStatusTab === 'all'"
            col-key="status"
            :title="t('状态')"
            :width="120">
            <template #default="{ row }: { row: RowData }">
              <TicketStatusTag
                :key="row.renderKey"
                :data="{
                  status: row.status,
                  statusText: row.status_display,
                }" />
            </template>
          </TableColumn>
          <!-- DB 类型 -->
          <TableColumn
            col-key="db_type"
            :title="t('DB 类型')"
            :width="120">
            <template #default="{ row }: { row: RowData }">
              {{ dbNameMap[row.db_type] || '--' }}
            </template>
          </TableColumn>
          <!-- 规格类型 -->
          <TableColumn
            col-key="spec_machine_type"
            :min-width="150"
            :title="t('规格类型')">
            <template #default="{ row }: { row: RowData }">
              {{ machineTypeMap[row.spec?.spec_machine_type] || '--' }}
            </template>
          </TableColumn>
          <!-- 规格 -->
          <TableColumn
            col-key="spec_name"
            :min-width="180"
            :title="t('规格')">
            <template #default="{ row }: { row: RowData }">
              {{ row.spec?.spec_name || '--' }}
            </template>
          </TableColumn>
          <!-- 地域 -->
          <TableColumn
            col-key="city"
            :title="t('地域')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              {{ row.city || '--' }}
            </template>
          </TableColumn>
          <!-- 园区 -->
          <TableColumn
            col-key="subzone"
            :title="t('园区')"
            :width="120">
            <template #default="{ row }: { row: RowData }">
              {{ row.subzone || '--' }}
            </template>
          </TableColumn>
          <!-- 操作系统 -->
          <TableColumn
            col-key="os_name"
            :title="t('操作系统')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              {{ row.os_name || '--' }}
            </template>
          </TableColumn>
          <!-- 申请数量 -->
          <TableColumn
            col-key="count"
            :title="t('申请数量')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              <span class="bold-number">{{ row.count || 0 }}</span>
            </template>
          </TableColumn>
          <!-- 已交付 -->
          <TableColumn
            col-key="delivery_count"
            :title="t('已交付')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              <span
                class="bold-number"
                :class="{
                  'green-number': row.delivery_count === row.count,
                  'red-number': row.delivery_count < row.count,
                }">
                {{ row.delivery_count || 0 }}
              </span>
            </template>
          </TableColumn>
        </PrimaryTable>
      </BkLoading>
    </div>

    <!-- 批量终止弹窗 -->
    <BkDialog
      v-model:is-show="isShowTerminateDialog"
      class="replenish-batch-terminate-dialog"
      :title="t('批量终止')"
      :width="480">
      <BkForm
        ref="terminateFormRef"
        form-type="vertical"
        :model="terminateForm"
        :rules="terminateFormRules">
        <BkFormItem
          :label="t('操作意见')"
          property="action"
          required>
          <StatusFailedAction v-model="terminateForm.action" />
        </BkFormItem>
        <BkFormItem
          :label="t('意见')"
          property="remark"
          required>
          <BkInput
            v-model="terminateForm.remark"
            :maxlength="100"
            :placeholder="t('请输入')"
            :rows="3"
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
        <BkButton
          class="ml-8"
          :disabled="isTerminating"
          @click="isShowTerminateDialog = false">
          {{ t('取消') }}
        </BkButton>
      </template>
    </BkDialog>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel from '@services/model/ticket/ticket';
  import {
    batchRetryReplenishTickets,
    exportReplenishTickets,
    fetchReplenish,
    listTicketApplyInfo,
  } from '@services/source/dbresourceReplenish';
  import { getTickets, getTicketStatus } from '@services/source/ticket';
  import { getInnerFlowInfo, revokeTicket } from '@services/source/ticketFlow';

  import { useSystemEnviron } from '@stores';

  import { DBTypeInfos, TicketTypes } from '@common/const';

  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import StatusFailedAction from '@views/ticket-center/ticket-self-todo/components/batch-operation/StatusFailedAction.vue';

  import { messageSuccess, random, utcDisplayTime } from '@utils';

  import { useTimeoutFn } from '@vueuse/core';

  type StatusKey = 'all' | 'FAILED' | 'RUNNING' | 'SUCCEEDED' | 'TERMINATED';

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
    renderKey: string;
    spec: {
      spec_machine_type: string;
      spec_name: string;
    };
    status: string;
    statusIcon: string;
    statusText: string;
    sub_ticket_id: number;
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

  const tableData = shallowRef<RowData[]>([]);
  const isLoading = shallowRef(false);
  const isExporting = ref(false);
  const activeStatusTab = ref<StatusKey>('all');
  const quickSearchValue = ref<Record<string, any>>({});
  const isShowTerminateDialog = ref(false);
  const isTerminating = ref(false);
  const terminateFormRef = ref();
  const isRetrying = ref(false);
  const ticketInnerFlowInfo = shallowRef<ServiceReturnType<typeof getInnerFlowInfo>>({});

  const shouldPoll = ref(false);

  const summaryInfo = ref({
    create_at: '',
    creator: '',
    details: {} as Record<string, number>,
  });

  const terminateForm = reactive({
    action: 'TERMINATE',
    remark: '',
  });

  const terminateFormRules = {
    remark: [{ message: t('意见不能为空'), required: true, trigger: 'blur' }],
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
    { key: TicketModel.STATUS_FAILED, label: t('已失败') },
    { key: TicketModel.STATUS_RUNNING, label: t('执行中') },
    { key: TicketModel.STATUS_SUCCEEDED, label: t('已完成') },
    { key: TicketModel.STATUS_TERMINATED, label: t('已终止') },
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
      [TicketModel.STATUS_FAILED]: 0,
      [TicketModel.STATUS_RUNNING]: 0,
      [TicketModel.STATUS_SUCCEEDED]: 0,
      [TicketModel.STATUS_TERMINATED]: 0,
    };
    tableData.value.forEach((item) => {
      // 将 APPROVE 状态映射为 RUNNING
      if (item.status === TicketModel.STATUS_APPROVE) {
        map.RUNNING++;
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
      if (activeStatusTab.value === 'RUNNING') {
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

  // 是否展示批量操作（仅全部和已失败 tab）
  const showBatchOperation = computed(
    () => activeStatusTab.value === 'all' || activeStatusTab.value === TicketModel.STATUS_FAILED,
  );

  // 选中行 Map（key 为行 id）
  const selectedRowMap = ref<Record<number, RowData>>({});

  // 选中行列表
  const selectedRows = computed(() => Object.values(selectedRowMap.value));

  // 本页是否全选（仅统计可选行，即失败状态的行）
  const isPageAllSelected = computed(() => {
    const selectableRows = filteredTableData.value.filter((item) => item.status === TicketModel.STATUS_FAILED);
    if (selectableRows.length < 1) return false;
    return selectableRows.every((row) => Boolean(selectedRowMap.value[row.id]));
  });

  // 全选/取消全选（仅选中失败状态的行）
  const handleTogglePageSelect = (checked: boolean) => {
    const map = { ...selectedRowMap.value };
    filteredTableData.value.forEach((row) => {
      if (row.status !== TicketModel.STATUS_FAILED) return;
      if (checked) {
        map[row.id] = row;
      } else {
        delete map[row.id];
      }
    });
    selectedRowMap.value = map;
  };

  // 单行勾选/取消勾选
  const handleRowSelect = (row: RowData) => {
    const map = { ...selectedRowMap.value };
    if (map[row.id]) {
      delete map[row.id];
    } else {
      map[row.id] = row;
    }
    selectedRowMap.value = map;
  };

  const handleStatusTabChange = (key: StatusKey) => {
    activeStatusTab.value = key;
    selectedRowMap.value = {};
  };

  const handleClearSelection = () => {
    selectedRowMap.value = {};
  };

  // 轮询获取单据状态
  const { refresh: fetchTicketStatus } = useRequest(
    () => {
      if (tableData.value.length < 1 || !shouldPoll.value) {
        return Promise.reject();
      }
      return getTicketStatus({
        ticket_ids: tableData.value.map((item) => item.id).join(','),
      });
    },
    {
      manual: true,
      onSuccess(data: Record<string, string>) {
        // 更新 tableData 中对应单据的 status
        tableData.value.forEach((ticketData) => {
          if (data[ticketData.id]) {
            Object.assign(ticketData, {
              renderKey: random(),
              status: data[ticketData.id],
              status_display:
                TicketModel.statusTextMap[data[ticketData.id] as keyof typeof TicketModel.statusTextMap] ||
                data[ticketData.id],
            });
          }
        });
        // 触发 shallowRef 响应式更新
        tableData.value = [...tableData.value];

        // 继续轮询
        if (shouldPoll.value) {
          loopFetchTicketStatus();
        }
      },
    },
  );

  const { start: loopFetchTicketStatus, stop: stopPolling } = useTimeoutFn(() => {
    fetchTicketStatus();
  }, 3000);

  const handleBatchTerminate = () => {
    if (selectedRows.value.length === 0) return;
    terminateForm.remark = '';
    isShowTerminateDialog.value = true;
  };

  const handleConfirmTerminate = async () => {
    try {
      await terminateFormRef.value?.validate();
      isTerminating.value = true;

      await revokeTicket({
        remark: terminateForm.remark,
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

  const handleBatchRetry = () => {
    if (selectedRows.value.length === 0) return;

    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定'),
      content: t('确认后，失败单据将重新发起补货申请。'),
      onConfirm: async () => {
        try {
          isRetrying.value = true;

          await batchRetryReplenishTickets({
            replenish_record_id: props.id,
            ticket_ids: selectedRows.value.map((item) => item.id),
          });

          messageSuccess(t('批量重试成功'));
          handleClearSelection();
          fetchData();
        } finally {
          isRetrying.value = false;
        }
      },
      title: t('确认批量重试 {count} 个单据', { count: selectedRows.value.length }),
    });
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

          // 启动轮询
          if (tableData.value.length > 0) {
            shouldPoll.value = true;
            fetchTicketStatus();
          }
        }
      }
    } finally {
      isLoading.value = false;
    }
  };

  watch(
    isShow,
    (newVal) => {
      if (newVal && props.id) {
        selectedRowMap.value = {};
        fetchData();
      } else {
        // 停止轮询
        shouldPoll.value = false;
        stopPolling();
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
  .replenish-batch-terminate-dialog {
    .bk-form-label {
      color: #63656e;
    }
  }

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

      &.red-number {
        color: #ea3636;
      }

      &.green-number {
        color: #2dcb56;
      }
    }

    .delivery-number {
      font-family: MicrosoftYaHei-Bold;
      font-weight: 700;
      font-size: 12px;
      color: #ea3636;
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
