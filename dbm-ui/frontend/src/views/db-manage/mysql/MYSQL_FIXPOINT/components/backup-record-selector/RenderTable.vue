<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="align-center mb-12">
    <div
      class="align-center mr-8"
      style="flex: 1">
      <div class="backup-time-picker">{{ t('备份时间') }}</div>
      <BkDatePicker
        v-model="daterange"
        append-to-body
        clearable
        :disabled-date="disableDate"
        :placeholder="t('请选择')"
        style="width: 100%"
        type="datetimerange"
        @clear="handleDateClear"
        @pick-success="handleDateChange" />
    </div>
    <DbSearchSelect
      v-model="searchSelectValue"
      :data="searchSelectData"
      :placeholder="t('搜索文件名或选择条件搜索')"
      style="flex: 1" />
  </div>
  <BkLoading :loading="loading">
    <BkTable
      ref="tableRef"
      :data="renderData"
      :height="500"
      :max-height="tableMaxHeight"
      :pagination="pagination.count > 0 ? pagination : false"
      @column-filter="handleFilter"
      @page-limit-change="handeChangeLimit"
      @page-value-change="handleChangePage">
      <BkTableColumn
        :label="t('文件名')"
        :min-width="300"
        :width="300">
        <template #header>
          <div class="ml-35">{{ t('备份记录') }}</div>
        </template>
        <template #default="{ row }: { row: BackupLogRecord }">
          <BkRadio
            v-model="checkedBackupId"
            :label="row.backup_id"
            @change="() => handleChecked(row)">
            <div class="ml-12">
              {{ `${row.mysql_role} ${utcDisplayTime(row.backup_time)}` }}
            </div>
          </BkRadio>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="backup_id"
        :label="t('备份 ID')"
        :width="270">
        <template #default="{ row }: { row: BackupLogRecord }">
          {{ row.backup_id }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="backup_type_filter"
        :filter="filterOption.backup_type_filter"
        :label="t('备份类型')">
        <template
          #default="{
            row,
          }: {
            row: BackupLogRecord & { backup_type_display: { label: string; theme: 'warning' | 'info' } };
          }">
          <BkTag
            v-if="row?.backup_type_display?.theme"
            :theme="row.backup_type_display.theme">
            {{ row.backup_type_display.label }}
          </BkTag>
          <span v-else>--</span>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="backup_method"
        :filter="filterOption.backup_method"
        :label="t('备份范围')"
        :width="150">
        <template #default="{ row }: { row: BackupLogRecord & { backup_method_label: string } }">
          <span
            :class="{
              [`backup-method-sign-${row.backup_method}`]: row?.backup_method_label,
            }">
            {{ row?.backup_method_label || '--' }}
          </span>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="backup_tool"
        :filter="filterOption.backup_tool"
        :label="t('备份工具')">
        <template #default="{ row }: { row: BackupLogRecord }">
          {{ row?.backup_tool || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('备份大小')">
        <template #default="{ row }: { row: BackupLogRecord }">
          {{ bytePretty(row?.total_filesize ?? 0) }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('关联单据')">
        <template #default="{ row }: { row: BackupLogRecord }">
          <RouterLink
            v-if="row.bill_id"
            target="_blank"
            :to="{
              name: 'ticketDetail',
              params: {
                ticketId: row.bill_id,
              },
            }">
            {{ row.bill_id }}
          </RouterLink>
          <span v-else>--</span>
        </template>
      </BkTableColumn>
    </BkTable>
  </BkLoading>
</template>
<script setup lang="ts">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type TendbhaModel from '@services/model/mysql/tendbha';
  import {
    type BackupLogRecord,
    queryBackupLogFromBklog,
    queryBackupLogFromLoacal,
  } from '@services/source/fixpointRollback';

  import { useDefaultPagination, useTableMaxHeight } from '@hooks';

  import { bytePretty, getSearchSelectorParams, utcDisplayTime } from '@utils';

  interface Props {
    backupSource: 'local' | 'remote';
    cluster: TendbhaModel;
    /**
     * 仅全备
     */
    onlyFull?: boolean;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<BackupLogRecord>();

  interface Exposes {
    clear(): void;
    init(): void;
  }

  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(240);

  const daterange = ref<[string, string] | [Date, Date]>([
    // dayjs().subtract(30, 'day').format('YYYY-MM-DD 00:00:00'),
    // dayjs().format('YYYY-MM-DD 23:59:59'),
    '',
    '',
  ]);
  // 用于时间选择器点确定时赋值
  const comfirmDaterange = ref<[string, string] | [Date, Date]>(daterange.value);
  const searchSelectValue = ref<ISearchValue[]>([]);
  const searchSelectData = [
    {
      id: 'display',
      multiple: true,
      name: t('文件名'),
    },
  ];
  const tableRef = ref();
  // 存储原始数据（请求到的所有备份记录）
  const originalData = shallowRef<BackupLogRecord[]>([]);
  // 全量结果
  const tableData = shallowRef<BackupLogRecord[]>([]);
  const pagination = ref(useDefaultPagination());
  const loading = ref(false);
  const checkedBackupId = ref<string>();
  // 过滤后的结果
  const filteredData = shallowRef<BackupLogRecord[]>([]);
  const filterOption = ref<
    Record<
      string,
      {
        checked: string[];
        key: string;
        list: { text: string; value: string }[];
      }
    >
  >({
    backup_method: {
      checked: [],
      key: 'backup_method',
      list: [
        {
          text: t('全库备份（例行）'),
          value: 'full_by_regular',
        },
        {
          text: t('全库备份（单据）'),
          value: 'full_by_ticket',
        },
        {
          text: t('库表备份（单据）'),
          value: 'partial_by_ticket',
        },
      ],
    },
    backup_tool: {
      checked: [],
      key: 'backup_tool',
      list: [],
    },
    backup_type_filter: {
      checked: [],
      key: 'backup_type_filter',
      list: [
        {
          text: t('物理备份'),
          value: 'physical',
        },
        {
          text: t('逻辑备份'),
          value: 'logical',
        },
      ],
    },
  });
  const isChecked = (row: any, field: 'backup_method' | 'backup_type_filter' | 'backup_tool') => {
    return filterOption.value[field]?.checked?.length ? filterOption.value[field].checked.includes(row[field]) : true;
  };
  const renderData = computed(() => {
    const [start, end] = comfirmDaterange.value;
    const dateParams =
      start && end
        ? {
            end_time: new Date(end).getTime(),
            start_time: new Date(start).getTime(),
          }
        : undefined;

    const searchParams = getSearchSelectorParams(searchSelectValue.value);

    filteredData.value = [];
    tableData.value.forEach((row) => {
      const timerange = {
        end_time: new Date(row.backup_begin_time).getTime(),
        start_time: new Date(row.backup_begin_time).getTime(),
      };
      const isTimeMatch = !dateParams
        ? true
        : timerange.start_time >= dateParams.start_time && timerange.end_time <= dateParams.end_time;
      const isSearchMatch = !searchParams.display
        ? true
        : `${row.mysql_role} ${utcDisplayTime(row.backup_time)}`.indexOf(searchParams.display) > -1;
      const isFilterChecked =
        isChecked(row, 'backup_type_filter') && isChecked(row, 'backup_method') && isChecked(row, 'backup_tool');
      if (isTimeMatch && isSearchMatch && isFilterChecked) {
        filteredData.value.push(row);
      }
    });

    const { current, limit } = pagination.value;
    const startIndex = (current - 1) * limit;
    const endIndex = startIndex + limit;
    return filteredData.value.slice(startIndex, endIndex);
  });

  watch(filteredData, () => {
    pagination.value.count = filteredData.value.length || tableData.value.length;
  });

  const generateRowData = (row: BackupLogRecord) => {
    const defaultDisplay = {
      backup_type_display: {
        label: '--',
        theme: '',
      },
    };
    const backupTypeMap = {
      logical: {
        backup_type_display: {
          label: t('逻辑备份'),
          theme: 'info',
        },
        backup_type_filter: 'logical', // 用于表头过滤
      },
      physical: {
        backup_type_display: {
          label: t('物理备份'),
          theme: 'warning',
        },
        backup_type_filter: 'physical',
      },
    };
    let backupTypeFilter;
    /**
     * backup_method
      - full_by_ticket: 全库备份（单据）
        可能为物理备份，或者逻辑备份
      - partial_by_ticket: 库表备份（单据）
        逻辑备份，bill_id 不为空
      - full_by_regular: 全库备份（例行）: 可能为物理备份
        或者逻辑备份, bill_id 为空
      - non_full_by_regular: 非全库备份（例行）
        构造，回档，这个应该要过滤掉，备份只有库表结构，权限，不能用户恢复
     */
    if (row.backup_method === 'partial_by_ticket') {
      // 必然是逻辑备份
      backupTypeFilter = Object.assign({}, defaultDisplay, backupTypeMap.logical);
    }

    if (row.backup_type === 'logical') {
      backupTypeFilter = Object.assign({}, defaultDisplay, backupTypeMap.logical);
    } else if (row.backup_type === 'physical') {
      backupTypeFilter = Object.assign({}, defaultDisplay, backupTypeMap.physical);
    }

    const backupMethodMap = {
      full_by_regular: t('全库备份（例行）'),
      full_by_ticket: t('全库备份（单据）'),
      non_full_by_regular: t('非全库备份（例行）'), // 过滤掉，不展示
      partial_by_ticket: t('库表备份（单据）'),
    } as Record<string, string>;

    return {
      ...row,
      backup_method_label: backupMethodMap[row.backup_method] || '--',
      ...backupTypeFilter,
    };
  };

  const fetchData = async () => {
    try {
      loading.value = true;
      let results: BackupLogRecord[] = [];
      if (props.backupSource === 'local') {
        results = await queryBackupLogFromLoacal({
          cluster_id: props.cluster.id,
          limit: -1,
        });
      } else {
        results = await queryBackupLogFromBklog({
          cluster_id: props.cluster.id,
          limit: -1,
        });
      }

      // 仅展示全备记录，需过滤掉库表备份
      if (props.onlyFull) {
        results = results.filter((item) => item.backup_method !== 'partial_by_ticket');
        filterOption.value.backup_method.list.splice(2, 1);
      }

      originalData.value = results;
      tableData.value = results
        .filter((item) => item.backup_method !== 'non_full_by_regular') // 过滤掉例行非全备
        .map((item) => generateRowData(item));

      filterOption.value.backup_tool.list = _.uniqBy(
        results.map((item) => ({
          text: item?.backup_tool,
          value: item?.backup_tool,
        })),
        'text',
      );
      pagination.value.count = results.length;
      checkedBackupId.value = modelValue.value?.backup_id;
    } catch {
      tableData.value = [];
      pagination.value.count = 0;
      checkedBackupId.value = undefined;
    } finally {
      loading.value = false;
    }
  };

  const handleChecked = (row: BackupLogRecord) => {
    checkedBackupId.value = row.backup_id;
    modelValue.value = originalData.value.find((item) => item.backup_id === row.backup_id);
  };

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
    tableRef.value!.getVxeTableInstance().scrollTo(0, 0);
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    handleChangePage(1);
  };

  const disableDate = (date?: Date | number) => dayjs(date).isAfter(dayjs(), 'day');

  const handleDateChange = () => {
    comfirmDaterange.value = daterange.value;
  };

  const handleDateClear = () => {
    comfirmDaterange.value = ['', ''];
  };

  const handleFilter = ({ checked, field }: { checked: string[]; field: string }) => {
    filterOption.value[field].checked = checked;
  };

  fetchData();

  defineExpose<Exposes>({
    clear() {
      if (modelValue.value?.backup_id) {
        checkedBackupId.value = undefined;
        modelValue.value = undefined;
      }
    },
    init() {
      nextTick(() => {
        checkedBackupId.value = modelValue.value?.backup_id;
      });
    },
  });
</script>
<style lang="less" scoped>
  // 全库备份（例行）
  .backup-method-sign-full_by_regular::before {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 6px;
    background-color: #3a84ff;
    content: '';
  }
  // 全库备份（单据）
  .backup-method-sign-full_by_ticket::before {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 6px;
    background-color: #2caf5e;
    content: '';
  }
  //库表备份（单据）
  .backup-method-sign-partial_by_ticket::before {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 6px;
    background-color: #f59500;
    content: '';
  }
</style>
