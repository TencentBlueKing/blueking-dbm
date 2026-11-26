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
  <div class="ticket-flow-list-content">
    <BkAlert
      class="mb-16"
      closable>
      {{
        t(
          '审批、确认执行各自按步骤控制来源展示：平台设置可编辑；单据预设、逐单判定的值后加锁，本页不可修改。待审批、待执行超时按对应步骤的控制来源提供。',
        )
      }}
    </BkAlert>
    <div class="top-operation">
      <span
        v-for="action in batchActions"
        :key="action.mode"
        v-bk-tooltips="{ content: batchDisabledReason(action.mode), disabled: !batchDisabledReason(action.mode) }">
        <BkButton
          v-if="batchDisabledReason(action.mode)"
          disabled>
          {{ action.label }}
        </BkButton>
        <AuthButton
          v-else
          action-id="ticket_config_set"
          :permission="selected.every((row) => row.permission.ticket_config_set)"
          :resource="dbType"
          @click="handleBatchEdit(action.mode)">
          {{ action.label }}
        </AuthButton>
      </span>
      <div
        v-if="selected.length"
        class="selection-info">
        <I18nT
          keypath="已选 n 项"
          scope="global"
          tag="span">
          <template #n>
            <span class="selection-count">{{ selected.length }}</span>
          </template>
        </I18nT>
        <BkButton
          text
          theme="primary"
          @click="clearSelection">
          {{ t('清空选择') }}
        </BkButton>
      </div>
      <DbQuickSearch
        v-model="searchValue"
        class="input-box"
        :data="searchSelectList" />
    </div>
    <div
      ref="tableContentRef"
      class="table-content">
      <DbTable
        ref="table"
        :bk-ui-settings="settings"
        class="table-box"
        :data-source="queryList"
        :default-limit="20"
        :disable-select-method="disableSelect"
        fixed-pagination
        row-key="id"
        selectable
        @bk-ui-settings-change="updateTableSettings"
        @clear-search="handleClearSearch"
        @selection="handleSelection">
        <TableColumn
          col-key="ticket_type_display"
          :min-width="220"
          :title="t('单据类型')">
          <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
            <AuthButton
              action-id="ticket_config_set"
              :permission="data.permission.ticket_config_set"
              :resource="dbType"
              text
              theme="primary"
              @click="handleEdit(data)">
              {{ data.ticket_type_display }}
            </AuthButton>
          </template>
        </TableColumn>
        <TableColumn
          col-key="ticket_type"
          ellipsis
          :min-width="200"
          :title="t('单据 ID')" />
        <TableColumn
          v-for="field in flowFields"
          :key="field.key"
          :col-key="field.key"
          :min-width="120"
          :title="field.label">
          <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
            {{ flowValueText(data, field.key) }}
            <DbIcon
              v-if="data[`editable_${field.key}`] !== true"
              v-bk-tooltips="flowLockedHint(data, field.key)"
              class="ml-4"
              type="lock-fill" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="expire_config"
          :min-width="280"
          :title="t('超时自动终止')">
          <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
            <TimeoutSummary :data="data" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="updater"
          ellipsis
          :min-width="140"
          :title="t('更新人')">
          <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
            <bk-user-display-name
              v-if="data.updater"
              :user-id="data.updater" />
            <span v-else>--</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="update_at"
          ellipsis
          :min-width="180"
          sorter
          :title="t('更新时间')">
          <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
            {{ data.update_at ? data.updateAtDisplay : '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="operations"
          :min-width="80"
          :title="t('操作')">
          <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
            <AuthButton
              action-id="ticket_config_set"
              :permission="data.permission.ticket_config_set"
              :resource="dbType"
              text
              theme="primary"
              @click="handleEdit(data)">
              {{ t('编辑') }}
            </AuthButton>
          </template>
        </TableColumn>
      </DbTable>
    </div>
  </div>
  <EditConfigSide
    v-model:is-show="isShowEdit"
    :data="editingRow"
    @success="fetchData" />
  <BatchConfigDialog
    v-model:is-show="isShowBatch"
    :mode="batchMode"
    :rows="batchRows"
    @success="fetchData" />
</template>

<script setup lang="ts">
  import { I18nT, useI18n } from 'vue-i18n';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { queryTicketFlowDescribe } from '@services/source/ticket';

  import { useTableSettings } from '@hooks';

  import { type DBTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { useResizeObserver } from '@vueuse/core';

  import { useSearchSelect } from '../hooks/use-search-select';

  import BatchConfigDialog, { type BatchMode } from './BatchConfigDialog.vue';
  import EditConfigSide from './EditConfigSide.vue';
  import TimeoutSummary from './TimeoutSummary.vue';

  interface Props {
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const table = ref<InstanceType<typeof DbTable>>();
  const tableContentRef = ref<HTMLElement>();
  const searchValue = ref<Record<string, string>>({});
  const selected = shallowRef<TicketFlowDescribeModel[]>([]);
  const editingRow = shallowRef(new TicketFlowDescribeModel());
  const batchRows = shallowRef<TicketFlowDescribeModel[]>([]);
  const batchMode = ref<BatchMode>('approve');
  const isShowEdit = ref(false);
  const isShowBatch = ref(false);

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TICKET_FLOW_GLOBAL_SETTINGS, {
    checked: [
      'ticket_type_display',
      'need_itsm',
      'need_manual_confirm',
      'expire_config',
      'updater',
      'update_at',
      'operations',
    ],
    disabled: ['ticket_type_display'],
    order: [
      'ticket_type_display',
      'ticket_type',
      'need_itsm',
      'need_manual_confirm',
      'expire_config',
      'updater',
      'update_at',
      'operations',
    ],
  });
  const batchActions: { label: string; mode: BatchMode }[] = [
    { label: t('批量设置审批'), mode: 'approve' },
    { label: t('批量设置确认执行'), mode: 'confirm' },
    { label: t('批量设置超时'), mode: 'timeout' },
  ];

  const { searchSelectList } = useSearchSelect();
  type FlowKey = 'need_itsm' | 'need_manual_confirm';
  const flowFields: { key: FlowKey; label: string }[] = [
    { key: 'need_itsm', label: t('审批') },
    { key: 'need_manual_confirm', label: t('确认执行') },
  ];
  const flowValueText = (row: TicketFlowDescribeModel, key: FlowKey) => {
    if (row[`editable_${key}`] === null) return t('逐单判定');
    return key === 'need_itsm'
      ? row.configs[key]
        ? t('需审批')
        : t('免审批')
      : row.configs[key]
        ? t('需确认')
        : t('免确认');
  };
  const flowLockedHint = (row: TicketFlowDescribeModel, key: FlowKey) =>
    row[`editable_${key}`] === null
      ? t('取值不固定；由该单据在提交时按提单内容判定，本页不可修改')
      : t('固定为{value}；由该单据流程预先确定，本页不可修改', { value: flowValueText(row, key) });

  const batchDisabledReason = (mode: BatchMode) => {
    if (!selected.value.length) return t('请先勾选要批量设置的单据类型');
    const key = mode === 'approve' ? 'editable_need_itsm' : 'editable_need_manual_confirm';
    if (mode !== 'timeout' && !selected.value.some((row) => row[key] === true)) {
      return mode === 'approve' ? t('所选单据类型的审批均不由本页设置') : t('所选单据类型的确认执行均不由本页设置');
    }
    return '';
  };
  const disableSelect = (row: TicketFlowDescribeModel) => !row.permission.ticket_config_set;

  // 接口返回类型全集；包含筛选、组合条件、自然序与分页均在全局页处理，不改变业务页查询契约。
  const queryList = async (params: Record<string, unknown>) => {
    const filters: Record<string, string> = {};
    Object.entries(params).forEach(([key, value]) => {
      if (typeof value === 'string') filters[key] = value;
    });
    const { results } = await queryTicketFlowDescribe({ db_type: props.dbType });
    const matched = results.filter((row) => {
      if (filters.db_type && !filters.db_type.split(',').includes(props.dbType)) return false;
      if (filters.ticket_type__in && !filters.ticket_type__in.split(',').includes(row.ticket_type)) return false;
      for (const key of ['need_itsm', 'need_manual_confirm'] as const) {
        const value = row[`editable_${key}`] === null ? 'null' : String(row.configs[key]);
        if (filters[key] && !filters[key].split(',').includes(value)) return false;
      }
      const timestamp = new Date(row.update_at).getTime();
      if (
        filters.update_at__gte &&
        (!Number.isFinite(timestamp) || timestamp < new Date(filters.update_at__gte).getTime())
      )
        return false;
      if (
        filters.update_at__lte &&
        (!Number.isFinite(timestamp) || timestamp > new Date(filters.update_at__lte).getTime())
      )
        return false;
      return true;
    });
    const ordering = typeof params.ordering === 'string' ? params.ordering : '';
    const collator = new Intl.Collator('zh-CN', { numeric: true });
    matched.sort((a, b) => {
      if (ordering === 'update_at' || ordering === '-update_at') {
        const diff = new Date(a.update_at || 0).getTime() - new Date(b.update_at || 0).getTime();
        return ordering.startsWith('-') ? -diff : diff;
      }
      return collator.compare(a.ticket_type_display, b.ticket_type_display);
    });
    const limit = Number(params.limit ?? 20);
    const offset = Number(params.offset ?? 0);
    return {
      count: matched.length,
      results: limit < 0 ? matched : matched.slice(offset, offset + limit),
    };
  };

  // 表格占用剩余空间，提示条关闭或窗口变化时同步更新内部滚动高度。
  useResizeObserver(tableContentRef, () => {
    table.value?.updateTableHeight(tableContentRef.value!.clientHeight);
  });

  const fetchData = () => table.value?.fetchData({ db_type: props.dbType, ...searchValue.value });
  const clearSelection = () => {
    selected.value.forEach((row) => table.value?.removeSelectByKey(String(row.id)));
    selected.value = [];
  };
  const handleSelection = (_ids: string[], rows: TicketFlowDescribeModel[]) => {
    selected.value = rows;
  };
  const handleEdit = (row: TicketFlowDescribeModel) => {
    editingRow.value = row;
    isShowEdit.value = true;
  };
  const handleBatchEdit = (mode: BatchMode) => {
    if (batchDisabledReason(mode)) return;
    batchMode.value = mode;
    batchRows.value = [...selected.value];
    isShowBatch.value = true;
  };
  const handleClearSearch = () => {
    searchValue.value = {};
  };

  watch(searchValue, () => {
    clearSelection();
    fetchData();
  });
  watch(
    () => props.dbType,
    () => {
      searchValue.value = {};
    },
  );
  onMounted(fetchData);
</script>

<style lang="less" scoped>
  .ticket-flow-list-content {
    display: flex;
    height: 100%;
    padding: 16px 24px;
    overflow: hidden;
    flex-direction: column;

    > .bk-alert {
      flex-shrink: 0;
    }

    .table-content {
      flex: 1;
      min-height: 0;
      overflow: hidden;
    }

    .top-operation {
      display: flex;
      width: 100%;
      align-items: center;
      flex-shrink: 0;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;

      .selection-info {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #63656e;
        white-space: nowrap;

        .selection-count {
          font-weight: 500;
          color: #3a84ff;
        }
      }

      .input-box {
        width: 550px;
        margin-left: auto;
      }
    }
  }
</style>
