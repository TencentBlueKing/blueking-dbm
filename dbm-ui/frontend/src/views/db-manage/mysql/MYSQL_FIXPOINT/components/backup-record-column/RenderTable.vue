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
        :clearable="false"
        :disabled-date="disableDate"
        :placeholder="t('请选择')"
        style="width: 100%"
        type="datetimerange"
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
          <div class="ml-35">{{ t('文件名') }}</div>
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
        field="is_full_backup"
        :filter="filterOption.is_full_backup"
        :label="t('备份范围')">
        <template #default="{ row }: { row: BackupLogRecord }">
          {{ row.is_full_backup === '1' ? t('全库备份') : t('库表备份') }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="backup_type"
        :filter="filterOption.backup_type"
        :label="t('备份类型')">
        <template #default="{ row }: { row: BackupLogRecord }">
          {{ row.backup_type === 'logical' ? t('逻辑备份') : t('物理备份') }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="bill_id"
        :filter="filterOption.bill_id"
        :label="t('触发方式')">
        <template #default="{ row }: { row: BackupLogRecord }">
          {{ row.bill_id ? t('单据备份') : t('例行备份') }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="backup_tool"
        :filter="filterOption.backup_tool"
        :label="t('备份工具')">
        <template #default="{ row }: { row: BackupLogRecord }">
          {{ row.extra_fields?.backup_tool || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('备份大小')">
        <template #default="{ row }: { row: BackupLogRecord }">
          {{ bytePretty(row.extra_fields?.total_filesize ?? 0) }}
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
    dayjs().subtract(30, 'day').format('YYYY-MM-DD 00:00:00'),
    dayjs().format('YYYY-MM-DD 23:59:59'),
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
  const tableData = shallowRef<BackupLogRecord[]>([]);
  const pagination = ref(useDefaultPagination());
  const loading = ref(false);
  const checkedBackupId = ref<string>();
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
    backup_tool: {
      checked: [],
      key: 'backup_tool',
      list: [],
    },
    backup_type: {
      checked: [],
      key: 'backup_type',
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
    bill_id: {
      checked: [],
      key: 'bill_id',
      list: [
        {
          text: t('单据备份'),
          value: '1',
        },
        {
          text: t('例行备份'),
          value: '0',
        },
      ],
    },
    is_full_backup: {
      checked: [],
      key: 'is_full_backup',
      list: [
        {
          text: t('库表备份'),
          value: '0',
        },
        {
          text: t('全库备份'),
          value: '1',
        },
      ],
    },
  });
  const isChecked = (row: any, field: 'is_full_backup' | 'bill_id' | 'backup_type' | 'extra_fields.backup_tool') => {
    const cloneData = _.cloneDeep(row);
    if (field === 'bill_id') {
      cloneData.bill_id = row.bill_id ? '1' : '0';
    }
    return filterOption.value[field]?.checked?.length
      ? filterOption.value[field].checked.includes(cloneData[field])
      : true;
  };
  const renderData = computed(() => {
    const [start, end] = comfirmDaterange.value;
    const dateParams =
      start && end
        ? {
            end_time: new Date(end).getTime(),
            start_time: new Date(start).getTime(),
          }
        : {
            end_time: 0,
            start_time: 0,
          };

    const searchParams = getSearchSelectorParams(searchSelectValue.value);

    filteredData.value = [];
    tableData.value.forEach((row) => {
      const timerange = {
        end_time: new Date(row.backup_begin_time).getTime(),
        start_time: new Date(row.backup_begin_time).getTime(),
      };
      const isTimeMatch = timerange.start_time >= dateParams.start_time && timerange.end_time <= dateParams.end_time;
      const isSearchMatch = !searchParams.display
        ? true
        : `${row.mysql_role} ${utcDisplayTime(row.backup_time)}`.indexOf(searchParams.display) > -1;
      const isFilterChecked =
        isChecked(row, 'backup_type') &&
        isChecked(row, 'bill_id') &&
        isChecked(row, 'is_full_backup') &&
        isChecked(row, 'extra_fields.backup_tool');
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
      tableData.value = results;
      filterOption.value.backup_tool.list = _.uniqBy(
        results.map((item) => ({
          text: item.extra_fields?.backup_tool,
          value: item.extra_fields?.backup_tool,
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
    modelValue.value = row;
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
